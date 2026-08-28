from __future__ import annotations

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QWidget

from .metadata import PLUGIN_ID, PLUGIN_NAME, PLUGIN_VERSION
from .panel import RoadPanel
from .runner import RoadRunner


class RoadChangePlugin(QObject):
    """Stable public lifecycle and event boundary exposed to host programs."""

    plugin_id = PLUGIN_ID
    name = PLUGIN_NAME
    version = PLUGIN_VERSION

    task_started = Signal(dict)
    task_progress = Signal(dict)
    task_log = Signal(str)
    task_finished = Signal(dict)
    task_failed = Signal(str)
    result_ready = Signal(dict)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._runner = RoadRunner(self)
        self._runner.task_started.connect(self.task_started.emit)
        self._runner.task_progress.connect(self.task_progress.emit)
        self._runner.task_log.connect(self.task_log.emit)
        self._runner.task_finished.connect(self.task_finished.emit)
        self._runner.task_failed.connect(self.task_failed.emit)
        self._runner.result_ready.connect(self.result_ready.emit)

    def create_widget(self, parent: QWidget | None = None) -> QWidget:
        return RoadPanel(self._runner, parent)

    def shutdown(self) -> None:
        self._runner.shutdown()


def create_plugin(parent: QObject | None = None) -> RoadChangePlugin:
    return RoadChangePlugin(parent)

