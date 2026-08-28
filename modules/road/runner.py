"""Future isolated-process runner boundary for the road module."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from modules.road.contracts import RoadJob, RoadWorkerEvent


class RoadProcessRunner:
    """Configuration-only QProcess seam; process startup is intentionally deferred."""

    def __init__(self, python_executable: str = "", worker_script: str = "") -> None:
        self.python_executable = python_executable
        self.worker_script = worker_script

    @property
    def configured(self) -> bool:
        return bool(self.python_executable and self.worker_script)

    def build_command(self, job_path: str | Path) -> tuple[str, ...]:
        if not self.configured:
            raise RuntimeError("道路独立运行环境尚未配置")
        return self.python_executable, self.worker_script, "--job", str(job_path)

    @staticmethod
    def write_job(job: RoadJob, job_path: str | Path) -> Path:
        path = Path(job_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(job.to_json(indent=2), encoding="utf-8")
        return path

    def start_job(
        self,
        job: RoadJob,
        on_event: Callable[[RoadWorkerEvent], None],
        on_error: Callable[[str], None],
    ) -> None:
        raise NotImplementedError("本轮仅建立 Runner 接口，尚未启动真实道路 Worker")

    def cancel(self, job_id: str) -> None:
        """Cancel a future running process; no process exists in the Mock phase."""
