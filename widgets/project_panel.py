from __future__ import annotations

from collections.abc import Iterable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QToolButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)


class ProjectPanel(QWidget):
    """Platform project and layer browser backed by generic context data."""

    def __init__(self, context, parent=None):
        super().__init__(parent)
        self.context = context

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 10, 8, 8)
        root.setSpacing(7)

        search_row = QHBoxLayout()
        search_row.setContentsMargins(0, 0, 0, 0)
        search_row.setSpacing(5)
        self.search = QLineEdit()
        self.search.setPlaceholderText("搜索项目、图层……")
        self.filter_button = QToolButton()
        self.filter_button.setObjectName("panelToolButton")
        self.filter_button.setText("筛选")
        self.filter_button.setToolTip("筛选项目和图层")
        search_row.addWidget(self.search, 1)
        search_row.addWidget(self.filter_button)
        root.addLayout(search_row)

        self.project_tree = QTreeWidget()
        self.project_tree.setObjectName("projectTree")
        self.project_tree.setHeaderHidden(True)
        self.project_tree.setIndentation(16)
        self.tree = self.project_tree
        root.addWidget(self.project_tree, 3)

        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        root.addWidget(separator)

        layer_header = QLabel("图层")
        layer_header.setObjectName("sectionTitle")
        root.addWidget(layer_header)
        self.layer_tree = QTreeWidget()
        self.layer_tree.setObjectName("layerTree")
        self.layer_tree.setHeaderHidden(True)
        self.layer_tree.setIndentation(8)
        root.addWidget(self.layer_tree, 2)

        self.bottom_toolbar = QWidget()
        bottom_layout = QHBoxLayout(self.bottom_toolbar)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bottom_layout.setSpacing(2)
        for text, tooltip in (("↑", "上移"), ("↓", "下移"), ("↻", "刷新")):
            button = QToolButton()
            button.setObjectName("panelToolButton")
            button.setText(text)
            button.setToolTip(tooltip)
            if text == "↻":
                button.clicked.connect(self._populate_project_tree)
            bottom_layout.addWidget(button)
        manage_button = QToolButton()
        manage_button.setObjectName("panelToolButton")
        manage_button.setText("图层管理")
        manage_button.setToolTip("图层管理")
        bottom_layout.addWidget(manage_button)
        bottom_layout.addStretch(1)
        settings_button = QToolButton()
        settings_button.setObjectName("panelToolButton")
        settings_button.setText("⚙")
        settings_button.setToolTip("面板设置")
        bottom_layout.addWidget(settings_button)
        root.addWidget(self.bottom_toolbar)

        self.search.textChanged.connect(self._filter)
        self._populate_project_tree()
        self.set_layers(())

    def _populate_project_tree(self):
        self.project_tree.clear()
        project = QTreeWidgetItem([self.context.project_name or "当前项目"])
        self.project_tree.addTopLevelItem(project)
        project.setExpanded(True)

        if not self.context.areas:
            placeholder = QTreeWidgetItem(["尚未加载区域"])
            placeholder.setForeground(0, Qt.gray)
            project.addChild(placeholder)
            return

        for area_id, area in self.context.areas.items():
            area_item = QTreeWidgetItem([self._name(area, area_id)])
            project.addChild(area_item)
            area_item.setExpanded(True)
            for period, name in self.context.periods.items():
                area_item.addChild(QTreeWidgetItem([f"时相 {period} · {name}"]))

    def set_layers(self, layers: Iterable):
        self.layer_tree.clear()
        layers = tuple(layers)
        if not layers:
            placeholder = QTreeWidgetItem(["尚无图层"])
            placeholder.setForeground(0, Qt.gray)
            self.layer_tree.addTopLevelItem(placeholder)
            return
        for layer in layers:
            item = QTreeWidgetItem([layer.name])
            item.setToolTip(0, f"{layer.layer_type} · {layer.module_id}")
            item.setCheckState(0, Qt.Checked)
            self.layer_tree.addTopLevelItem(item)

    def _filter(self, value: str):
        value = value.strip().casefold()
        self._filter_tree(self.project_tree, value)
        self._filter_tree(self.layer_tree, value)

    @staticmethod
    def _filter_tree(tree: QTreeWidget, value: str):
        for index in range(tree.topLevelItemCount()):
            ProjectPanel._filter_item(tree.topLevelItem(index), value)

    @staticmethod
    def _filter_item(item: QTreeWidgetItem, value: str) -> bool:
        own_match = not value or value in item.text(0).casefold()
        child_match = False
        for index in range(item.childCount()):
            child_match = ProjectPanel._filter_item(item.child(index), value) or child_match
        item.setHidden(not (own_match or child_match))
        return own_match or child_match

    @staticmethod
    def _name(value, fallback: str) -> str:
        if isinstance(value, dict):
            return str(value.get("name", fallback))
        return str(value or fallback)
