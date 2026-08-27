"""Small, versioned API implemented by independently updated modules."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence

from core.models import Command, ResultTypeDefinition, ToolDefinition, WorkflowDefinition
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

    def set_project_context(self, context: ProjectContext) -> None:
        self.project_context = context

    @abstractmethod
    def handle_command(self, command: Command) -> None:
        raise NotImplementedError

