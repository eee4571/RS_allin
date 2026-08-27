"""Qt-signal event boundary between plugins and presentation widgets."""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal

from core.models import (
    LayerAdded,
    LayerRemoved,
    LayerUpdated,
    ResultAvailable,
    SelectionChanged,
    TaskCompleted,
    TaskFailed,
    TaskLog,
    TaskProgress,
    TaskStarted,
    WorkflowStateChanged,
)


class EventBus(QObject):
    event_published = Signal(object)
    task_started = Signal(object)
    task_progress = Signal(object)
    task_log = Signal(object)
    task_completed = Signal(object)
    task_failed = Signal(object)
    layer_added = Signal(object)
    layer_removed = Signal(object)
    layer_updated = Signal(object)
    selection_changed = Signal(object)
    result_available = Signal(object)
    workflow_state_changed = Signal(object)

    _SIGNALS = {
        TaskStarted: "task_started",
        TaskProgress: "task_progress",
        TaskLog: "task_log",
        TaskCompleted: "task_completed",
        TaskFailed: "task_failed",
        LayerAdded: "layer_added",
        LayerRemoved: "layer_removed",
        LayerUpdated: "layer_updated",
        SelectionChanged: "selection_changed",
        ResultAvailable: "result_available",
        WorkflowStateChanged: "workflow_state_changed",
    }

    def publish(self, event: object) -> None:
        """Publish an immutable event without knowing any UI receiver."""
        self.event_published.emit(event)
        signal_name = self._SIGNALS.get(type(event))
        if signal_name:
            getattr(self, signal_name).emit(event)

