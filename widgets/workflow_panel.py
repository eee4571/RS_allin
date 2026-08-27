from __future__ import annotations

from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from core.models import Command
from widgets.parameter_panel import ParameterPanel


class StepRow(QFrame):
    def __init__(self, index, step, parent=None):
        super().__init__(parent)
        self.setObjectName("stepRow")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(7, 6, 7, 6)
        self.badge = QLabel(str(index))
        self.badge.setObjectName("stepBadge")
        self.badge.setAlignment(Qt.AlignCenter)
        self.badge.setFixedSize(24, 24)
        text = QLabel(step.name + ("（可选）" if step.optional else ""))
        text.setWordWrap(True)
        if step.description:
            text.setToolTip(step.description)
        layout.addWidget(self.badge)
        layout.addWidget(text, 1)

    def set_state(self, state):
        self.setProperty("state", state)
        self.style().unpolish(self)
        self.style().polish(self)


class WorkflowPanel(QWidget):
    command_requested = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._module = None
        self._workflow = None
        self._context = None
        self._step_rows = {}

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)
        self.module_label = QLabel("选择一个工作流")
        self.module_label.setObjectName("eyebrow")
        self.title = QLabel("当前工作流")
        self.title.setObjectName("panelTitle")
        self.description = QLabel("从顶部功能区选择业务流程。")
        self.description.setObjectName("mutedText")
        self.description.setWordWrap(True)
        root.addWidget(self.module_label)
        root.addWidget(self.title)
        root.addWidget(self.description)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        body = QWidget()
        self.body_layout = QVBoxLayout(body)
        self.body_layout.setContentsMargins(0, 4, 4, 4)
        self.body_layout.setSpacing(8)
        self.steps_title = QLabel("处理流程")
        self.steps_title.setObjectName("sectionTitle")
        self.steps_holder = QWidget()
        self.steps_layout = QVBoxLayout(self.steps_holder)
        self.steps_layout.setContentsMargins(0, 0, 0, 0)
        self.steps_layout.setSpacing(5)
        self.params_title = QLabel("运行参数")
        self.params_title.setObjectName("sectionTitle")
        self.parameters = ParameterPanel()
        self.body_layout.addWidget(self.steps_title)
        self.body_layout.addWidget(self.steps_holder)
        self.body_layout.addSpacing(7)
        self.body_layout.addWidget(self.params_title)
        self.body_layout.addWidget(self.parameters)
        scroll.setWidget(body)
        root.addWidget(scroll, 1)

        self.tools_holder = QWidget()
        self.tools_layout = QHBoxLayout(self.tools_holder)
        self.tools_layout.setContentsMargins(0, 0, 0, 0)
        root.addWidget(self.tools_holder)
        self.run_button = QPushButton("运行工作流")
        self.run_button.setObjectName("primaryButton")
        self.run_button.setMinimumHeight(42)
        self.run_button.setEnabled(False)
        self.run_button.clicked.connect(self._run)
        root.addWidget(self.run_button)

    def set_workflow(self, module, workflow, context):
        self._module, self._workflow, self._context = module, workflow, context
        self.module_label.setText(f"{module.display_name}  ·  v{module.module_version}")
        self.title.setText(f"{workflow.icon}  {workflow.name}")
        self.description.setText(workflow.description)
        self._clear_layout(self.steps_layout)
        self._step_rows.clear()
        for index, step in enumerate(workflow.steps, 1):
            row = StepRow(index, step)
            self.steps_layout.addWidget(row)
            self._step_rows[step.id] = row
        self.parameters.set_definitions(workflow.parameters)
        self._clear_layout(self.tools_layout)
        for tool in module.tools():
            button = QPushButton(f"{tool.icon} {tool.name}".strip())
            button.setObjectName("secondaryButton")
            button.setToolTip(tool.description)
            button.clicked.connect(
                lambda checked=False, action=tool.id: self._emit_tool(action)
            )
            self.tools_layout.addWidget(button)
        self.tools_layout.addStretch(1)
        self.run_button.setEnabled(True)
        self.set_running(False)

    @staticmethod
    def _clear_layout(layout):
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _run(self):
        if not self._module or not self._workflow:
            return
        self.command_requested.emit(
            Command(
                self._module.module_id,
                self._workflow.id,
                "run",
                self.parameters.values(),
                self._context,
            )
        )

    def _emit_tool(self, action):
        if self._module and self._workflow:
            self.command_requested.emit(
                Command(
                    self._module.module_id,
                    self._workflow.id,
                    action,
                    self.parameters.values(),
                    self._context,
                )
            )

    def belongs_to(self, module_id, workflow_id):
        return bool(
            self._module and self._workflow
            and self._module.module_id == module_id
            and self._workflow.id == workflow_id
        )

    def set_running(self, running):
        self.run_button.setEnabled(not running and self._workflow is not None)
        self.run_button.setText("处理中…" if running else "运行工作流")
        if not running:
            for row in self._step_rows.values():
                row.set_state("")

    def update_progress(self, step_id):
        reached = False
        for current_id, row in self._step_rows.items():
            if current_id == step_id:
                row.set_state("active")
                reached = True
            elif not reached:
                row.set_state("done")
            else:
                row.set_state("")

    def complete(self):
        self.set_running(False)
        for row in self._step_rows.values():
            row.set_state("done")
