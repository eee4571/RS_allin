from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)


class PathEditor(QWidget):
    def __init__(self, directory=False, parent=None):
        super().__init__(parent)
        self._directory = directory
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        self.edit = QLineEdit()
        self.edit.setPlaceholderText("请选择目录" if directory else "请选择文件")
        button = QPushButton("浏览")
        button.setObjectName("secondaryButton")
        button.clicked.connect(self._browse)
        layout.addWidget(self.edit, 1)
        layout.addWidget(button)

    def _browse(self):
        if self._directory:
            value = QFileDialog.getExistingDirectory(self, "选择目录", self.edit.text())
        else:
            value, _ = QFileDialog.getOpenFileName(self, "选择文件", self.edit.text())
        if value:
            self.edit.setText(value)

    def value(self):
        return self.edit.text().strip()


class ParameterPanel(QWidget):
    values_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(9)
        self._editors = {}

    def set_definitions(self, definitions):
        while self._layout.count():
            item = self._layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._editors.clear()
        for definition in definitions:
            row = QWidget()
            row_layout = QVBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(4)
            label = QLabel(definition.name + (" *" if definition.required else ""))
            label.setObjectName("fieldLabel")
            editor = self._create_editor(definition)
            if definition.description:
                editor.setToolTip(definition.description)
            row_layout.addWidget(label)
            row_layout.addWidget(editor)
            self._layout.addWidget(row)
            self._editors[definition.id] = (definition, editor)
        self._layout.addStretch(1)

    def _create_editor(self, definition):
        kind = definition.type.lower()
        if kind == "choice":
            editor = QComboBox()
            editor.addItems([str(item) for item in definition.options])
            index = editor.findText(str(definition.default))
            editor.setCurrentIndex(max(0, index))
            editor.currentIndexChanged.connect(self.values_changed)
            return editor
        if kind == "boolean":
            editor = QCheckBox("启用")
            editor.setChecked(bool(definition.default))
            editor.toggled.connect(self.values_changed)
            return editor
        if kind == "integer":
            editor = QSpinBox()
            editor.setRange(-2_000_000_000, 2_000_000_000)
            editor.setValue(int(definition.default or 0))
            editor.valueChanged.connect(self.values_changed)
            return editor
        if kind == "float":
            editor = QDoubleSpinBox()
            editor.setRange(-1_000_000_000.0, 1_000_000_000.0)
            editor.setDecimals(4)
            editor.setSingleStep(0.05)
            editor.setValue(float(definition.default or 0.0))
            editor.valueChanged.connect(self.values_changed)
            return editor
        if kind in {"file", "directory"}:
            editor = PathEditor(directory=kind == "directory")
            editor.edit.setText(str(definition.default or ""))
            editor.edit.textChanged.connect(self.values_changed)
            return editor
        editor = QLineEdit(str(definition.default or ""))
        editor.textChanged.connect(self.values_changed)
        return editor

    def values(self):
        result = {}
        for key, (definition, editor) in self._editors.items():
            kind = definition.type.lower()
            if isinstance(editor, QComboBox):
                value = editor.currentText()
            elif isinstance(editor, QCheckBox):
                value = editor.isChecked()
            elif isinstance(editor, (QSpinBox, QDoubleSpinBox)):
                value = editor.value()
            elif isinstance(editor, PathEditor):
                value = editor.value()
            else:
                value = editor.text().strip()
            result[key] = value
        return result

