from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSignalBlocker, QSize, Qt, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QButtonGroup,
    QHBoxLayout,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)


class Ribbon(QWidget):
    """Top-level platform navigation, independent of business modules."""

    module_selected = Signal(str)

    MODULES = (
        ("road_change_detection", "道路变化检测", "road_change.svg"),
        ("building_change_detection", "建筑物变化检测", "building_change.svg"),
        ("building_entity_extraction", "建筑实体提取及位移校正", "building_extract.svg"),
        ("agent", "智能体", "agent.svg"),
    )

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ribbon")
        self._buttons: dict[str, QToolButton] = {}
        self._button_group = QButtonGroup(self)
        self._button_group.setExclusive(True)

        root = QVBoxLayout(self)
        root.setContentsMargins(14, 8, 14, 8)
        root.setSpacing(4)

        buttons = QHBoxLayout()
        buttons.setContentsMargins(0, 0, 0, 0)
        buttons.setSpacing(8)
        for module_id, name, icon in self.MODULES:
            button = QToolButton()
            button.setObjectName("ribbonButton")
            button.setCheckable(True)
            button.setText(name)
            button.setToolTip(name)
            button.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
            icon_path = Path(__file__).resolve().parents[1] / "assets" / "icons" / icon
            button.setIcon(QIcon(str(icon_path)))
            button.setIconSize(QSize(20, 20))
            button.setMinimumWidth(150)
            button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
            button.clicked.connect(
                lambda checked=False, value=module_id: self._select(value)
            )
            self._button_group.addButton(button)
            self._buttons[module_id] = button
            buttons.addWidget(button, 1)

        first_id = self.MODULES[0][0]
        self._buttons[first_id].setChecked(True)
        root.addLayout(buttons)

    @property
    def selected_module_id(self) -> str:
        for module_id, button in self._buttons.items():
            if button.isChecked():
                return module_id
        return ""

    def _select(self, module_id: str) -> None:
        button = self._buttons[module_id]
        with QSignalBlocker(button):
            button.setChecked(True)
        self.module_selected.emit(module_id)
