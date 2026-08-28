"""Road-specific operation page; emits Commands and never calls algorithms."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QTabWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from core.models import Command
from core.project_context import ProjectContext


class RoadPanel(QWidget):
    """Compact road workflow UI backed only by platform context and Commands."""

    command_requested = Signal(object)

    DISPLAY_STEPS = (
        ("check", "数据检查"),
        ("extract", "道路提取"),
        ("width", "道路宽度计算"),
        ("change", "相邻期变化检测"),
        ("update", "成果更新"),
    )
    WORKFLOW_STEPS = {
        "full_pipeline": {"check", "extract", "width", "change", "update"},
        "rerun_period": {"check", "extract", "width", "update"},
        "rerun_change_pair": {"check", "change", "update"},
    }

    def __init__(
        self,
        module_id="road",
        title="道路变化检测",
        descriptor=None,
        project_context=None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("roadPanel")
        self.module_id = module_id
        self.descriptor = descriptor
        self.project_context = project_context or ProjectContext()
        self._action_buttons: list[QPushButton] = []

        root = QVBoxLayout(self)
        root.setContentsMargins(14, 12, 14, 10)
        root.setSpacing(7)

        heading = QLabel(title)
        heading.setObjectName("moduleTitle")
        root.addWidget(heading)
        self.context_status = QLabel(self._context_summary())
        self.context_status.setObjectName("roadContextStatus")
        self.context_status.setWordWrap(True)
        root.addWidget(self.context_status)

        mode_bar = QFrame()
        mode_bar.setObjectName("roadModeBar")
        mode_layout = QHBoxLayout(mode_bar)
        mode_layout.setContentsMargins(0, 0, 0, 0)
        mode_layout.setSpacing(0)
        self.mode_group = QButtonGroup(self)
        self.mode_group.setExclusive(True)
        self.automatic_button = self._mode_button("自动处理", 0)
        self.local_button = self._mode_button("局部重跑", 1)
        mode_layout.addWidget(self.automatic_button)
        mode_layout.addWidget(self.local_button)
        mode_layout.addStretch(1)
        root.addWidget(mode_bar)

        self.mode_stack = QStackedWidget()
        self.mode_stack.setObjectName("roadModeStack")
        self.mode_stack.addWidget(self._scroll_page(self._build_automatic_page()))
        self.mode_stack.addWidget(self._scroll_page(self._build_local_page()))
        root.addWidget(self.mode_stack, 3)

        root.addWidget(self._separator())
        status_title = QLabel("运行状态 / 处理步骤")
        status_title.setObjectName("roadSectionTitle")
        root.addWidget(status_title)
        self.run_status = QLabel("等待任务")
        self.run_status.setObjectName("roadStatus")
        self.run_status.setWordWrap(True)
        root.addWidget(self.run_status)
        self.steps = QListWidget()
        self.steps.setObjectName("roadWorkflowSteps")
        self.steps.setMaximumHeight(118)
        for _, name in self.DISPLAY_STEPS:
            self.steps.addItem(f"○  {name}")
        root.addWidget(self.steps)

        self.automatic_button.setChecked(True)
        self._set_mode(0)

    def _mode_button(self, text: str, index: int) -> QPushButton:
        button = QPushButton(text)
        button.setObjectName("roadModeButton")
        button.setCheckable(True)
        button.clicked.connect(lambda checked=False, value=index: self._set_mode(value))
        self.mode_group.addButton(button, index)
        return button

    def _build_automatic_page(self) -> QWidget:
        page = QWidget()
        page.setObjectName("roadModePage")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 7, 3, 3)
        layout.setSpacing(7)

        form = QFormLayout()
        form.setContentsMargins(0, 0, 0, 0)
        form.setVerticalSpacing(6)
        self.auto_area = QComboBox()
        self._populate_areas(self.auto_area)
        form.addRow("区域", self.auto_area)
        layout.addLayout(form)

        periods_label = QLabel("处理期次")
        periods_label.setObjectName("roadFieldLabel")
        layout.addWidget(periods_label)
        self.period_checks: dict[str, QCheckBox] = {}
        periods_row = QHBoxLayout()
        periods_row.setContentsMargins(0, 0, 0, 0)
        for period in self.project_context.periods:
            check = QCheckBox(str(period))
            check.setChecked(True)
            self.period_checks[str(period)] = check
            periods_row.addWidget(check)
        periods_row.addStretch(1)
        layout.addLayout(periods_row)

        self.data_line = QLabel()
        self.data_line.setWordWrap(True)
        layout.addWidget(self.data_line)
        self.data_summary = QLabel()
        layout.addWidget(self.data_summary)
        self.auto_area.currentIndexChanged.connect(self._refresh_data_status)
        self._refresh_data_status()

        self.advanced_toggle = QToolButton()
        self.advanced_toggle.setObjectName("roadAdvancedToggle")
        self.advanced_toggle.setText("高级设置")
        self.advanced_toggle.setCheckable(True)
        self.advanced_toggle.setArrowType(Qt.RightArrow)
        self.advanced_toggle.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.advanced_toggle.toggled.connect(self._toggle_advanced)
        layout.addWidget(self.advanced_toggle)

        self.advanced_panel = QWidget()
        advanced_form = QFormLayout(self.advanced_panel)
        advanced_form.setContentsMargins(12, 0, 0, 0)
        self.device = QComboBox()
        self.device.addItems(("CUDA", "CPU"))
        self.change_threshold = QDoubleSpinBox()
        self.change_threshold.setRange(0.0, 1.0)
        self.change_threshold.setSingleStep(0.05)
        self.change_threshold.setValue(0.55)
        self.processing_mode = QComboBox()
        self.processing_mode.addItems(("快速", "标准"))
        self.processing_mode.setCurrentText("标准")
        advanced_form.addRow("计算设备", self.device)
        advanced_form.addRow("变化检测阈值", self.change_threshold)
        advanced_form.addRow("处理模式", self.processing_mode)
        self.advanced_panel.hide()
        layout.addWidget(self.advanced_panel)

        self.run_full_button = self._action_button("运行完整流程", self._run_full)
        self.run_full_button.setObjectName("primaryButton")
        layout.addWidget(self.run_full_button)
        layout.addStretch(1)
        return page

    def _build_local_page(self) -> QWidget:
        page = QWidget()
        page.setObjectName("roadModePage")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 7, 3, 3)
        layout.setSpacing(7)

        area_form = QFormLayout()
        area_form.setContentsMargins(0, 0, 0, 0)
        self.local_area = QComboBox()
        self._populate_areas(self.local_area)
        area_form.addRow("区域", self.local_area)
        layout.addLayout(area_form)
        local_tabs = QTabWidget()
        local_tabs.setObjectName("roadLocalTabs")
        local_tabs.setMaximumHeight(130)

        period_page = QWidget()
        period_layout = QVBoxLayout(period_page)
        period_layout.setContentsMargins(5, 7, 5, 5)
        period_form = QFormLayout()
        period_form.setContentsMargins(0, 0, 0, 0)
        self.period_selector = QComboBox()
        self.period_selector.addItems([str(item) for item in self.project_context.periods])
        period_form.addRow("期次", self.period_selector)
        period_layout.addLayout(period_form)
        period_status = QLabel("○ 道路中心线    ○ 道路面    ○ 道路宽度")
        period_status.setObjectName("roadDataPending")
        period_status.setWordWrap(True)
        period_layout.addWidget(period_status)
        self.rerun_period_button = self._action_button(
            "重跑所选期次", self._rerun_period
        )
        period_layout.addWidget(self.rerun_period_button)
        period_layout.addStretch(1)
        local_tabs.addTab(period_page, "道路成果")

        change_page = QWidget()
        change_layout = QVBoxLayout(change_page)
        change_layout.setContentsMargins(5, 7, 5, 5)
        change_form = QFormLayout()
        change_form.setContentsMargins(0, 0, 0, 0)
        self.change_pair_selector = QComboBox()
        periods = [str(item) for item in self.project_context.periods]
        for before, after in zip(periods, periods[1:]):
            self.change_pair_selector.addItem(f"{before} → {after}", (before, after))
        if not self.change_pair_selector.count():
            self.change_pair_selector.addItem("暂无可用变化对", None)
        change_form.addRow("变化对", self.change_pair_selector)
        change_layout.addLayout(change_form)
        change_status = QLabel("○ 等待平台成果状态")
        change_status.setObjectName("roadDataPending")
        change_layout.addWidget(change_status)
        self.rerun_change_button = self._action_button(
            "重跑该变化对", self._rerun_change_pair
        )
        change_layout.addWidget(self.rerun_change_button)
        change_layout.addStretch(1)
        local_tabs.addTab(change_page, "变化检测")
        layout.addWidget(local_tabs, 1)

        self.update_related = QCheckBox("同时更新受影响的相关成果")
        self.update_related.setChecked(True)
        layout.addWidget(self.update_related)
        layout.addStretch(1)
        return page

    def _run_full(self) -> None:
        periods = [
            period for period, check in self.period_checks.items() if check.isChecked()
        ]
        if not periods:
            self.run_status.setText("请至少选择一个处理期次")
            return
        self._emit_command(
            "full_pipeline",
            {
                "area_id": self.auto_area.currentData() or "",
                "periods": periods,
                "device": self.device.currentText(),
                "change_threshold": self.change_threshold.value(),
                "processing_mode": self.processing_mode.currentText(),
                "update_related": True,
            },
        )

    def _rerun_period(self) -> None:
        self._emit_command(
            "rerun_period",
            {
                "area_id": self.local_area.currentData() or "",
                "period": self.period_selector.currentText(),
                "update_related": self.update_related.isChecked(),
            },
        )

    def _rerun_change_pair(self) -> None:
        pair = self.change_pair_selector.currentData()
        if not pair:
            self.run_status.setText("当前项目没有可重跑的变化对")
            return
        self._emit_command(
            "rerun_change_pair",
            {
                "area_id": self.local_area.currentData() or "",
                "before": pair[0],
                "after": pair[1],
                "update_related": self.update_related.isChecked(),
            },
        )

    def _emit_command(self, workflow_id: str, payload: dict) -> None:
        self.run_status.setText("任务已提交，等待调度")
        self.command_requested.emit(
            Command(self.module_id, workflow_id, action="run", payload=payload)
        )

    def update_task_state(
        self, workflow_id, state, message, progress=None, step_id=""
    ) -> None:
        if workflow_id not in {
            "full_pipeline", "rerun_period", "rerun_change_pair"
        }:
            return
        self.run_status.setText(message)
        running = state in {"queued", "running"}
        for button in self._action_buttons:
            button.setEnabled(not running)
        relevant = self.WORKFLOW_STEPS[workflow_id]
        ordered_relevant = [key for key, _ in self.DISPLAY_STEPS if key in relevant]
        count = len(ordered_relevant) if state == "completed" else 0
        if progress is not None and state != "completed":
            count = min(len(ordered_relevant), int(progress * len(ordered_relevant)))
        completed_keys = set(ordered_relevant[:count])
        for key, name in self.DISPLAY_STEPS:
            marker = "—" if key not in relevant else ("完成" if key in completed_keys else "○")
            if step_id == key and running:
                marker = "进行"
            self.steps.item(index).setText(f"{marker}  {name}")

    def _set_mode(self, index: int) -> None:
        self.mode_stack.setCurrentIndex(index)
        button = self.mode_group.button(index)
        if button is not None:
            button.setChecked(True)

    def _toggle_advanced(self, expanded: bool) -> None:
        self.advanced_panel.setVisible(expanded)
        self.advanced_toggle.setArrowType(Qt.DownArrow if expanded else Qt.RightArrow)

    def _populate_areas(self, combo: QComboBox) -> None:
        if not self.project_context.areas:
            combo.addItem("当前区域", "")
            return
        for area_id, value in self.project_context.areas.items():
            name = value.get("name", area_id) if isinstance(value, dict) else value
            combo.addItem(str(name or area_id), str(area_id))

    def _refresh_data_status(self, *_):
        checks = self._data_checks()
        ready = all(value for _, value in checks)
        self.data_line.setText(
            "    ".join(f"{'✓' if value else '○'} {label}" for label, value in checks)
        )
        self.data_line.setObjectName("roadDataReady" if ready else "roadDataPending")
        self.data_summary.setText(
            "数据已就绪" if ready else "项目数据待完善；当前仍可运行 Mock 流程"
        )
        self.data_summary.setObjectName(
            "roadDataSummaryReady" if ready else "roadDataSummaryPending"
        )
        self.style().unpolish(self.data_line)
        self.style().polish(self.data_line)
        self.style().unpolish(self.data_summary)
        self.style().polish(self.data_summary)

    def _data_checks(self) -> tuple[tuple[str, bool], ...]:
        inputs = self.project_context.inputs or {}
        area_id = self.auto_area.currentData() if hasattr(self, "auto_area") else ""
        area_inputs = inputs.get(area_id) if area_id else None
        manifest = area_inputs if isinstance(area_inputs, dict) else inputs
        input_keys = {str(key).casefold() for key in manifest}
        has_validation = bool(
            input_keys.intersection({"validation", "validation_area", "roi", "mask"})
        )
        has_imagery = bool(
            input_keys.intersection({"imagery", "images", "rasters", "periods"})
            or manifest
        )
        has_output = bool(
            self.project_context.output_root or self.project_context.project_root
        )
        return (
            ("验证区", has_validation),
            ("多期影像", has_imagery),
            ("输出位置", has_output),
        )

    def _context_summary(self) -> str:
        area_count = len(self.project_context.areas)
        period_count = len(self.project_context.periods)
        return f"当前区域：{area_count or '未配置'} · 可用期次：{period_count}"

    def _action_button(self, text: str, slot) -> QPushButton:
        button = QPushButton(text)
        button.clicked.connect(slot)
        self._action_buttons.append(button)
        return button

    @staticmethod
    def _separator() -> QFrame:
        separator = QFrame()
        separator.setObjectName("roadSeparator")
        separator.setFrameShape(QFrame.HLine)
        return separator

    @staticmethod
    def _scroll_page(page: QWidget) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setObjectName("roadModeScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setWidget(page)
        return scroll
