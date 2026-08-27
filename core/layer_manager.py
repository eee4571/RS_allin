"""Shared in-memory layer catalog fed entirely by layer events."""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal

from core.event_bus import EventBus
from core.models import LayerAdded, LayerRemoved, LayerUpdated


class LayerManager(QObject):
    layers_changed = Signal(object)

    def __init__(self, event_bus: EventBus) -> None:
        super().__init__()
        self._layers: dict[str, LayerAdded] = {}
        event_bus.layer_added.connect(self._on_added)
        event_bus.layer_removed.connect(self._on_removed)
        event_bus.layer_updated.connect(self._on_updated)

    def layers(self) -> tuple[LayerAdded, ...]:
        return tuple(self._layers.values())

    def _on_added(self, event: LayerAdded) -> None:
        self._layers[event.layer_id] = event
        self.layers_changed.emit(self.layers())

    def _on_removed(self, event: LayerRemoved) -> None:
        self._layers.pop(event.layer_id, None)
        self.layers_changed.emit(self.layers())

    def _on_updated(self, event: LayerUpdated) -> None:
        current = self._layers.get(event.layer_id)
        if current:
            data = dict(current.data or {})
            data.update(event.changes)
            self._layers[event.layer_id] = LayerAdded(
                current.module_id, current.layer_id, current.name, current.layer_type, data
            )
            self.layers_changed.emit(self.layers())

