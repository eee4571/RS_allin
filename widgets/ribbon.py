from __future__ import annotations

from collections import defaultdict

from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QToolButton,
    QVBoxLayout,
    QWidget,
)


class Ribbon(QWidget):
    workflow_selected = Signal(str, str)

    def __init__(self, registry, parent=None):
        super().__init__(parent)
        self.setObjectName("ribbon")
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 8, 14, 8)
        root.setSpacing(4)

        sections = QHBoxLayout()
        sections.setSpacing(8)
        grouped = defaultdict(list)
        for module, workflow in registry.all_workflows():
            grouped[workflow.category].append((module, workflow))

        for category, workflows in grouped.items():
            section = QFrame()
            section.setObjectName("ribbonSection")
            section_layout = QVBoxLayout(section)
            section_layout.setContentsMargins(8, 5, 8, 5)
            buttons = QHBoxLayout()
            buttons.setSpacing(4)
            for module, workflow in workflows:
                button = QToolButton()
                button.setObjectName("ribbonButton")
                button.setText(f"{workflow.icon}\n{workflow.name}")
                button.setToolTip(f"{module.display_name} · v{module.module_version}\n{workflow.description}")
                button.setToolButtonStyle(Qt.ToolButtonTextOnly)
                button.setMinimumWidth(96)
                button.clicked.connect(
                    lambda checked=False, m=module.module_id, w=workflow.id:
                    self.workflow_selected.emit(m, w)
                )
                buttons.addWidget(button)
            section_layout.addLayout(buttons)
            label = QLabel(category)
            label.setObjectName("ribbonCategory")
            label.setAlignment(Qt.AlignCenter)
            section_layout.addWidget(label)
            sections.addWidget(section)

        sections.addStretch(1)
        holder = QWidget()
        holder.setLayout(sections)
        scroll = QScrollArea()
        scroll.setObjectName("ribbonScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setWidget(holder)
        root.addWidget(scroll)

