from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QLabel,
    QListWidget,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from core.models import Command
from widgets.parameter_panel import ParameterPanel


class ModulePanel(QWidget):
    """Platform-owned host that presents module capabilities generically."""

    command_requested = Signal(object)

    def __init__(
        self,
        parent=None,
        navigation=(),
        descriptors=(),
        page_factories=None,
        project_context=None,
    ):
        super().__init__(parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        self.stack = QStackedWidget()
        self.stack.setObjectName("moduleStack")
        root.addWidget(self.stack)
        self._pages: dict[str, QWidget] = {}
        descriptor_by_id = {item.module_id: item for item in descriptors}
        page_factories = dict(page_factories or {})
        for module_id, title in navigation:
            descriptor = descriptor_by_id.get(module_id)
            page_factory = page_factories.get(module_id)
            if page_factory is None:
                page = ModuleOperationPage(module_id, title, descriptor)
            else:
                page = page_factory(
                    module_id=module_id,
                    title=title,
                    descriptor=descriptor,
                    project_context=project_context,
                )
            page.command_requested.connect(self.command_requested.emit)
            self._pages[module_id] = page
            self.stack.addWidget(page)

        if self._pages:
            self.show_module(next(iter(self._pages)))

    @property
    def current_module_id(self) -> str:
        page = self.stack.currentWidget()
        return page.module_id if page is not None else ""

    def show_module(self, module_id: str) -> bool:
        page = self._pages.get(module_id)
        if page is None:
            return False
        self.stack.setCurrentWidget(page)
        return True

    def update_task_state(
        self,
        module_id: str,
        workflow_id: str,
        state: str,
        message: str,
        progress: float | None = None,
        step_id: str = "",
    ) -> None:
        page = self._pages.get(module_id)
        if page is not None:
            page.update_task_state(workflow_id, state, message, progress, step_id)


class ModuleOperationPage(QWidget):
    """Reusable page shell generated from a public module descriptor."""

    command_requested = Signal(object)

    def __init__(self, module_id, title, descriptor=None, parent=None):
        super().__init__(parent)
        self.module_id = module_id
        self.descriptor = descriptor
        self._workflow_by_id = {
            workflow.id: workflow for workflow in descriptor.workflows
        } if descriptor is not None else {}

        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 12)
        root.setSpacing(9)

        heading = QLabel(title)
        heading.setObjectName("moduleTitle")
        root.addWidget(heading)
        self.status = QLabel("已就绪" if self._workflow_by_id else "模块能力尚未接入")
        self.status.setObjectName("moduleStatus")
        self.status.setWordWrap(True)
        root.addWidget(self.status)
        root.addWidget(self._separator())

        if not self._workflow_by_id:
            placeholder = QLabel("此页面已预留。模块注册能力后会在这里显示通用操作界面。")
            placeholder.setObjectName("modulePlaceholder")
            placeholder.setWordWrap(True)
            placeholder.setAlignment(Qt.AlignTop | Qt.AlignLeft)
            root.addWidget(placeholder)
            root.addStretch(1)
            return

        section = QLabel("工作流 / 功能")
        section.setObjectName("sectionTitle")
        root.addWidget(section)
        self.workflow_selector = QComboBox()
        for workflow in descriptor.workflows:
            self.workflow_selector.addItem(workflow.name, workflow.id)
        self.workflow_selector.currentIndexChanged.connect(self._show_workflow)
        root.addWidget(self.workflow_selector)

        self.description = QLabel()
        self.description.setObjectName("moduleDescription")
        self.description.setWordWrap(True)
        root.addWidget(self.description)
        root.addWidget(self._separator())

        scroll = QScrollArea()
        scroll.setObjectName("moduleParameterScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 0, 4, 0)
        parameter_title = QLabel("当前工作流参数")
        parameter_title.setObjectName("sectionTitle")
        scroll_layout.addWidget(parameter_title)
        self.parameters = ParameterPanel()
        scroll_layout.addWidget(self.parameters)
        scroll.setWidget(scroll_content)
        root.addWidget(scroll, 3)

        root.addWidget(self._separator())
        steps_title = QLabel("运行状态 / 步骤")
        steps_title.setObjectName("sectionTitle")
        root.addWidget(steps_title)
        self.steps = QListWidget()
        self.steps.setObjectName("workflowSteps")
        self.steps.setMaximumHeight(132)
        root.addWidget(self.steps)

        self.run_button = QPushButton("开始处理")
        self.run_button.setObjectName("primaryButton")
        self.run_button.clicked.connect(self._request_run)
        root.addWidget(self.run_button)
        self._show_workflow()

    @staticmethod
    def _separator():
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setObjectName("moduleSeparator")
        return separator

    def _current_workflow(self):
        if not hasattr(self, "workflow_selector"):
            return None
        return self._workflow_by_id.get(self.workflow_selector.currentData())

    def _show_workflow(self, *_):
        workflow = self._current_workflow()
        if workflow is None:
            return
        self.description.setText(workflow.description)
        self.parameters.set_definitions(workflow.parameters)
        self.steps.clear()
        for step in workflow.steps:
            self.steps.addItem(f"○  {step.name}")
        self.status.setText("已就绪")
        self.run_button.setEnabled(True)

    def _request_run(self):
        workflow = self._current_workflow()
        if workflow is None:
            return
        self.command_requested.emit(
            Command(self.module_id, workflow.id, payload=self.parameters.values())
        )

    def update_task_state(
        self, workflow_id, state, message, progress=None, step_id=""
    ) -> None:
        if workflow_id not in self._workflow_by_id:
            return
        index = self.workflow_selector.findData(workflow_id)
        if index >= 0 and self.workflow_selector.currentIndex() != index:
            self.workflow_selector.setCurrentIndex(index)
        self.status.setText(message)
        self.run_button.setEnabled(state not in {"running", "queued"})
        workflow = self._workflow_by_id[workflow_id]
        completed_count = 0
        if state == "completed":
            completed_count = len(workflow.steps)
        elif progress is not None:
            completed_count = min(len(workflow.steps), int(progress * len(workflow.steps)))
        for index, step in enumerate(workflow.steps):
            marker = "✓" if index < completed_count else "○"
            if step_id and step.id == step_id and state == "running":
                marker = "●"
            self.steps.item(index).setText(f"{marker}  {step.name}")
