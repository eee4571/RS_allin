"""Single entry point for all business commands emitted by the GUI."""

from __future__ import annotations

from core.event_bus import EventBus
from core.models import Command, TaskFailed
from core.module_registry import ModuleRegistry


class CommandBus:
    def __init__(self, registry: ModuleRegistry, event_bus: EventBus) -> None:
        self._registry = registry
        self._event_bus = event_bus

    def dispatch(self, command: Command) -> None:
        try:
            self._registry.dispatch(command)
        except Exception as exc:
            self._event_bus.publish(
                TaskFailed(command.module_id, command.workflow_id, str(exc))
            )

