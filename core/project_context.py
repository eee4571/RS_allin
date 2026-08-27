"""Project information shared by every module."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class ProjectContext:
    project_name: str = "未命名遥感工程"
    project_root: str = ""
    periods: dict[str, str] = field(
        default_factory=lambda: {"2022": "前期影像", "2024": "后期影像"}
    )
    areas: dict[str, Any] = field(default_factory=dict)
    layers: list[Any] = field(default_factory=list)
    results: dict[str, Any] = field(default_factory=dict)

