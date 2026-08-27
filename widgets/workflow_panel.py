from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class ModulePanel(QWidget):
    """Empty platform-owned host for a future module operation panel."""

    def __init__(self, parent=None):
        super().__init__(parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setAlignment(Qt.AlignCenter)

        self.placeholder = QLabel("选择功能模块后在此显示操作面板")
        self.placeholder.setObjectName("modulePlaceholder")
        self.placeholder.setAlignment(Qt.AlignCenter)
        root.addWidget(self.placeholder)
