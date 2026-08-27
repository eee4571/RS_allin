"""Small, versioned API implemented by independently updated modules."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence

from core.models import (
    Command,
    ModuleDescriptor,
    ResultTypeDefinition,
    ToolDefinition,
    WorkflowDefinition,
)
from core.project_context import ProjectContext


class ProcessingModule(ABC):
    module_id: str
    display_name: str
    module_version: str
    api_version: str

    @abstractmethod
    def workflows(self) -> Sequence[WorkflowDefinition]:
        raise NotImplementedError

    def tools(self) -> Sequence[ToolDefinition]:
        return ()

    def result_types(self) -> Sequence[ResultTypeDefinition]:
        return ()

    def descriptor(self) -> ModuleDescriptor:
        """Return the stable metadata boundary used by platform presentation."""
        return ModuleDescriptor(
            module_id=self.module_id,
            display_name=self.display_name,
            module_version=self.module_version,
            api_version=self.api_version,
            workflows=tuple(self.workflows()),
            tools=tuple(self.tools()),
            result_types=tuple(self.result_types()),
        )

    def set_project_context(self, context: ProjectContext) -> None:
        self.project_context = context

    @abstractmethod
    def handle_command(self, command: Command) -> None:
        raise NotImplementedError
