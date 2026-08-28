"""Plugin discovery, API compatibility checks, and command routing."""

from __future__ import annotations

import importlib
import pkgutil
from dataclasses import dataclass
from typing import Any, Callable

from core.event_bus import EventBus
from core.models import Command, ModuleDescriptor, WorkflowCapability, WorkflowDefinition
from core.module_api import ProcessingModule
from core.project_context import ProjectContext


@dataclass(frozen=True, slots=True)
class DisabledModule:
    module_id: str
    display_name: str
    api_version: str
    reason: str


class ModuleRegistry:
    SUPPORTED_API_VERSION = "1"

    def __init__(self, event_bus: EventBus, project_context: ProjectContext) -> None:
        self._event_bus = event_bus
        self._project_context = project_context
        self._modules: dict[str, ProcessingModule] = {}
        self._descriptors: dict[str, ModuleDescriptor] = {}
        self._disabled: list[DisabledModule] = []
        self._operation_page_factories: dict[str, Callable[..., Any]] = {}

    def register(self, module: ProcessingModule) -> bool:
        if module.api_version != self.SUPPORTED_API_VERSION:
            self._disabled.append(
                DisabledModule(
                    module.module_id,
                    module.display_name,
                    module.api_version,
                    f"接口版本不兼容：模块为 {module.api_version}，主程序支持 {self.SUPPORTED_API_VERSION}",
                )
            )
            return False
        if module.module_id in self._modules:
            raise ValueError(f"模块 ID 重复：{module.module_id}")
        module.set_project_context(self._project_context)
        descriptor = module.descriptor()
        if descriptor.module_id != module.module_id:
            raise ValueError(f"模块描述信息与实现不一致：{module.module_id}")
        self._modules[module.module_id] = module
        self._descriptors[module.module_id] = descriptor
        return True

    def discover(self, package_name: str = "modules") -> list[str]:
        """Discover packages exposing create_plugin(event_bus), safely isolating failures."""
        errors: list[str] = []
        package = importlib.import_module(package_name)
        for item in pkgutil.iter_modules(package.__path__, f"{package_name}."):
            if not item.ispkg:
                continue
            plugin_module_name = f"{item.name}.plugin"
            try:
                plugin_module = importlib.import_module(plugin_module_name)
                factory = getattr(plugin_module, "create_plugin")
                module = factory(self._event_bus)
                if self.register(module):
                    page_factory = getattr(
                        plugin_module, "create_operation_page", None
                    )
                    if callable(page_factory):
                        self._operation_page_factories[module.module_id] = page_factory
            except Exception as exc:  # one broken plugin must not break the shell
                errors.append(f"{plugin_module_name}: {exc}")
        return errors

    def modules(self) -> tuple[ProcessingModule, ...]:
        return tuple(self._modules.values())

    def descriptors(self) -> tuple[ModuleDescriptor, ...]:
        """Return immutable metadata for platform presentation and reporting."""
        return tuple(self._descriptors.values())

    def disabled_modules(self) -> tuple[DisabledModule, ...]:
        return tuple(self._disabled)

    def operation_page_factories(self) -> dict[str, Callable[..., Any]]:
        """Return optional module-owned page factories as opaque extensions."""
        return dict(self._operation_page_factories)

    def get(self, module_id: str) -> ProcessingModule:
        try:
            return self._modules[module_id]
        except KeyError as exc:
            raise KeyError(f"未找到可用模块：{module_id}") from exc

    def capability(self, module_id: str, workflow_id: str) -> WorkflowCapability:
        descriptor = self._descriptors.get(module_id)
        if descriptor is None:
            raise KeyError(f"未找到可用模块：{module_id}")
        for workflow in descriptor.workflows:
            if workflow.id == workflow_id:
                return WorkflowCapability(descriptor, workflow)
        raise KeyError(f"模块 {module_id} 中不存在工作流 {workflow_id}")

    def workflow(self, module_id: str, workflow_id: str) -> WorkflowDefinition:
        return self.capability(module_id, workflow_id).workflow

    def all_workflows(self) -> tuple[WorkflowCapability, ...]:
        result = [
            WorkflowCapability(descriptor, workflow)
            for descriptor in self.descriptors()
            for workflow in descriptor.workflows
        ]
        return tuple(sorted(result, key=lambda item: (item.workflow.category, item.workflow.order)))

    def dispatch(self, command: Command) -> None:
        self.get(command.module_id).handle_command(command)
