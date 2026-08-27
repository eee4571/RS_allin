"""Reusable timer-driven adapter used by the three prototype integrations."""

from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import QObject, QTimer

from core.event_bus import EventBus
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


class TimedMockAdapter(QObject):
    """Simulate algorithms while preserving the future adapter boundary."""

    def __init__(self, event_bus: EventBus, module_id: str, layer_type: str) -> None:
        super().__init__(event_bus)
        self._event_bus = event_bus
        self._module_id = module_id
        self._layer_type = layer_type
        self._active: set[str] = set()
        self._timers: set[QTimer] = set()

    def run(self, command: Command, workflow: WorkflowDefinition) -> None:
        key = workflow.id
        if key in self._active:
            self._event_bus.publish(
                TaskFailed(self._module_id, key, "该工作流正在运行，请稍候。")
            )
            return

        self._active.add(key)
        self._event_bus.publish(TaskStarted(self._module_id, key, f"开始：{workflow.name}"))
        self._event_bus.publish(TaskLog(self._module_id, key, f"Mock 参数：{command.payload}"))
        self._event_bus.publish(WorkflowStateChanged(self._module_id, key, "running"))

        timer = QTimer(self)
        timer.setInterval(420)
        self._timers.add(timer)
        tick = {"value": 0}
        total = max(1, len(workflow.steps))

        def advance() -> None:
            index = tick["value"]
            if index < total:
                step = workflow.steps[min(index, len(workflow.steps) - 1)]
                progress = (index + 1) / total
                self._event_bus.publish(
                    TaskProgress(
                        self._module_id,
                        key,
                        progress,
                        f"{step.name}（Mock）",
                        step.id,
                    )
                )
                self._event_bus.publish(
                    TaskLog(self._module_id, key, f"完成模拟步骤：{step.name}")
                )
                tick["value"] += 1
                return

            timer.stop()
            timer.deleteLater()
            self._timers.discard(timer)
            self._active.discard(key)
            layer_id = f"{self._module_id}.{key}.{datetime.now():%H%M%S}"
            result = {"mock": True, "parameters": dict(command.payload)}
            self._event_bus.publish(
                ResultAvailable(self._module_id, key, self._layer_type, workflow.name, result)
            )
            self._event_bus.publish(
                LayerAdded(self._module_id, layer_id, f"{workflow.name}结果", self._layer_type, result)
            )
            self._event_bus.publish(
                TaskCompleted(self._module_id, key, f"{workflow.name}模拟运行完成", result)
            )
            self._event_bus.publish(WorkflowStateChanged(self._module_id, key, "completed"))

        timer.timeout.connect(advance)
        timer.start()
        advance()

    def execute_tool(self, command: Command) -> None:
        self._event_bus.publish(
            TaskLog(
                self._module_id,
                command.workflow_id,
                f"收到统一工具命令：{command.action}，参数：{command.payload}",
            )
        )

