"""Stable data contracts shared by the shell and business plugins."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class ParameterDefinition:
    id: str
    name: str
    type: str
    default: Any = None
    options: tuple[Any, ...] = ()
    description: str = ""
    required: bool = False


@dataclass(frozen=True, slots=True)
class WorkflowStep:
    id: str
    name: str
    description: str = ""
    optional: bool = False


@dataclass(frozen=True, slots=True)
class WorkflowDefinition:
    id: str
    name: str
    icon: str
    description: str
    steps: tuple[WorkflowStep, ...]
    parameters: tuple[ParameterDefinition, ...] = ()
    category: str = "目标提取"
    order: int = 100


@dataclass(frozen=True, slots=True)
class ToolDefinition:
    id: str
    name: str
    icon: str = ""
    description: str = ""


@dataclass(frozen=True, slots=True)
class ResultTypeDefinition:
    id: str
    name: str
    geometry_type: str = "unknown"


@dataclass(frozen=True, slots=True)
class ModuleDescriptor:
    """Immutable public metadata exposed by a registered module.

    The platform may use this descriptor to present a module, but it never
    needs the module implementation object itself.
    """

    module_id: str
    display_name: str
    module_version: str
    api_version: str
    workflows: tuple[WorkflowDefinition, ...] = ()
    tools: tuple[ToolDefinition, ...] = ()
    result_types: tuple[ResultTypeDefinition, ...] = ()


@dataclass(frozen=True, slots=True)
class WorkflowCapability:
    """A workflow capability together with its public module metadata."""

    module: ModuleDescriptor
    workflow: WorkflowDefinition

    @property
    def module_id(self) -> str:
        return self.module.module_id


@dataclass(slots=True)
class Command:
    module_id: str
    workflow_id: str = ""
    action: str = "run"
    payload: dict[str, Any] = field(default_factory=dict)
    context: Any = None


@dataclass(frozen=True, slots=True)
class TaskStarted:
    module_id: str
    workflow_id: str
    message: str


@dataclass(frozen=True, slots=True)
class TaskProgress:
    module_id: str
    workflow_id: str
    progress: float
    message: str
    step_id: str = ""


@dataclass(frozen=True, slots=True)
class TaskLog:
    module_id: str
    workflow_id: str
    message: str
    level: str = "INFO"


@dataclass(frozen=True, slots=True)
class TaskCompleted:
    module_id: str
    workflow_id: str
    message: str
    result: Any = None


@dataclass(frozen=True, slots=True)
class TaskFailed:
    module_id: str
    workflow_id: str
    message: str


@dataclass(frozen=True, slots=True)
class LayerAdded:
    module_id: str
    layer_id: str
    name: str
    layer_type: str
    data: Any = None


@dataclass(frozen=True, slots=True)
class LayerRemoved:
    layer_id: str


@dataclass(frozen=True, slots=True)
class LayerUpdated:
    layer_id: str
    changes: dict[str, Any]


@dataclass(frozen=True, slots=True)
class SelectionChanged:
    layer_id: str
    feature_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ResultAvailable:
    module_id: str
    workflow_id: str
    result_type: str
    name: str
    data: Any = None


@dataclass(frozen=True, slots=True)
class WorkflowStateChanged:
    module_id: str
    workflow_id: str
    state: str
    step_id: str = ""
