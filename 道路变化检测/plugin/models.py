from __future__ import annotations

"""Lightweight plugin-side models.

This module intentionally uses only the Python standard library.  Road algorithm
packages are loaded exclusively by ``code/user_pipeline.py`` in its own process.
"""

import json
import importlib
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable


@dataclass(frozen=True)
class PluginPaths:
    root: Path
    runtime_root: Path
    backend_script: Path
    python_executable: Path
    checkpoint: Path
    config: Path

    @classmethod
    def discover(cls, anchor: Path | None = None) -> "PluginPaths":
        root = (anchor or Path(__file__)).resolve().parents[1]
        runtime = root / "runtime"
        python_candidates = (
            runtime / "env" / "samroad_env" / "python.exe",
            runtime / "env" / "samroad_env" / "bin" / "python",
            runtime / "python.exe",
        )
        python = next((path for path in python_candidates if path.is_file()), python_candidates[0])
        return cls(
            root=root,
            runtime_root=runtime,
            backend_script=root / "code" / "user_pipeline.py",
            python_executable=python,
            checkpoint=runtime / "models" / "samroad" / "samroad.ckpt",
            config=runtime / "config" / "samroad_inference.yaml",
        )

    def runtime_issues(self) -> list[str]:
        issues: list[str] = []
        for label, path in (
            ("独立 Python", self.python_executable),
            ("批处理后端", self.backend_script),
            ("道路模型", self.checkpoint),
            ("推理配置", self.config),
        ):
            if not path.is_file():
                issues.append(f"{label}不存在：{path}")
        return issues


@dataclass(frozen=True)
class AreaData:
    area_id: str
    validation_area: Path
    periods: dict[str, Path]
    truths: dict[tuple[str, str], Path] = field(default_factory=dict)


@dataclass(frozen=True)
class DataCatalog:
    source_root: Path
    areas: dict[str, AreaData]
    suggested_output: Path

    @property
    def area_ids(self) -> list[str]:
        return list(self.areas)


@dataclass(frozen=True)
class RunRequest:
    catalog: DataCatalog
    area_id: str
    periods: tuple[str, ...]
    output_root: Path
    execution_profile: str = "full"
    device: str = "auto"
    absolute: str = "2.0"
    ratio: str = "0.2"
    tolerance: str = "3.0"
    pixel_size: str = "0.0"
    rescale: str = "off"
    junction_node_mode: str = "sparse"
    continue_on_error: bool = True


def _open_with_project_manager(root: Path, source: Path) -> dict[str, Any]:
    """Use the existing scanner without leaking its generic ``app`` package.

    The historical backend uses top-level imports such as ``app.project_manager``.
    An embedding host may own a package with that name, so the algorithm package
    is installed only for this synchronous scan and the host's modules are then
    restored unchanged.
    """
    code_root = str((root / "code").resolve())
    saved_app_modules = {
        name: module for name, module in tuple(sys.modules.items())
        if name == "app" or name.startswith("app.")
    }
    for name in saved_app_modules:
        sys.modules.pop(name, None)
    sys.path.insert(0, code_root)
    try:
        module = importlib.import_module("app.project_manager")
        return module.ProjectManager().open_project(source)
    finally:
        for name in tuple(sys.modules):
            if name == "app" or name.startswith("app."):
                sys.modules.pop(name, None)
        sys.modules.update(saved_app_modules)
        try:
            sys.path.remove(code_root)
        except ValueError:
            pass


def scan_data_source(source_root: Path | str, plugin_root: Path | None = None) -> DataCatalog:
    root = Path(source_root).expanduser().resolve()
    if not root.is_dir():
        raise ValueError(f"数据目录不存在：{root}")
    paths = PluginPaths.discover(plugin_root / "plugin" / "models.py" if plugin_root else None)
    opened = _open_with_project_manager(paths.root, root)
    discovered = dict(opened.get("discovered") or {})
    config = dict(opened.get("config") or {})
    validation_areas = config.get("validation_areas") or discovered.get("validation_areas") or []
    area_periods = config.get("area_periods") or discovered.get("area_periods") or {}
    truth_rows = config.get("area_truths") or discovered.get("area_truths") or {}
    if isinstance(truth_rows, dict):
        truth_map = {
            tuple(map(str, key)): Path(value).resolve()
            for key, value in truth_rows.items()
        }
    else:
        truth_map = {
            (str(area), str(before), str(after)): Path(value).resolve()
            for area, before, after, value in truth_rows
        }
    areas: dict[str, AreaData] = {}
    for area_id, boundary in validation_areas:
        name = str(area_id)
        periods = {
            str(period): Path(source).expanduser().resolve()
            for period, source in area_periods.get(name, [])
        }
        truths = {
            (before, after): path
            for (area, before, after), path in truth_map.items()
            if area == name
        }
        areas[name] = AreaData(name, Path(boundary).expanduser().resolve(), periods, truths)
    if not areas:
        raise ValueError("没有识别到验证区和多期影像。")
    suggested_output = config.get("output_root") or discovered.get("output_root") or (root / "成果输出")
    return DataCatalog(root, areas, Path(suggested_output).expanduser().resolve())


