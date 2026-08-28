from __future__ import annotations

from PySide6.QtCore import QSignalBlocker, Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QHBoxLayout,
    QSizePolicy,
    QToolButton,
    QWidget,
)


class Ribbon(QWidget):
    """Top-level platform navigation, independent of business modules."""

    module_selected = Signal(str)

    MODULES = (
        ("road", "道路变化检测"),
        ("building_change", "建筑物变化检测"),
        ("building_extract", "建筑实体提取及位移校正"),
        ("agent", "智能体"),
    )

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ribbon")
        self._buttons: dict[str, QToolButton] = {}
        self._button_group = QButtonGroup(self)
        self._button_group.setExclusive(True)

        buttons = QHBoxLayout(self)
        buttons.setContentsMargins(12, 0, 12, 0)
        buttons.setSpacing(2)
        for module_id, name in self.MODULES:
            button = QToolButton()
            button.setObjectName("ribbonButton")
            button.setCheckable(True)
            button.setText(name)
            button.setToolTip(name)
            button.setToolButtonStyle(Qt.ToolButtonTextOnly)
            button.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
            button.clicked.connect(
                lambda checked=False, value=module_id: self._select(value)
            )
            self._button_group.addButton(button)
            self._buttons[module_id] = button
            buttons.addWidget(button)

        first_id = self.MODULES[0][0]
        self._buttons[first_id].setChecked(True)
        buttons.addStretch(1)

    @classmethod
    def labels(cls) -> dict[str, str]:
        return {module_id: name for module_id, name in cls.MODULES}

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
