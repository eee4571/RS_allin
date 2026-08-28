from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QWidget


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
if str(PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(PLUGIN_ROOT))

from plugin import create_plugin
from plugin.models import (
    AreaData, DataCatalog, PluginPaths, RunRequest, result_events_from_index,
    scan_data_source,
)
from plugin.runner import RoadRunner
from standalone import build_window


class PluginTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temporary.name)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def request(self, profile: str = "full", device: str = "auto", name: str = "case") -> RunRequest:
        source = self.temp_path / name / "data"
        source.mkdir(parents=True)
        boundary = source / "area.shp"
        before = source / "2022.txt"
        after = source / "2024.txt"
        truth = source / "2022_to_2024.shp"
        for path in (boundary, before, after, truth):
            path.touch()
        area = AreaData("area_a", boundary, {"2022": before, "2024": after}, {("2022", "2024"): truth})
        catalog = DataCatalog(source, {"area_a": area}, self.temp_path / name / "suggested")
        return RunRequest(
            catalog=catalog,
            area_id="area_a",
            periods=("2022", "2024"),
            output_root=self.temp_path / name / "output",
            execution_profile=profile,
            device=device,
        )

    def test_public_plugin_and_widget(self) -> None:
        plugin = create_plugin()
        widget = plugin.create_widget()
        self.assertEqual(plugin.plugin_id, "road_change")
        self.assertIsInstance(widget, QWidget)
        plugin.shutdown()

    def test_standalone_builds_window(self) -> None:
        plugin, widget = build_window()
        self.assertIsInstance(widget, QWidget)
        self.assertTrue(widget.windowTitle().startswith("道路变化检测"))
        plugin.shutdown()

    def test_import_does_not_load_algorithm_dependencies(self) -> None:
        script = (
            "import json,sys; "
            f"sys.path.insert(0, {str(PLUGIN_ROOT)!r}); "
            "import plugin; "
            "names=('torch','rasterio','osgeo','cv2','segment_anything'); "
            "print(json.dumps([n for n in names if n in sys.modules]))"
        )
        env = dict(os.environ, QT_QPA_PLATFORM="offscreen")
        completed = subprocess.run(
            [sys.executable, "-c", script], check=True, capture_output=True, text=True, env=env,
        )
        self.assertEqual(json.loads(completed.stdout), [])

    def test_plugin_metadata(self) -> None:
        payload = json.loads((PLUGIN_ROOT / "plugin.json").read_text(encoding="utf-8"))
        self.assertEqual(payload["id"], "road_change")
        self.assertEqual(payload["entry"], "plugin:create_plugin")
        self.assertEqual(payload["ui"], "dock")

    def test_paths_are_relative_to_plugin_root(self) -> None:
        paths = PluginPaths.discover()
        self.assertEqual(paths.root, PLUGIN_ROOT)
        self.assertEqual(paths.backend_script, PLUGIN_ROOT / "code" / "user_pipeline.py")
        self.assertEqual(
            paths.python_executable,
            PLUGIN_ROOT / "runtime" / "env" / "samroad_env" / "python.exe",
        )
        self.assertEqual(paths.config, PLUGIN_ROOT / "runtime" / "config" / "samroad_inference.yaml")

    def test_full_command_profiles_and_devices(self) -> None:
        runner = RoadRunner(paths=PluginPaths.discover())
        for profile in ("full", "fast"):
            for device in ("auto", "cuda", "cpu"):
                with self.subTest(profile=profile, device=device):
                    args = runner.build_full_arguments(self.request(profile, device, f"{profile}_{device}"))
                    self.assertEqual(args[:3], ["all", "--mode", "validation"])
                    self.assertEqual(args[args.index("--execution-profile") + 1], profile)
                    self.assertEqual(args[args.index("--device") + 1], device)
                    self.assertIn("--validation-area", args)
                    self.assertEqual(args.count("--period"), 2)

    def test_existing_project_scanner_is_reused_without_leaking_app_package(self) -> None:
        project = self.temp_path / "project"
        boundary_dir = project / "01_验证区"
        imagery_dir = project / "02_影像"
        boundary_dir.mkdir(parents=True)
        imagery_dir.mkdir()
        (boundary_dir / "area_a.shp").touch()
        (imagery_dir / "2022.txt").touch()
        (imagery_dir / "2024.txt").touch()
        before = {name: module for name, module in sys.modules.items() if name == "app" or name.startswith("app.")}
        catalog = scan_data_source(project, PLUGIN_ROOT)
        after = {name: module for name, module in sys.modules.items() if name == "app" or name.startswith("app.")}
        self.assertEqual(catalog.area_ids, ["area_a"])
        self.assertEqual(list(catalog.areas["area_a"].periods), ["2022", "2024"])
        self.assertEqual(before, after)

    def test_rerun_commands_match_real_cli(self) -> None:
        manifest = self.temp_path / "pipeline_result.json"
        period = RoadRunner.build_rerun_period_arguments(manifest, "a", "2022")
        change = RoadRunner.build_rerun_change_arguments(manifest, "a", "2022", "2024")
        self.assertEqual(period[0], "rerun-period")
        self.assertEqual(period[-1], "--update-related")
        self.assertEqual(change[0], "rerun-change")
        self.assertEqual(change[-1], "--update-temporal")

    def test_structured_and_plain_stdout_parsing(self) -> None:
        kind, payload = RoadRunner.parse_line('__SAMROAD_USER__{"kind":"pipeline","progress":0.35}')
        self.assertEqual(kind, "event")
        self.assertEqual(payload["progress"], 0.35)
        self.assertEqual(RoadRunner.parse_line("ordinary log"), ("log", "ordinary log"))

    def test_result_index_becomes_result_ready_payloads(self) -> None:
        index_path = self.temp_path / "result_index.json"
        index = {
            "areas": {
                "area_a": {
                    "periods": {
                        "2022": {
                            "centerlines": "area/road_centerlines.shp",
                            "surfaces": "area/road_surfaces.shp",
                            "width_segments": "area/road_width_segments.shp",
                        }
                    },
                    "changes": {
                        "2022_to_2024": {
                            "before_period": "2022",
                            "after_period": "2024",
                            "changes": "area/road_changes.shp",
                        }
                    },
                    "temporal": {},
                    "evaluation": {},
                }
            }
        }
        events = result_events_from_index(index, index_path)
        by_type = {event["type"]: event for event in events}
        self.assertTrue(
            {"road_centerline", "road_surface", "road_width_segments", "road_change"}
            <= set(by_type)
        )
        self.assertEqual(by_type["road_change"]["before_period"], "2022")
        self.assertTrue(Path(by_type["road_change"]["path"]).is_absolute())

    def test_plugin_sources_have_no_host_or_heavy_imports(self) -> None:
        sources = "\n".join(path.read_text(encoding="utf-8") for path in (PLUGIN_ROOT / "plugin").glob("*.py"))
        forbidden = (
            "from core", "from modules", "from widgets", "from main_window",
            "import user_pipeline", "import torch", "import rasterio", "import osgeo",
            "import cv2", "import segment_anything", "C:\\Users\\",
        )
        self.assertFalse([value for value in forbidden if value in sources])


if __name__ == "__main__":
    unittest.main()
