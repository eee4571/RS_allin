from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget


class ProjectPanel(QWidget):
    def __init__(self, context, parent=None):
        super().__init__(parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 10, 8, 8)
        label = QLabel(context.project_name)
        label.setObjectName("panelTitleSmall")
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setIndentation(16)
        periods = QTreeWidgetItem(["时相数据"])
        for period, name in context.periods.items():
            periods.addChild(QTreeWidgetItem([f"{period} · {name}"]))
        self.layers_root = QTreeWidgetItem(["结果图层"])
        self.tree.addTopLevelItem(periods)
        self.tree.addTopLevelItem(self.layers_root)
        periods.setExpanded(True)
        self.layers_root.setExpanded(True)
        self.set_layers(())
        root.addWidget(label)
        root.addWidget(self.tree, 1)

    def set_layers(self, layers):
        self.layers_root.takeChildren()
        if not layers:
            placeholder = QTreeWidgetItem(["尚无结果图层"])
            placeholder.setForeground(0, Qt.gray)
            self.layers_root.addChild(placeholder)
        else:
            for layer in layers:
                item = QTreeWidgetItem([layer.name])
                item.setToolTip(0, f"{layer.layer_type} · {layer.module_id}")
                item.setCheckState(0, Qt.Checked)
                self.layers_root.addChild(item)
