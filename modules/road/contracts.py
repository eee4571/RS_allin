"""Serializable contracts between the road adapter and a future worker."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


def _json_value(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_json_value(item) for item in value]
    return value


@dataclass(frozen=True, slots=True)
class RoadJob:
    """Qt-free road job description suitable for a future ``job.json``."""

    job_id: str
    action: str
    project_root: str = ""
    area_id: str = ""
    periods: tuple[str, ...] = ()
    change_pair: tuple[str, str] | None = None
    input_manifest: dict[str, Any] = field(default_factory=dict)
    output_root: str = ""
    options: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["periods"] = list(self.periods)
        value["change_pair"] = (
            list(self.change_pair) if self.change_pair is not None else None
        )
        return _json_value(value)

    def to_json(self, *, indent: int | None = None) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "RoadJob":
        pair = value.get("change_pair")
        return cls(
            job_id=str(value["job_id"]),
            action=str(value["action"]),
            project_root=str(value.get("project_root", "")),
            area_id=str(value.get("area_id", "")),
            periods=tuple(str(item) for item in value.get("periods", ())),
            change_pair=(str(pair[0]), str(pair[1])) if pair else None,
            input_manifest=dict(value.get("input_manifest") or {}),
            output_root=str(value.get("output_root", "")),
            options=dict(value.get("options") or {}),
        )


@dataclass(frozen=True, slots=True)
class RoadWorkerEvent:
    """One JSON-Lines event emitted by a future isolated road worker."""

    type: str
    message: str = ""
    progress: float | None = None
    step: str = ""
    level: str = "INFO"
    result_type: str = ""
    path: str = ""
    name: str = ""
    data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return _json_value({
            key: value
            for key, value in asdict(self).items()
            if value not in (None, "", {})
        })

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)

    @classmethod
    def from_json_line(cls, line: str) -> "RoadWorkerEvent":
        value = json.loads(line)
        if not isinstance(value, dict) or not value.get("type"):
            raise ValueError("道路 Worker 事件必须是包含 type 的 JSON 对象")
        return cls(
            type=str(value["type"]),
            message=str(value.get("message", "")),
            progress=(
                float(value["progress"]) if value.get("progress") is not None else None
            ),
            step=str(value.get("step", "")),
            level=str(value.get("level", "INFO")),
            result_type=str(value.get("result_type", "")),
            path=str(value.get("path", "")),
            name=str(value.get("name", "")),
            data=dict(value.get("data") or {}),
        )
