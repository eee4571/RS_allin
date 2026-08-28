"""Road execution boundary: platform commands in, platform events out."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from PySide6.QtCore import QObject, QTimer

from core.models import (
    Command,
    LayerAdded,
    ResultAvailable,
    TaskCompleted,
    TaskFailed,
    TaskLog,
    TaskProgress,
    TaskStarted,
    WorkflowDefinition,
    WorkflowStateChanged,
)
from core.project_context import ProjectContext
from modules.road.contracts import RoadJob, RoadWorkerEvent
from modules.road.runner import RoadProcessRunner


class RoadAdapter(QObject):
    """Translate stable road commands to jobs without importing algorithm code."""

    MODULE_ID = "road"

    def __init__(
        self,
        event_bus,
        runner: RoadProcessRunner | None = None,
        mock_interval_ms: int = 120,
    ) -> None:
        super().__init__(event_bus)
        self._event_bus = event_bus
        self._runner = runner
        self._mock_interval_ms = mock_interval_ms
        self._project_context = ProjectContext()
        self._jobs: dict[str, tuple[RoadJob, WorkflowDefinition]] = {}
        self._active_workflows: dict[str, str] = {}
        self._timers: dict[str, QTimer] = {}

    def set_project_context(self, context: ProjectContext) -> None:
        self._project_context = context

    def run(self, command: Command, workflow: WorkflowDefinition) -> None:
        if workflow.id in self._active_workflows:
            self._event_bus.publish(
                TaskFailed(
                    self.MODULE_ID,
                    workflow.id,
                    "该道路任务正在运行，请等待完成或取消后重试。",
                )
            )
            return
        job = self.build_job(command)
        self._jobs[job.job_id] = (job, workflow)
        self._active_workflows[workflow.id] = job.job_id
        self.start_job(job, workflow)

    def build_job(self, command: Command) -> RoadJob:
        """Resolve project-owned data into a Qt-free worker contract."""
        payload = dict(command.payload)
        action = command.workflow_id
        area_id = str(payload.get("area_id", ""))
        periods: tuple[str, ...] = ()
        change_pair = None
        if action == "full_pipeline":
            periods = self._normalize_periods(payload.get("periods"))
        elif action == "rerun_period":
            period = str(payload.get("period", ""))
            periods = (period,) if period else ()
        elif action == "rerun_change_pair":
            before = str(payload.get("before", ""))
            after = str(payload.get("after", ""))
            if before and after:
                change_pair = (before, after)
                periods = change_pair

        project_root = str(self._project_context.project_root or "")
        output_root = str(self._project_context.output_root or "")
        if not output_root and project_root:
            output_root = str(Path(project_root) / "results")

        inputs = self._project_context.inputs or {}
        area_inputs = inputs.get(area_id) if area_id else None
        input_manifest = dict(area_inputs) if isinstance(area_inputs, dict) else dict(inputs)
        business_fields = {
            "area_id", "periods", "period", "before", "after", "update_related"
        }
        options = {
            key: value for key, value in payload.items() if key not in business_fields
        }
        options["update_related"] = bool(payload.get("update_related", True))

        return RoadJob(
            job_id=uuid4().hex,
            action=action,
            project_root=project_root,
            area_id=area_id,
            periods=periods,
            change_pair=change_pair,
            input_manifest=input_manifest,
            output_root=output_root,
            options=options,
        )

    def start_job(self, job: RoadJob, workflow: WorkflowDefinition) -> None:
        """Use a configured process runner later; use the isolated Mock path now."""
        self.handle_worker_event(
            job.job_id,
            RoadWorkerEvent("started", f"开始：{workflow.name}"),
        )
        self._event_bus.publish(
            TaskLog(
                self.MODULE_ID,
                workflow.id,
                f"道路任务已构建：{job.action} · 区域 {job.area_id or '当前区域'}",
            )
        )
        if self._runner is None:
            self.run_mock_job(job, workflow)
            return
        try:
            self._runner.start_job(
                job,
                lambda event: self.handle_worker_event(job.job_id, event),
                lambda message: self.handle_error(job.job_id, message),
            )
        except Exception as exc:
            self.handle_error(job.job_id, str(exc))

    def run_mock_job(self, job: RoadJob, workflow: WorkflowDefinition) -> None:
        """Simulate Worker JSON events while exercising the final adapter path."""
        timer = QTimer(self)
        timer.setInterval(self._mock_interval_ms)
        self._timers[job.job_id] = timer
        tick = {"value": 0}
        steps = workflow.steps

        def advance() -> None:
            index = tick["value"]
            if index < len(steps):
                step = steps[index]
                self.handle_worker_event(
                    job.job_id,
                    RoadWorkerEvent(
                        "progress",
                        f"{step.name}（Mock）",
                        (index + 1) / max(1, len(steps)),
                        step.id,
                    ),
                )
                self.handle_worker_event(
                    job.job_id,
                    RoadWorkerEvent("log", f"完成模拟步骤：{step.name}"),
                )
                tick["value"] += 1
                return

            timer.stop()
            for result in self._mock_result_events(job):
                self.handle_worker_event(job.job_id, result)
            self.handle_worker_event(
                job.job_id,
                RoadWorkerEvent("completed", f"{workflow.name}模拟运行完成"),
            )

        timer.timeout.connect(advance)
        timer.start()
        advance()

    def handle_worker_event(self, job_id: str, event: RoadWorkerEvent) -> None:
        """Map one worker-protocol event to stable platform events."""
        job_entry = self._jobs.get(job_id)
        if job_entry is None:
            return
        job, workflow = job_entry
        if event.type == "started":
            self._event_bus.publish(
                TaskStarted(self.MODULE_ID, workflow.id, event.message)
            )
            self._event_bus.publish(
                WorkflowStateChanged(self.MODULE_ID, workflow.id, "running")
            )
        elif event.type == "progress":
            self._event_bus.publish(
                TaskProgress(
                    self.MODULE_ID,
                    workflow.id,
                    max(0.0, min(1.0, event.progress or 0.0)),
                    event.message,
                    event.step,
                )
            )
        elif event.type == "log":
            self._event_bus.publish(
                TaskLog(self.MODULE_ID, workflow.id, event.message, event.level)
            )
        elif event.type == "result":
            self.handle_result(job, workflow, event)
        elif event.type == "completed":
            self._event_bus.publish(
                TaskCompleted(
                    self.MODULE_ID, workflow.id, event.message, job.to_dict()
                )
            )
            self._event_bus.publish(
                WorkflowStateChanged(self.MODULE_ID, workflow.id, "completed")
            )
            self._cleanup(job_id, workflow.id)
        elif event.type in {"error", "failed"}:
            self.handle_error(job_id, event.message)
        else:
            self._event_bus.publish(
                TaskLog(
                    self.MODULE_ID,
                    workflow.id,
                    f"忽略未知 Worker 事件：{event.type}",
                    "WARNING",
                )
            )

    def handle_result(
        self,
        job: RoadJob,
        workflow: WorkflowDefinition,
        event: RoadWorkerEvent,
    ) -> None:
        data = dict(event.data)
        data.update(
            {
                "path": event.path,
                "area_id": job.area_id,
                "job_id": job.job_id,
                "mock": self._runner is None,
            }
        )
        name = event.name or event.result_type
        self._event_bus.publish(
            ResultAvailable(
                self.MODULE_ID, workflow.id, event.result_type, name, data
            )
        )
        self._event_bus.publish(
            LayerAdded(
                self.MODULE_ID,
                f"road.{job.job_id}.{event.result_type}",
                name,
                event.result_type,
                data,
            )
        )

    def handle_error(self, job_id: str, message: str) -> None:
        job_entry = self._jobs.get(job_id)
        if job_entry is None:
            return
        _, workflow = job_entry
        self._event_bus.publish(
            TaskFailed(self.MODULE_ID, workflow.id, message or "道路任务失败")
        )
        self._event_bus.publish(
            WorkflowStateChanged(self.MODULE_ID, workflow.id, "failed")
        )
        self._cleanup(job_id, workflow.id)

    def cancel(self, workflow_id: str = "") -> None:
        if workflow_id:
            job_id = self._active_workflows.get(workflow_id)
            targets = [job_id] if job_id else []
        else:
            targets = list(self._jobs)
        for job_id in targets:
            if self._runner is not None:
                self._runner.cancel(job_id)
            self.handle_error(job_id, "道路任务已取消")

    def handle_action(self, command: Command) -> None:
        if command.action != "update_after_edit":
            raise ValueError(f"未知道路操作：{command.action}")
        self._event_bus.publish(
            TaskLog(
                self.MODULE_ID,
                command.workflow_id,
                "已收到编辑后成果更新请求；业务接口已预留，本轮未执行计算。",
            )
        )

    def _cleanup(self, job_id: str, workflow_id: str) -> None:
        timer = self._timers.pop(job_id, None)
        if timer is not None:
            timer.stop()
            timer.deleteLater()
        self._jobs.pop(job_id, None)
        self._active_workflows.pop(workflow_id, None)

    def _mock_result_events(self, job: RoadJob) -> tuple[RoadWorkerEvent, ...]:
        if job.action == "rerun_change_pair":
            result_types = ("road_change",)
        elif job.action == "rerun_period":
            result_types = ("road_centerline", "road_surface", "road_width")
        else:
            result_types = (
                "road_centerline", "road_surface", "road_width", "road_change"
            )
        names = {
            "road_centerline": "道路中心线",
            "road_surface": "道路面",
            "road_width": "道路宽度",
            "road_change": "道路变化结果",
        }
        suffix = "-".join(job.change_pair or job.periods) or "current"
        return tuple(
            RoadWorkerEvent(
                "result",
                result_type=result_type,
                path=self._mock_output_path(job, result_type, suffix),
                name=f"{names[result_type]} · {suffix}",
                data={
                    "group": "道路变化" if result_type == "road_change" else "道路成果"
                },
            )
            for result_type in result_types
        )

    @staticmethod
    def _mock_output_path(job: RoadJob, result_type: str, suffix: str) -> str:
        if not job.output_root:
            return f"mock://{job.job_id}/{result_type}/{suffix}"
        return str(Path(job.output_root) / job.area_id / f"{result_type}_{suffix}.geojson")

    @staticmethod
    def _normalize_periods(value) -> tuple[str, ...]:
        if isinstance(value, str):
            return tuple(item.strip() for item in value.split(",") if item.strip())
        if value is None:
            return ()
        return tuple(str(item) for item in value)
