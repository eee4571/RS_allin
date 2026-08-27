from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QDockWidget,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from widgets.log_panel import LogPanel
from widgets.map_view import MapView
from widgets.project_panel import ProjectPanel
from widgets.ribbon import Ribbon
from widgets.workflow_panel import WorkflowPanel


class MainWindow(QMainWindow):
    """Presentation shell: display, interaction, dispatch, and status only."""

    def __init__(self, registry, command_bus, event_bus, layer_manager, context):
        super().__init__()
        self.registry = registry
        self.command_bus = command_bus
        self.event_bus = event_bus
        self.layer_manager = layer_manager
        self.context = context
        self.setWindowTitle("遥感智能解译综合平台 · 原型")
        self.resize(1480, 900)
        self.setMinimumSize(1080, 680)
        self._build_menu()
        self._build_workspace()
        self._connect_events()
        self._report_plugins()

        workflows = registry.all_workflows()
        if workflows:
            module, workflow = workflows[0]
            self.select_workflow(module.module_id, workflow.id)

    def _build_menu(self):
        project_menu = self.menuBar().addMenu("项目")
        new_action = QAction("新建工程", self)
        new_action.setShortcut(QKeySequence.New)
        new_action.triggered.connect(lambda: self.statusBar().showMessage("原型：新建工程", 2500))
        open_action = QAction("打开工程", self)
        open_action.setShortcut(QKeySequence.Open)
        open_action.triggered.connect(lambda: self.statusBar().showMessage("原型：打开工程", 2500))
        project_menu.addActions((new_action, open_action))
        view_menu = self.menuBar().addMenu("视图")
        reset_action = QAction("恢复默认布局", self)
        reset_action.triggered.connect(self._restore_layout)
        view_menu.addAction(reset_action)
        help_menu = self.menuBar().addMenu("帮助")
        about_action = QAction("关于", self)
        about_action.triggered.connect(
            lambda: QMessageBox.about(
                self, "关于", "遥感智能解译综合平台\n插件化 GUI 架构原型 · API v1"
            )
        )
        help_menu.addAction(about_action)

        toolbar = QToolBar("项目工具")
        toolbar.setObjectName("projectToolbar")
        toolbar.setMovable(False)
        toolbar.addActions((new_action, open_action))
        self.addToolBar(toolbar)

    def _build_workspace(self):
        central = QWidget()
        central_layout = QVBoxLayout(central)
        central_layout.setContentsMargins(0, 0, 0, 0)
        central_layout.setSpacing(0)
        self.ribbon = Ribbon(self.registry)
        self.map_view = MapView()
        central_layout.addWidget(self.ribbon)
        central_layout.addWidget(self.map_view, 1)
        self.setCentralWidget(central)

        self.project_panel = ProjectPanel(self.context)
        self.project_dock = self._dock("项目与图层", self.project_panel, Qt.LeftDockWidgetArea)
        self.project_dock.setMinimumWidth(230)
        self.workflow_panel = WorkflowPanel()
        self.workflow_dock = self._dock("当前工作流", self.workflow_panel, Qt.RightDockWidgetArea)
        self.workflow_dock.setMinimumWidth(330)
        self.log_panel = LogPanel()
        self.log_dock = self._dock("日志与任务", self.log_panel, Qt.BottomDockWidgetArea)
        self.log_dock.setMinimumHeight(170)

        self.status_text = QLabel("就绪")
        self.progress = QProgressBar()
        self.progress.setFixedWidth(190)
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setTextVisible(True)
        self.statusBar().addWidget(self.status_text, 1)
        self.statusBar().addPermanentWidget(self.progress)

    def _dock(self, title, widget, area):
        dock = QDockWidget(title, self)
        dock.setObjectName(title)
        dock.setWidget(widget)
        dock.setAllowedAreas(Qt.AllDockWidgetAreas)
        self.addDockWidget(area, dock)
        return dock

    def _connect_events(self):
        self.ribbon.workflow_selected.connect(self.select_workflow)
        self.workflow_panel.command_requested.connect(self.command_bus.dispatch)
        self.layer_manager.layers_changed.connect(self.project_panel.set_layers)
        self.layer_manager.layers_changed.connect(self.map_view.set_layers)
        self.event_bus.task_started.connect(self._on_started)
        self.event_bus.task_progress.connect(self._on_progress)
        self.event_bus.task_log.connect(self._on_log)
        self.event_bus.task_completed.connect(self._on_completed)
        self.event_bus.task_failed.connect(self._on_failed)
        self.event_bus.result_available.connect(
            lambda event: self.log_panel.append(f"成果可用：{event.name} [{event.result_type}]")
        )

    def select_workflow(self, module_id, workflow_id):
        try:
            module = self.registry.get(module_id)
            workflow = self.registry.workflow(module_id, workflow_id)
        except KeyError as exc:
            self.status_text.setText(str(exc))
            return
        self.workflow_panel.set_workflow(module, workflow, self.context)
        self.status_text.setText(f"当前：{workflow.name}")

    def _on_started(self, event):
        self.progress.setValue(0)
        self.status_text.setText(event.message)
        self.log_panel.append(event.message)
        self.log_panel.update_task(event.module_id, event.workflow_id, "运行中", 0)
        if self.workflow_panel.belongs_to(event.module_id, event.workflow_id):
            self.workflow_panel.set_running(True)

    def _on_progress(self, event):
        self.progress.setValue(round(event.progress * 100))
        self.status_text.setText(event.message)
        self.log_panel.update_task(
            event.module_id, event.workflow_id, event.message, event.progress
        )
        if self.workflow_panel.belongs_to(event.module_id, event.workflow_id):
            self.workflow_panel.update_progress(event.step_id)

    def _on_log(self, event):
        self.log_panel.append(f"{event.module_id} · {event.message}", event.level)

    def _on_completed(self, event):
        self.progress.setValue(100)
        self.status_text.setText(event.message)
        self.log_panel.append(event.message)
        self.log_panel.update_task(event.module_id, event.workflow_id, "已完成", 1.0)
        if self.workflow_panel.belongs_to(event.module_id, event.workflow_id):
            self.workflow_panel.complete()

    def _on_failed(self, event):
        self.status_text.setText(event.message)
        self.log_panel.append(event.message, "ERROR")
        self.log_panel.update_task(event.module_id, event.workflow_id, "失败")
        if self.workflow_panel.belongs_to(event.module_id, event.workflow_id):
            self.workflow_panel.set_running(False)

    def _report_plugins(self):
        for module in self.registry.modules():
            self.log_panel.append(
                f"模块已加载：{module.display_name} v{module.module_version} (API {module.api_version})"
            )
        for disabled in self.registry.disabled_modules():
            self.log_panel.append(f"模块已禁用：{disabled.display_name} · {disabled.reason}", "WARNING")

    def _restore_layout(self):
        self.addDockWidget(Qt.LeftDockWidgetArea, self.project_dock)
        self.addDockWidget(Qt.RightDockWidgetArea, self.workflow_dock)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.log_dock)
        for dock in (self.project_dock, self.workflow_dock, self.log_dock):
            dock.show()

