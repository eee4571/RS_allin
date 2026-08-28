from __future__ import annotations

from datetime import datetime

from PySide6.QtWidgets import (
    QHeaderView,
    QPlainTextEdit,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


class LogPanel(QWidget):
    def __init__(self, parent=None, module_names=None, workflow_names=None):
        super().__init__(parent)
        self._module_names = dict(module_names or {})
        self._workflow_names = dict(workflow_names or {})
        root = QVBoxLayout(self)
        root.setContentsMargins(4, 4, 4, 4)
        self.tabs = QTabWidget()
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(1000)
        self.tasks = QTableWidget(0, 4)
        self.tasks.setHorizontalHeaderLabels(["模块", "工作流", "状态", "进度"])
        self.tasks.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tasks.verticalHeader().hide()
        self.tabs.addTab(self.log, "运行日志")
        self.tabs.addTab(self.tasks, "任务")
        root.addWidget(self.tabs)
        self._rows = {}

    def append(self, message, level="INFO"):
        now = datetime.now().strftime("%H:%M:%S")
        self.log.appendPlainText(f"[{now}] [{level}] {message}")

    def update_task(self, module_id, workflow_id, status, progress=None):
        key = (module_id, workflow_id)
        if key not in self._rows:
            row = self.tasks.rowCount()
            self.tasks.insertRow(row)
            self._rows[key] = row
            self.tasks.setItem(
                row, 0, QTableWidgetItem(self._module_names.get(module_id, module_id))
            )
            self.tasks.setItem(
                row,
                1,
                QTableWidgetItem(
                    self._workflow_names.get((module_id, workflow_id), workflow_id)
                ),
            )
        row = self._rows[key]
        self.tasks.setItem(row, 2, QTableWidgetItem(status))
        display = "—" if progress is None else f"{round(progress * 100)}%"
        self.tasks.setItem(row, 3, QTableWidgetItem(display))
