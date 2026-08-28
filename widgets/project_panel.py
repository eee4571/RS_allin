from __future__ import annotations

from collections.abc import Iterable

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLineEdit,
    QMenu,
    QStyle,
    QToolButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)


class ProjectPanel(QWidget):
    """Unified project/layer tree backed only by generic project contracts."""

    visible_layers_changed = Signal(object)
    layer_selected = Signal(str)
    layer_activated = Signal(str)

    LAYER_ID_ROLE = Qt.UserRole
    NODE_KIND_ROLE = Qt.UserRole + 1

    def __init__(self, context, parent=None):
        super().__init__(parent)
        self.context = context
        self._layers = ()
        self._visibility: dict[str, bool] = {}
        self._updating_tree = False

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 10, 8, 8)
        root.setSpacing(7)

        search_row = QHBoxLayout()
        search_row.setContentsMargins(0, 0, 0, 0)
        search_row.setSpacing(5)
        self.search = QLineEdit()
        self.search.setPlaceholderText("搜索区域、时相或图层……")
        self.filter_button = QToolButton()
        self.filter_button.setObjectName("panelToolButton")
        self.filter_button.setText("筛选")
        self.filter_button.setToolTip("筛选项目和图层")
        search_row.addWidget(self.search, 1)
        search_row.addWidget(self.filter_button)
        root.addLayout(search_row)

        self.tree = QTreeWidget()
        self.tree.setObjectName("projectTree")
        self.tree.setHeaderHidden(True)
        self.tree.setIndentation(16)
        self.tree.setSelectionMode(QTreeWidget.SingleSelection)
        self.tree.setDragEnabled(True)
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        root.addWidget(self.tree, 1)
        self.project_tree = self.tree

        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(0, 0, 0, 0)
        toolbar.setSpacing(2)
        refresh = QToolButton()
        refresh.setObjectName("panelToolButton")
        refresh.setText("刷新")
        refresh.clicked.connect(self._populate_tree)
        toolbar.addWidget(refresh)
        toolbar.addStretch(1)
        root.addLayout(toolbar)

        self.search.textChanged.connect(self._filter)
        self.tree.itemChanged.connect(self._on_item_changed)
        self.tree.itemSelectionChanged.connect(self._on_selection_changed)
        self.tree.itemDoubleClicked.connect(self._on_item_activated)
        self.tree.customContextMenuRequested.connect(self._show_context_menu)
        self._populate_tree()

    @property
    def selected_layer_id(self) -> str:
        item = self.tree.currentItem()
        return str(item.data(0, self.LAYER_ID_ROLE) or "") if item else ""

    def set_layers(self, layers: Iterable):
        self._layers = tuple(layers)
        current_ids = {layer.layer_id for layer in self._layers}
        self._visibility = {
            layer_id: visible
            for layer_id, visible in self._visibility.items()
            if layer_id in current_ids
        }
        for layer_id in current_ids:
            self._visibility.setdefault(layer_id, True)
        self._populate_tree()
        self._emit_visible_layers()

    def _populate_tree(self):
        self._updating_tree = True
        self.tree.clear()
        project = self._item(
            self.context.project_name or "当前项目", "project", QStyle.SP_DirHomeIcon
        )
        self.tree.addTopLevelItem(project)
        project.setExpanded(True)

        areas = self.context.areas or {}
        if areas:
            for area_id, area in areas.items():
                area_item = self._item(
                    self._name(area, area_id), "area", QStyle.SP_DirIcon
                )
                area_item.setData(0, Qt.UserRole + 2, area_id)
                project.addChild(area_item)
                area_item.setExpanded(True)
                self._add_area_structure(area_item, area_id)
        else:
            empty = self._item("尚未加载区域", "placeholder")
            empty.setForeground(0, Qt.gray)
            project.addChild(empty)

        public = self._item("公共数据", "public", QStyle.SP_DirIcon)
        project.addChild(public)
        public.setExpanded(True)
        assigned = {
            layer.layer_id
            for layer in self._layers
            if self._layer_metadata(layer).get("area_id") in areas
        }
        for layer in self._layers:
            if layer.layer_id not in assigned:
                public.addChild(self._layer_item(layer))
        if public.childCount() == 0:
            placeholder = self._item("尚无公共图层", "placeholder")
            placeholder.setForeground(0, Qt.gray)
            public.addChild(placeholder)

        self._updating_tree = False
        self._filter(self.search.text())

    def _add_area_structure(self, area_item, area_id):
        raw = self._item("原始数据", "raw", QStyle.SP_DirIcon)
        results = self._item("成果", "results", QStyle.SP_DirIcon)
        area_item.addChildren((raw, results))
        raw.setExpanded(True)
        results.setExpanded(True)

        for period, name in self.context.periods.items():
            raw.addChild(self._item(f"{period} · {name}", "period", QStyle.SP_FileIcon))

        area_layers = [
            layer
            for layer in self._layers
            if self._layer_metadata(layer).get("area_id") == area_id
        ]
        groups: dict[str, QTreeWidgetItem] = {}
        for layer in area_layers:
            metadata = self._layer_metadata(layer)
            group_name = str(metadata.get("group") or layer.layer_type or "其他成果")
            group = groups.get(group_name)
            if group is None:
                group = self._item(group_name, "result_group", QStyle.SP_DirIcon)
                results.addChild(group)
                groups[group_name] = group
            group.addChild(self._layer_item(layer))
        if not area_layers:
            placeholder = self._item("尚无成果", "placeholder")
            placeholder.setForeground(0, Qt.gray)
            results.addChild(placeholder)

    def _layer_item(self, layer):
        item = self._item(layer.name, "layer", QStyle.SP_FileIcon)
        item.setData(0, self.LAYER_ID_ROLE, layer.layer_id)
        item.setToolTip(0, f"{layer.layer_type} · {layer.module_id}")
        item.setFlags(
            item.flags()
            | Qt.ItemIsUserCheckable
            | Qt.ItemIsSelectable
            | Qt.ItemIsDragEnabled
        )
        item.setCheckState(
            0, Qt.Checked if self._visibility.get(layer.layer_id, True) else Qt.Unchecked
        )
        return item

    def _item(self, text, kind, standard_icon=None):
        item = QTreeWidgetItem([text])
        item.setData(0, self.NODE_KIND_ROLE, kind)
        if standard_icon is not None:
            item.setIcon(0, self.style().standardIcon(standard_icon))
        return item

    def _on_item_changed(self, item, column):
        if self._updating_tree or column != 0:
            return
        layer_id = item.data(0, self.LAYER_ID_ROLE)
        if not layer_id:
            return
        self._visibility[str(layer_id)] = item.checkState(0) == Qt.Checked
        self._emit_visible_layers()

    def _emit_visible_layers(self):
        visible = tuple(
            layer
            for layer in self._layers
            if self._visibility.get(layer.layer_id, True)
        )
        self.visible_layers_changed.emit(visible)

    def _on_selection_changed(self):
        layer_id = self.selected_layer_id
        if layer_id:
            self.layer_selected.emit(layer_id)

    def _on_item_activated(self, item, column):
        layer_id = item.data(0, self.LAYER_ID_ROLE)
        if layer_id:
            self.layer_activated.emit(str(layer_id))

    def _show_context_menu(self, position):
        item = self.tree.itemAt(position)
        if item is None:
            return
        layer_id = item.data(0, self.LAYER_ID_ROLE)
        if not layer_id:
            return
        menu = QMenu(self)
        zoom = QAction("缩放至图层", self)
        zoom.triggered.connect(lambda: self.layer_activated.emit(str(layer_id)))
        menu.addAction(zoom)
        menu.exec(self.tree.viewport().mapToGlobal(position))

    def _filter(self, value: str):
        value = value.strip().casefold()
        for index in range(self.tree.topLevelItemCount()):
            self._filter_item(self.tree.topLevelItem(index), value)

    @staticmethod
    def _filter_item(item: QTreeWidgetItem, value: str) -> bool:
        own_match = not value or value in item.text(0).casefold()
        child_match = False
        for index in range(item.childCount()):
            child_match = ProjectPanel._filter_item(item.child(index), value) or child_match
        item.setHidden(not (own_match or child_match))
        return own_match or child_match

    @staticmethod
    def _layer_metadata(layer) -> dict:
        return layer.data if isinstance(layer.data, dict) else {}

    @staticmethod
    def _name(value, fallback: str) -> str:
        if isinstance(value, dict):
            return str(value.get("name", fallback))
        return str(value or fallback)
