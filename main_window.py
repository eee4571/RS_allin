from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QDockWidget,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QSizePolicy,
    QToolBar,
)

from widgets.log_panel import LogPanel
from widgets.map_view import MapView
from widgets.project_panel import ProjectPanel
from widgets.ribbon import Ribbon
from widgets.workflow_panel import ModulePanel


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
        self._build_view_menu()
        self._connect_events()
        self._report_plugins()

    def _build_menu(self):
        file_menu = self.menuBar().addMenu("文件(&F)")
        new_action = QAction("新建工程", self)
        new_action.setShortcut(QKeySequence.New)
        new_action.triggered.connect(lambda: self.statusBar().showMessage("原型：新建工程", 2500))
        open_action = QAction("打开工程", self)
        open_action.setShortcut(QKeySequence.Open)
        open_action.triggered.connect(lambda: self.statusBar().showMessage("原型：打开工程", 2500))
        exit_action = QAction("退出", self)
        exit_action.setShortcut(QKeySequence.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addActions((new_action, open_action))
        file_menu.addSeparator()
        file_menu.addAction(exit_action)

        self.view_menu = self.menuBar().addMenu("视图(&V)")
        reset_action = QAction("恢复默认布局", self)
        reset_action.triggered.connect(self._restore_layout)
        self.view_menu.addAction(reset_action)
        self.menuBar().addMenu("数据(&D)")
        self.menuBar().addMenu("工具(&T)")
        self.menuBar().addMenu("窗口(&W)")
        help_menu = self.menuBar().addMenu("帮助(&H)")
        about_action = QAction("关于", self)
        about_action.triggered.connect(
            lambda: QMessageBox.about(
                self, "关于", "遥感智能解译综合平台\n插件化 GUI 架构原型 · API v1"
            )
        )
        help_menu.addAction(about_action)

    def _build_workspace(self):
        self.ribbon = Ribbon()
        self.ribbon.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.module_toolbar = QToolBar("模块导航")
        self.module_toolbar.setObjectName("moduleToolbar")
        self.module_toolbar.setMovable(False)
        self.module_toolbar.setFloatable(False)
        self.module_toolbar.addWidget(self.ribbon)
        self.addToolBar(Qt.TopToolBarArea, self.module_toolbar)

        self.map_view = MapView()
        self.setCentralWidget(self.map_view)

        self.project_panel = ProjectPanel(self.context)
        self.project_dock = self._dock("项目与图层", self.project_panel, Qt.LeftDockWidgetArea)
        self.project_dock.setMinimumWidth(230)
        self.module_panel = ModulePanel()
        self.module_dock = self._dock("功能面板", self.module_panel, Qt.RightDockWidgetArea)
        self.module_dock.setMinimumWidth(330)
        self.log_panel = LogPanel()
        self.log_dock = self._dock("日志与任务", self.log_panel, Qt.BottomDockWidgetArea)
        self.log_dock.setMinimumHeight(170)
        self.log_dock.hide()

        self.status_text = QLabel("✓ 就绪")
        self.status_project = QLabel(f"项目：{self.context.project_name or '—'}")
        self.status_area = QLabel("区域：—")
        self.status_period = QLabel("期次：—")
        self.status_crs = QLabel("坐标系：—")
        self.status_coordinate = QLabel("坐标：—")
        self.status_scale = QLabel("比例尺：—")
        self.task_progress_label = QLabel("任务进度")
        self.progress = QProgressBar()
        self.progress.setFixedWidth(145)
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setTextVisible(True)
        self.statusBar().addWidget(self.status_text)
        self.statusBar().addWidget(self.status_project, 1)
        for label in (
            self.status_area,
            self.status_period,
            self.status_crs,
            self.status_coordinate,
            self.status_scale,
            self.task_progress_label,
        ):
            self.statusBar().addWidget(label)
        self.statusBar().addPermanentWidget(self.progress)

    def _build_view_menu(self):
        self.view_menu.addSeparator()
        self.view_menu.addAction(self.project_dock.toggleViewAction())
        self.view_menu.addAction(self.module_dock.toggleViewAction())
        self.view_menu.addAction(self.log_dock.toggleViewAction())

    def _dock(self, title, widget, area):
        dock = QDockWidget(title, self)
        dock.setObjectName(title)
        dock.setWidget(widget)
        dock.setAllowedAreas(Qt.AllDockWidgetAreas)
        self.addDockWidget(area, dock)
        return dock

    def _connect_events(self):
        self.ribbon.module_selected.connect(self._on_module_selected)
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

    def _on_module_selected(self, module_id):
        labels = dict((item[0], item[1]) for item in Ribbon.MODULES)
        self.status_text.setText("✓ 已选择：" + labels[module_id])

    def _on_started(self, event):
        self.progress.setValue(0)
        self.status_text.setText(event.message)
        self.log_panel.append(event.message)
        self.log_panel.update_task(event.module_id, event.workflow_id, "运行中", 0)

    def _on_progress(self, event):
        self.progress.setValue(round(event.progress * 100))
        self.status_text.setText(event.message)
        self.log_panel.update_task(
            event.module_id, event.workflow_id, event.message, event.progress
        )

    def _on_log(self, event):
        self.log_panel.append(f"{event.module_id} · {event.message}", event.level)

    def _on_completed(self, event):
        self.progress.setValue(100)
        self.status_text.setText(event.message)
        self.log_panel.append(event.message)
        self.log_panel.update_task(event.module_id, event.workflow_id, "已完成", 1.0)

    def _on_failed(self, event):
        self.status_text.setText(event.message)
        self.log_panel.append(event.message, "ERROR")
        self.log_panel.update_task(event.module_id, event.workflow_id, "失败")

    def _report_plugins(self):
        for descriptor in self.registry.descriptors():
            self.log_panel.append(
                f"模块已加载：{descriptor.display_name} v{descriptor.module_version} "
                f"(API {descriptor.api_version})"
            )
        for disabled in self.registry.disabled_modules():
            self.log_panel.append(f"模块已禁用：{disabled.display_name} · {disabled.reason}", "WARNING")

    def _restore_layout(self):
        self.addDockWidget(Qt.LeftDockWidgetArea, self.project_dock)
        self.addDockWidget(Qt.RightDockWidgetArea, self.module_dock)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.log_dock)
        self.project_dock.show()
        self.module_dock.show()
        self.log_dock.hide()
