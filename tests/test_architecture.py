import os
import unittest
from types import SimpleNamespace
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QPushButton, QToolButton

from core.event_bus import EventBus
from core.command_bus import CommandBus
from core import module_registry as module_registry_impl
from core.models import (
    Command,
    ModuleDescriptor,
    TaskFailed,
    WorkflowCapability,
    WorkflowDefinition,
    WorkflowStep,
)
from core.module_api import ProcessingModule
from core.module_registry import ModuleRegistry
from core.project_context import ProjectContext
from widgets.ribbon import Ribbon
from widgets.workflow_panel import ModulePanel


class IncompatiblePlugin(ProcessingModule):
    module_id = "future"
    display_name = "未来模块"
    module_version = "9.0.0"
    api_version = "2"

    def workflows(self):
        return ()

    def handle_command(self, command):
        raise AssertionError("disabled module must never receive commands")


class RecordingModule(ProcessingModule):
    module_id = "recording"
    display_name = "测试模块"
    module_version = "0.0.1"
    api_version = "1"

    def __init__(self):
        self.commands = []

    def workflows(self):
        return (WorkflowDefinition("record", "记录命令", "T", "", (WorkflowStep("run", "运行"),)),)

    def handle_command(self, command):
        self.commands.append(command)


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

    def test_presentation_receives_descriptors_not_module_implementations(self):
        capabilities = self.registry.all_workflows()
        self.assertTrue(all(isinstance(item, WorkflowCapability) for item in capabilities))
        self.assertTrue(all(isinstance(item.module, ModuleDescriptor) for item in capabilities))
        self.assertFalse(hasattr(capabilities[0].module, "handle_command"))
        self.assertEqual("road", self.registry.capability("road", "road_extraction").module_id)

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

    def test_modules_do_not_import_platform_presentation(self):
        root = Path(__file__).parents[1]
        forbidden = ("main_window", "widgets.map_view", "widgets.log_panel", "widgets.project_panel", "widgets.ribbon")
        for path in (root / "modules").rglob("*.py"):
            source = path.read_text(encoding="utf-8")
            for value in forbidden:
                self.assertNotIn(value, source, path)

    def test_generic_widgets_do_not_import_business_modules(self):
        root = Path(__file__).parents[1]
        for path in (root / "widgets").rglob("*.py"):
            source = path.read_text(encoding="utf-8")
            self.assertNotIn("from modules.", source, path)
            self.assertNotIn("import modules.", source, path)

    def test_generic_map_view_has_no_business_module_branch(self):
        root = Path(__file__).parents[1]
        source = (root / "widgets" / "map_view.py").read_text(encoding="utf-8")
        self.assertNotIn("building", source.lower())
        self.assertNotIn("road", source.lower())

    def test_main_navigation_has_four_independent_entries(self):
        ribbon = Ribbon()
        self.assertEqual(
            ["道路变化检测", "建筑物变化检测", "建筑实体提取及位移校正", "智能体"],
            [name for _, name, _ in ribbon.MODULES],
        )
        self.assertEqual("road_change_detection", ribbon.selected_module_id)
        emitted = []
        ribbon.module_selected.connect(emitted.append)
        ribbon._buttons["agent"].click()
        self.assertEqual(["agent"], emitted)
        self.assertEqual("agent", ribbon.selected_module_id)

    def test_module_panel_is_empty_host(self):
        panel = ModulePanel()
        self.assertEqual("选择功能模块后在此显示操作面板", panel.placeholder.text())
        self.assertEqual([], panel.findChildren(QPushButton))
        self.assertEqual([], panel.findChildren(QToolButton))

    def test_broken_plugin_isolated_during_discovery(self):
        good = SimpleNamespace(create_plugin=lambda event_bus: RecordingModule())
        package = SimpleNamespace(__path__=[])

        def import_side_effect(name):
            if name == "fake_modules":
                return package
            if name == "fake_modules.good.plugin":
                return good
            if name == "fake_modules.broken.plugin":
                raise RuntimeError("broken plugin")
            raise AssertionError(name)

        items = (
            SimpleNamespace(name="fake_modules.good", ispkg=True),
            SimpleNamespace(name="fake_modules.broken", ispkg=True),
        )
        registry = ModuleRegistry(self.bus, ProjectContext())
        with patch.object(module_registry_impl.importlib, "import_module", side_effect=import_side_effect), \
                patch.object(module_registry_impl.pkgutil, "iter_modules", return_value=items):
            errors = registry.discover("fake_modules")
        self.assertEqual(1, len(errors))
        self.assertEqual(("recording",), tuple(item.module_id for item in registry.descriptors()))

    def test_command_bus_routes_to_module_implementation(self):
        registry = ModuleRegistry(self.bus, ProjectContext())
        module = RecordingModule()
        self.assertTrue(registry.register(module))
        CommandBus(registry, self.bus).dispatch(Command("recording", "record", payload={"x": 1}))
        self.assertEqual("record", module.commands[0].workflow_id)

    def test_replacing_module_implementation_keeps_platform_contract(self):
        replacement = RecordingModule()
        registry = ModuleRegistry(self.bus, ProjectContext())
        registry.register(replacement)
        capability = registry.capability("recording", "record")
        self.assertEqual("recording", capability.module_id)
        CommandBus(registry, self.bus).dispatch(Command(capability.module_id, capability.workflow.id))
        self.assertEqual(1, len(replacement.commands))

    def test_event_bus_exposes_plugin_to_ui_event_boundary(self):
        received = []
        self.bus.task_failed.connect(received.append)
        event = TaskFailed("road", "road_extraction", "sample")
        self.bus.publish(event)
        self.assertEqual([event], received)


if __name__ == "__main__":
    unittest.main()
