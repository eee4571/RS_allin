from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, QProcess, QProcessEnvironment, Signal

from .models import (
    PluginPaths,
    RunRequest,
    choose_run_state,
    latest_pipeline_manifest,
    read_json_object,
    result_events_from_index,
    selected_pairs,
)


STRUCTURED_PREFIX = "__SAMROAD_USER__"


class RoadRunner(QObject):
    task_started = Signal(dict)
    task_progress = Signal(dict)
    task_log = Signal(str)
    task_finished = Signal(dict)
    task_failed = Signal(str)
    result_ready = Signal(dict)
    running_changed = Signal(bool)

    def __init__(self, parent: QObject | None = None, *, paths: PluginPaths | None = None) -> None:
        super().__init__(parent)
        self.paths = paths or PluginPaths.discover()
        self._process = QProcess(self)
        self._process.setProcessChannelMode(QProcess.SeparateChannels)
        self._process.readyReadStandardOutput.connect(self._read_stdout)
        self._process.readyReadStandardError.connect(self._read_stderr)
        self._process.started.connect(self._on_started)
        self._process.finished.connect(self._on_finished)
        self._process.errorOccurred.connect(self._on_process_error)
        self._stdout_buffer = ""
        self._stderr_buffer = ""
        self._command: list[str] = []
        self._last_event: dict[str, Any] = {}
        self._output_root: Path | None = None
        self._manifest_path: Path | None = None
        self._cancelled = False

    @property
    def is_running(self) -> bool:
        return self._process.state() != QProcess.NotRunning

    def build_full_arguments(self, request: RunRequest) -> list[str]:
        if request.execution_profile not in {"full", "fast"}:
            raise ValueError("处理模式必须是 full 或 fast。")
        if request.device not in {"auto", "cuda", "cpu"}:
            raise ValueError("计算设备必须是 auto、cuda 或 cpu。")
        area = request.catalog.areas.get(request.area_id)
        if area is None:
            raise ValueError(f"数据中不存在区域：{request.area_id}")
        periods = tuple(request.periods)
        if len(periods) < 2:
            raise ValueError("请至少选择两个期次。")
        missing = [period for period in periods if period not in area.periods]
        if missing:
            raise ValueError("区域中不存在期次：" + "、".join(missing))
        output = Path(request.output_root).expanduser().resolve()
        run_id, resume = choose_run_state(output, request.execution_profile)
        args = [
            "all", "--mode", "validation",
            "--execution-profile", request.execution_profile,
            "--validation-area", area.area_id, str(area.validation_area),
        ]
        for period in periods:
            args.extend(("--period", area.area_id, period, str(area.periods[period])))
        truths_complete = True
        for before, after in selected_pairs(periods):
            truth = area.truths.get((before, after))
            if truth is None or not truth.is_file():
                truths_complete = False
                break
        if truths_complete:
            for before, after in selected_pairs(periods):
                args.extend(("--truth", area.area_id, before, after, str(area.truths[(before, after)])))
        else:
            args.append("--no-evaluation")
        args.extend((
            "--output-root", str(output),
            "--checkpoint", str(self.paths.checkpoint),
            "--config", str(self.paths.config),
            "--device", request.device,
            "--pixel-size", str(request.pixel_size),
            "--rescale", request.rescale,
            "--junction-node-mode", request.junction_node_mode,
            "--absolute", str(request.absolute),
            "--ratio", str(request.ratio),
            "--tolerance", str(request.tolerance),
            "--run-id", run_id,
            "--runtime-preflight",
        ))
        if resume:
            args.append("--resume")
        if request.continue_on_error:
            args.append("--continue-on-error")
        return args

    @staticmethod
    def build_rerun_period_arguments(manifest: Path | str, area_id: str, period: str) -> list[str]:
        return [
            "rerun-period", "--pipeline-manifest", str(Path(manifest).resolve()),
            "--grid", str(area_id), "--period", str(period), "--update-related",
        ]

    @staticmethod
    def build_rerun_change_arguments(
        manifest: Path | str, area_id: str, before: str, after: str,
    ) -> list[str]:
        return [
            "rerun-change", "--pipeline-manifest", str(Path(manifest).resolve()),
            "--grid", str(area_id), "--before-period", str(before),
            "--after-period", str(after), "--update-temporal",
        ]

    def command_line(self, arguments: list[str]) -> list[str]:
        return [str(self.paths.python_executable), str(self.paths.backend_script), *map(str, arguments)]

    def start_full(self, request: RunRequest) -> None:
        self._output_root = Path(request.output_root).expanduser().resolve()
        self._manifest_path = None
        self.start(self.build_full_arguments(request))

    def start_rerun_period(self, output_root: Path | str, area_id: str, period: str) -> None:
        manifest = latest_pipeline_manifest(output_root)
        if manifest is None:
            raise ValueError("未找到当前任务的 pipeline_result，请先运行完整流程。")
        self._output_root = Path(output_root).expanduser().resolve()
        self._manifest_path = manifest
        self.start(self.build_rerun_period_arguments(manifest, area_id, period))

    def start_rerun_change(self, output_root: Path | str, area_id: str, before: str, after: str) -> None:
        manifest = latest_pipeline_manifest(output_root)
        if manifest is None:
            raise ValueError("未找到当前任务的 pipeline_result，请先运行完整流程。")
        self._output_root = Path(output_root).expanduser().resolve()
        self._manifest_path = manifest
        self.start(self.build_rerun_change_arguments(manifest, area_id, before, after))

    def start(self, arguments: list[str]) -> None:
        if self.is_running:
            raise RuntimeError("当前已有道路变化检测任务在运行。")
        issues = self.paths.runtime_issues()
        if issues:
            raise FileNotFoundError("\n".join(issues))
        self._stdout_buffer = ""
        self._stderr_buffer = ""
        self._last_event = {}
        self._cancelled = False
        self._command = self.command_line(arguments)
        environment = QProcessEnvironment.systemEnvironment()
        environment.insert("PYTHONUTF8", "1")
        environment.insert("PYTHONIOENCODING", "utf-8")
        site_packages = self.paths.runtime_root / "env" / "samroad_env" / "Lib" / "site-packages"
        proj = site_packages / "rasterio" / "proj_data"
        gdal = site_packages / "rasterio" / "gdal_data"
        if (proj / "proj.db").is_file():
            environment.insert("PROJ_DATA", str(proj))
            environment.insert("PROJ_LIB", str(proj))
        if gdal.is_dir():
            environment.insert("GDAL_DATA", str(gdal))
        self._process.setProcessEnvironment(environment)
        self._process.setWorkingDirectory(str(self.paths.root / "code"))
        self._process.setProgram(self._command[0])
        self._process.setArguments(self._command[1:])
        self.running_changed.emit(True)
        self._process.start()

    def cancel(self) -> None:
        if not self.is_running:
            return
        self._cancelled = True
        self.task_log.emit("正在取消任务…")
        self._process.terminate()
        if not self._process.waitForFinished(3000):
            self._process.kill()

    def shutdown(self) -> None:
        self.cancel()

    @staticmethod
    def parse_line(line: str) -> tuple[str, dict[str, Any] | str]:
        value = str(line).rstrip("\r\n")
        if not value.startswith(STRUCTURED_PREFIX):
            return "log", value
        payload = json.loads(value[len(STRUCTURED_PREFIX):])
        if not isinstance(payload, dict):
            raise ValueError("后端结构化消息必须是 JSON 对象")
        return "event", payload

    def _consume_lines(self, text: str, *, stderr: bool = False) -> None:
        buffer_name = "_stderr_buffer" if stderr else "_stdout_buffer"
        combined = getattr(self, buffer_name) + text
        lines = combined.splitlines(keepends=True)
        tail = ""
        if lines and not lines[-1].endswith(("\n", "\r")):
            tail = lines.pop()
        setattr(self, buffer_name, tail)
        for line in lines:
            self._handle_line(line.rstrip("\r\n"), force_log=stderr)

    def _handle_line(self, line: str, *, force_log: bool = False) -> None:
        if not line:
            return
        if force_log:
            self.task_log.emit(line)
            return
        try:
            kind, value = self.parse_line(line)
        except (json.JSONDecodeError, ValueError) as exc:
            self.task_log.emit(f"[结构化消息解析失败] {exc}: {line}")
            return
        if kind == "log":
            self.task_log.emit(str(value))
            return
        payload = dict(value)  # type: ignore[arg-type]
        self._last_event = payload
        manifest = payload.get("manifest")
        if isinstance(manifest, str) and manifest:
            self._manifest_path = Path(manifest).expanduser().resolve()
        completed, total = payload.get("completed"), payload.get("total")
        try:
            progress = float(payload.get("progress"))
        except (TypeError, ValueError):
            try:
                progress = float(completed) / float(total) if float(total) else 0.0
            except (TypeError, ValueError, ZeroDivisionError):
                progress = -1.0
        payload["progress"] = max(0.0, min(1.0, progress)) if progress >= 0 else -1.0
        self.task_progress.emit(payload)
        if payload.get("kind") == "failure" or payload.get("status") == "failed":
            self.task_log.emit(str(payload.get("error") or payload.get("message") or "后端报告失败"))

    def _read_stdout(self) -> None:
        text = bytes(self._process.readAllStandardOutput()).decode("utf-8", errors="replace")
        self._consume_lines(text)

    def _read_stderr(self) -> None:
        text = bytes(self._process.readAllStandardError()).decode("utf-8", errors="replace")
        self._consume_lines(text, stderr=True)

    def _flush_buffers(self) -> None:
        if self._stdout_buffer:
            self._handle_line(self._stdout_buffer)
            self._stdout_buffer = ""
        if self._stderr_buffer:
            self._handle_line(self._stderr_buffer, force_log=True)
            self._stderr_buffer = ""

    def _on_started(self) -> None:
        self.task_started.emit({"command": list(self._command)})

    def _on_process_error(self, error: QProcess.ProcessError) -> None:
        if error == QProcess.FailedToStart:
            self.task_failed.emit(f"无法启动道路算法进程：{self._process.errorString()}")

    def _on_finished(self, exit_code: int, exit_status: QProcess.ExitStatus) -> None:
        self._flush_buffers()
        self.running_changed.emit(False)
        if self._cancelled:
            self.task_failed.emit("任务已取消。")
            return
        if exit_status != QProcess.NormalExit or exit_code != 0:
            self.task_failed.emit(f"道路算法进程异常结束（退出码 {exit_code}）。")
            return
        result = {"exit_code": exit_code, "command": list(self._command), "event": dict(self._last_event)}
        self.task_finished.emit(result)
        self._publish_results()

    def _publish_results(self) -> None:
        if self._output_root is None:
            return
        index_path = self._output_root / "result_index.json"
        index = read_json_object(index_path)
        if index is None:
            self.task_log.emit(f"未找到正式成果索引：{index_path}")
            return
        for result in result_events_from_index(index, index_path):
            self.result_ready.emit(result)

