import os
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from core.event_bus import EventBus
from core.models import Command, TaskFailed, WorkflowDefinition, WorkflowStep
from core.module_api import ProcessingModule
from core.module_registry import ModuleRegistry
from core.project_context import ProjectContext


class IncompatiblePlugin(ProcessingModule):
    module_id = "future"
    display_name = "未来模块"
    module_version = "9.0.0"
    api_version = "2"

    def workflows(self):
        return ()

    def handle_command(self, command):
        raise AssertionError("disabled module must never receive commands")


class ArchitectureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.bus = EventBus()
        self.registry = ModuleRegistry(self.bus, ProjectContext())
        self.errors = self.registry.discover()

    def test_three_plugins_are_discovered_without_shell_imports(self):
        self.assertEqual([], self.errors)
        self.assertEqual(
            {"road", "building_extract", "building_change"},
            {module.module_id for module in self.registry.modules()},
        )
        self.assertEqual(6, len(self.registry.all_workflows()))

    def test_workflows_are_owned_by_plugins(self):
        road_ids = {workflow.id for workflow in self.registry.get("road").workflows()}
        self.assertIn("road_timeseries", road_ids)
        self.assertEqual(
            {"building_extraction", "building_quantification"},
            {item.id for item in self.registry.get("building_extract").workflows()},
        )

    def test_incompatible_plugin_is_disabled_without_crash(self):
        self.assertFalse(self.registry.register(IncompatiblePlugin()))
        disabled = self.registry.disabled_modules()
        self.assertEqual(1, len(disabled))
        self.assertIn("主程序支持 1", disabled[0].reason)

    def test_shell_has_no_concrete_module_or_adapter_import(self):
        root = Path(__file__).parents[1]
        shell = (root / "main_window.py").read_text(encoding="utf-8")
        startup = (root / "main.py").read_text(encoding="utf-8")
        combined = shell + startup
        for forbidden in (
            "RoadPlugin", "RoadAdapter", "BuildingExtractPlugin",
            "BuildingExtractAdapter", "BuildingChangePlugin", "BuildingChangeAdapter",
        ):
            self.assertNotIn(forbidden, combined)

    def test_event_bus_exposes_plugin_to_ui_event_boundary(self):
        received = []
        self.bus.task_failed.connect(received.append)
        event = TaskFailed("road", "road_extraction", "sample")
        self.bus.publish(event)
        self.assertEqual([event], received)


if __name__ == "__main__":
    unittest.main()

