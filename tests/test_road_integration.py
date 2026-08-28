import json
import os
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QPushButton

from core.command_bus import CommandBus
from core.event_bus import EventBus
from core.layer_manager import LayerManager
from core.models import Command
from core.module_registry import ModuleRegistry
from core.project_context import ProjectContext
from modules.road.adapter import RoadAdapter
from modules.road.contracts import RoadJob, RoadWorkerEvent
from modules.road.ui.road_panel import RoadPanel
from widgets.ribbon import Ribbon
from widgets.workflow_panel import ModuleOperationPage, ModulePanel


class RoadIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def make_context(self):
        return ProjectContext(
            project_name="道路测试工程",
            project_root="project",
            periods={"2020": "影像", "2022": "影像", "2024": "影像"},
            areas={"area-a": {"name": "区域 A"}},
            inputs={
                "area-a": {
                    "validation_area": "inputs/area-a/validation.geojson",
                    "imagery": {
                        "2020": "inputs/area-a/2020.tif",
                        "2022": "inputs/area-a/2022.tif",
                        "2024": "inputs/area-a/2024.tif",
                    },
                }
            },
            output_root="results",
        )

    def make_registry(self, context=None):
        bus = EventBus()
        registry = ModuleRegistry(bus, context or self.make_context())
        self.assertEqual([], registry.discover())
        return bus, registry

    def test_registry_discovers_stable_road_module_and_ui_factory(self):
        _, registry = self.make_registry()
        self.assertEqual("road", registry.get("road").module_id)
        self.assertIn("road", registry.operation_page_factories())

    def test_custom_road_page_and_generic_pages_coexist(self):
        context = self.make_context()
        _, registry = self.make_registry(context)
        panel = ModulePanel(
            navigation=tuple((module_id, title) for module_id, title in Ribbon.MODULES),
            descriptors=registry.descriptors(),
            page_factories=registry.operation_page_factories(),
            project_context=context,
        )
        self.assertIsInstance(panel.stack.currentWidget(), RoadPanel)
        panel.show_module("building_change")
        self.assertIsInstance(panel.stack.currentWidget(), ModuleOperationPage)

    def test_road_panel_modes_emit_only_stable_commands(self):
        context = self.make_context()
        panel = RoadPanel(project_context=context)
        commands = []
        panel.command_requested.connect(commands.append)

        panel.run_full_button.click()
        self.assertEqual("road", commands[-1].module_id)
        self.assertEqual("full_pipeline", commands[-1].workflow_id)
        self.assertEqual(["2020", "2022", "2024"], commands[-1].payload["periods"])

        panel.local_button.click()
        self.assertEqual(1, panel.mode_stack.currentIndex())
        panel.rerun_period_button.click()
        self.assertEqual("rerun_period", commands[-1].workflow_id)
        panel.rerun_change_button.click()
        self.assertEqual("rerun_change_pair", commands[-1].workflow_id)
        self.assertTrue(
            all("人工编辑" not in button.text() for button in panel.findChildren(QPushButton))
        )

        source = Path(__file__).parents[1] / "modules" / "road" / "ui" / "road_panel.py"
        text = source.read_text(encoding="utf-8")
        self.assertNotIn("RoadAdapter", text)
        self.assertNotIn("handle_command", text)

    def test_road_panel_tracks_platform_task_state(self):
        panel = RoadPanel(project_context=self.make_context())
        panel.update_task_state(
            "full_pipeline", "running", "正在提取道路", 0.3, "extract"
        )
        self.assertIn("进行", panel.steps.item(1).text())
        self.assertFalse(panel.run_full_button.isEnabled())
        panel.update_task_state(
            "full_pipeline", "completed", "处理完成", 1.0, ""
        )
        self.assertTrue(
            all("完成" in panel.steps.item(index).text() for index in range(5))
        )
        self.assertTrue(panel.run_full_button.isEnabled())

    def test_road_job_and_worker_event_are_json_serializable(self):
        job = RoadJob(
            job_id="job-1",
            action="full_pipeline",
            project_root="project",
            area_id="area-a",
            periods=("2022", "2024"),
            input_manifest={"imagery": {"2022": "a.tif"}},
            output_root="results",
            options={"device": "CPU"},
        )
        restored = RoadJob.from_dict(json.loads(job.to_json()))
        self.assertEqual(job, restored)
        path_job = RoadJob(
            job_id="job-path",
            action="rerun_period",
            input_manifest={"image": Path("inputs/2024.tif")},
        )
        self.assertEqual(
            str(Path("inputs/2024.tif")),
            json.loads(path_job.to_json())["input_manifest"]["image"],
        )
        event = RoadWorkerEvent.from_json_line(
            '{"type":"progress","step":"extract","progress":0.25,'
            '"message":"正在提取道路"}'
        )
        self.assertEqual(("progress", "extract", 0.25), (
            event.type, event.step, event.progress
        ))

    def test_adapter_builds_job_from_project_context_not_file_picker_payloads(self):
        context = self.make_context()
        adapter = RoadAdapter(EventBus())
        adapter.set_project_context(context)
        job = adapter.build_job(
            Command(
                "road",
                "rerun_period",
                payload={"area_id": "area-a", "period": "2022", "device": "CPU"},
            )
        )
        self.assertEqual("project", job.project_root)
        self.assertEqual("results", job.output_root)
        self.assertIn("imagery", job.input_manifest)
        self.assertEqual(("2022",), job.periods)
        self.assertEqual({"device": "CPU", "update_related": True}, job.options)

    def test_mock_adapter_events_and_results_follow_platform_path(self):
        context = self.make_context()
        bus, registry = self.make_registry(context)
        manager = LayerManager(bus)
        started = []
        progress = []
        completed = []
        results = []
        bus.task_started.connect(started.append)
        bus.task_progress.connect(progress.append)
        bus.task_completed.connect(completed.append)
        bus.result_available.connect(results.append)
        registry.get("road")._adapter._mock_interval_ms = 1

        CommandBus(registry, bus).dispatch(
            Command(
                "road",
                "full_pipeline",
                payload={
                    "area_id": "area-a",
                    "periods": ["2022", "2024"],
                    "device": "CPU",
                },
            )
        )
        QTest.qWait(80)

        self.assertEqual("full_pipeline", started[0].workflow_id)
        self.assertTrue(progress)
        self.assertEqual("full_pipeline", completed[0].workflow_id)
        self.assertEqual(4, len(results))
        self.assertEqual(
            {"road_centerline", "road_surface", "road_width", "road_change"},
            {layer.layer_type for layer in manager.layers()},
        )
        self.assertTrue(
            all(layer.data["area_id"] == "area-a" for layer in manager.layers())
        )

    def test_road_adapter_is_not_a_timed_mock_subclass(self):
        from core.mock_adapter import TimedMockAdapter

        self.assertFalse(issubclass(RoadAdapter, TimedMockAdapter))

    def test_road_module_has_no_algorithm_environment_imports(self):
        road_root = Path(__file__).parents[1] / "modules" / "road"
        source = "\n".join(
            path.read_text(encoding="utf-8") for path in road_root.rglob("*.py")
        ).casefold()
        for forbidden in (
            "import torch", "from torch", "import osgeo", "from osgeo",
            "import rasterio", "from rasterio", "import cv2", "segment_anything",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