def latest_pipeline_manifest(output_root: Path | str) -> Path | None:
    output = Path(output_root).expanduser().resolve()
    candidate = output.parent / "_work" / "tasks" / "latest_pipeline.json"
    return candidate if candidate.is_file() else None


def read_json_object(path: Path | str) -> dict[str, Any] | None:
    source = Path(path).expanduser()
    try:
        value = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def selected_pairs(periods: Iterable[str]) -> list[tuple[str, str]]:
    ordered = [str(value) for value in periods]
    return list(zip(ordered, ordered[1:]))


def choose_run_state(output_root: Path, execution_profile: str) -> tuple[str, bool]:
    manifest_path = latest_pipeline_manifest(output_root)
    manifest = read_json_object(manifest_path) if manifest_path else None
    if manifest and str(manifest.get("execution_profile") or "full") == execution_profile:
        run_id = str(manifest.get("run_id") or "").strip()
        if run_id:
            return run_id, True
    return time.strftime("run_%Y%m%d_%H%M%S"), False


_PERIOD_RESULT_TYPES = {
    "centerlines": "road_centerline",
    "surfaces": "road_surface",
    "width_segments": "road_width_segments",
    "corridors": "road_corridor",
    "road_extraction": "road_extraction_preview",
    "road_width": "road_width_preview",
}
_CHANGE_RESULT_TYPES = {
    "changes": "road_change",
    "added": "road_added",
    "removed": "road_removed",
    "widened": "road_widened",
    "narrowed": "road_narrowed",
    "width_changed": "road_width_changed",
    "road_change": "road_change_preview",
    "review_change": "road_change_review_preview",
}
_TEMPORAL_RESULT_TYPES = {
    "life_shp": "road_life",
    "observations_shp": "road_observations",
    "events_shp": "road_events",
    "event_parts_shp": "road_event_parts",
    "lineage_shp": "road_lineage",
    "review_shp": "road_review",
}


def result_events_from_index(index: dict[str, Any], index_path: Path | str) -> list[dict[str, Any]]:
    """Convert the authoritative result index to host-neutral result dictionaries."""
    base = Path(index_path).expanduser().resolve().parent
    events: list[dict[str, Any]] = []

    def add(mapping: dict[str, str], values: dict[str, Any], common: dict[str, Any]) -> None:
        for key, result_type in mapping.items():
            raw = values.get(key)
            if not isinstance(raw, str) or not raw.strip():
                continue
            path = Path(raw).expanduser()
            if not path.is_absolute():
                path = base / path
            events.append({"type": result_type, "path": str(path.resolve()), **common})

    for area_id, area in (index.get("areas") or {}).items():
        if not isinstance(area, dict):
            continue
        for period, values in (area.get("periods") or {}).items():
            if isinstance(values, dict):
                add(_PERIOD_RESULT_TYPES, values, {"area_id": str(area_id), "period": str(period)})
        for pair, values in (area.get("changes") or {}).items():
            if not isinstance(values, dict):
                continue
            before = str(values.get("before_period") or str(pair).split("_to_", 1)[0])
            after = str(values.get("after_period") or (str(pair).split("_to_", 1)[1] if "_to_" in str(pair) else ""))
            add(_CHANGE_RESULT_TYPES, values, {
                "area_id": str(area_id), "before_period": before, "after_period": after,
            })
        temporal = area.get("temporal")
        if isinstance(temporal, dict):
            add(_TEMPORAL_RESULT_TYPES, temporal, {"area_id": str(area_id)})
        evaluation = area.get("evaluation")
        if isinstance(evaluation, dict):
            add({"csv": "road_evaluation_csv", "json": "road_evaluation_json"}, evaluation, {"area_id": str(area_id)})
    reports = index.get("task_report")
    if isinstance(reports, dict):
        add({"csv": "road_task_report_csv", "json": "road_task_report_json"}, reports, {})
    return events
