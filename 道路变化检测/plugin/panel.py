from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from .models import (
    DataCatalog,
    RunRequest,
    latest_pipeline_manifest,
    read_json_object,
    scan_data_source,
)
from .runner import RoadRunner


class RoadPanel(QWidget):
    """Compact, self-sufficient dock panel for road change processing."""

    def __init__(self, runner: RoadRunner, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.runner = runner
        self.catalog: DataCatalog | None = None
        self._period_checks: dict[str, QCheckBox] = {}
        self.setObjectName("roadChangePanel")
        self.setMinimumWidth(300)
        self.setMaximumWidth(520)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        self._build_ui()
        self._connect_runner()

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        outer.addWidget(scroll)
        body = QWidget(scroll)
        scroll.setWidget(body)
        layout = QVBoxLayout(body)
        layout.setContentsMargins(12, 10, 12, 12)
        layout.setSpacing(10)

        title = QLabel("道路变化检测", body)
        title.setStyleSheet("font-size: 17px; font-weight: 600;")
        layout.addWidget(title)

        data_group = QGroupBox("数据准备", body)
        data_layout = QVBoxLayout(data_group)
        self.source_edit, source_row = self._path_row("选择包含验证区和多期 TXT 的数据目录", self._choose_source)
        self.output_edit, output_row = self._path_row("选择插件独立成果输出目录", self._choose_output)
        data_layout.addWidget(QLabel("数据源"))
        data_layout.addLayout(source_row)
        data_layout.addWidget(QLabel("输出位置"))
        data_layout.addLayout(output_row)
        self.scan_button = QPushButton("扫描数据", data_group)
        self.scan_button.clicked.connect(self.scan_source)
        data_layout.addWidget(self.scan_button)
        form = QFormLayout()
        self.area_combo = QComboBox(data_group)
        self.area_combo.currentTextChanged.connect(self._area_changed)
        form.addRow("区域", self.area_combo)
        data_layout.addLayout(form)
        data_layout.addWidget(QLabel("处理期次"))
        self.period_widget = QWidget(data_group)
        self.period_layout = QVBoxLayout(self.period_widget)
        self.period_layout.setContentsMargins(4, 0, 0, 0)
        self.period_layout.setSpacing(3)
        data_layout.addWidget(self.period_widget)
        self.data_status = QLabel("○ 尚未扫描数据", data_group)
        self.data_status.setWordWrap(True)
        data_layout.addWidget(self.data_status)
        layout.addWidget(data_group)

        settings_group = QGroupBox("运行设置", body)
        settings_layout = QVBoxLayout(settings_group)
        basic_form = QFormLayout()
        self.profile_combo = QComboBox(settings_group)
        self.profile_combo.addItem("标准", "full")
        self.profile_combo.addItem("快速", "fast")
        self.device_combo = QComboBox(settings_group)
        self.device_combo.addItem("自动", "auto")
        self.device_combo.addItem("CUDA", "cuda")
        self.device_combo.addItem("CPU", "cpu")
        basic_form.addRow("处理模式", self.profile_combo)
        basic_form.addRow("计算设备", self.device_combo)
        settings_layout.addLayout(basic_form)
        self.advanced_toggle = QToolButton(settings_group)
        self.advanced_toggle.setText("高级设置")
        self.advanced_toggle.setCheckable(True)
        self.advanced_toggle.setArrowType(Qt.RightArrow)
        self.advanced_toggle.toggled.connect(self._toggle_advanced)
        settings_layout.addWidget(self.advanced_toggle)
        self.advanced_widget = QWidget(settings_group)
        advanced_form = QFormLayout(self.advanced_widget)
        self.absolute_spin = self._double_spin(2.0, 0.0, 100000.0, 2)
        self.ratio_spin = self._double_spin(0.2, 0.0, 100.0, 3)
        self.tolerance_spin = self._double_spin(3.0, 0.0, 100000.0, 2)
        self.pixel_size_spin = self._double_spin(0.0, 0.0, 100000.0, 4)
        self.rescale_combo = QComboBox(self.advanced_widget)
        self.rescale_combo.addItem("关闭", "off")
        self.rescale_combo.addItem("开启", "on")
        self.junction_combo = QComboBox(self.advanced_widget)
        self.junction_combo.addItem("稀疏路口", "sparse")
        self.junction_combo.addItem("旧版密集路口", "dense_legacy")
        advanced_form.addRow("绝对阈值", self.absolute_spin)
        advanced_form.addRow("相对阈值", self.ratio_spin)
        advanced_form.addRow("位置容差", self.tolerance_spin)
        advanced_form.addRow("像元大小", self.pixel_size_spin)
        advanced_form.addRow("重采样", self.rescale_combo)
        advanced_form.addRow("路口节点", self.junction_combo)
        self.advanced_widget.hide()
        settings_layout.addWidget(self.advanced_widget)
        layout.addWidget(settings_group)

        self.run_button = QPushButton("运行完整流程", body)
        self.run_button.setMinimumHeight(34)
        self.run_button.clicked.connect(self.run_full)
        layout.addWidget(self.run_button)

        rerun_group = QGroupBox("局部重跑", body)
        rerun_layout = QFormLayout(rerun_group)
        self.period_rerun_combo = QComboBox(rerun_group)
        self.change_rerun_combo = QComboBox(rerun_group)
        self.period_rerun_button = QPushButton("重跑所选期次", rerun_group)
        self.change_rerun_button = QPushButton("重跑该变化对", rerun_group)
        self.period_rerun_button.clicked.connect(self.rerun_period)
        self.change_rerun_button.clicked.connect(self.rerun_change)
        rerun_layout.addRow("期次", self.period_rerun_combo)
        rerun_layout.addRow("", self.period_rerun_button)
        rerun_layout.addRow("变化对", self.change_rerun_combo)
        rerun_layout.addRow("", self.change_rerun_button)
        layout.addWidget(rerun_group)

        status_group = QGroupBox("当前状态", body)
        status_layout = QVBoxLayout(status_group)
        self.status_label = QLabel("等待任务", status_group)
        self.status_label.setWordWrap(True)
        self.progress_bar = QProgressBar(status_group)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.context_label = QLabel("当前：—", status_group)
        self.context_label.setWordWrap(True)
        status_layout.addWidget(self.status_label)
        status_layout.addWidget(self.progress_bar)
        status_layout.addWidget(self.context_label)
        button_row = QHBoxLayout()
        self.log_toggle = QPushButton("查看日志", status_group)
        self.log_toggle.setCheckable(True)
        self.log_toggle.toggled.connect(self._toggle_log)
        self.cancel_button = QPushButton("取消任务", status_group)
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self.runner.cancel)
        button_row.addWidget(self.log_toggle)
        button_row.addWidget(self.cancel_button)
        status_layout.addLayout(button_row)
        self.log_view = QPlainTextEdit(status_group)
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumBlockCount(500)
        self.log_view.setMinimumHeight(120)
        self.log_view.hide()
        status_layout.addWidget(self.log_view)
        layout.addWidget(status_group)
        layout.addStretch(1)
        self._set_rerun_enabled(False)

    def _path_row(self, placeholder: str, slot) -> tuple[QLineEdit, QHBoxLayout]:
        row = QHBoxLayout()
        edit = QLineEdit(self)
        edit.setPlaceholderText(placeholder)
        button = QPushButton("选择", self)
        button.clicked.connect(slot)
        row.addWidget(edit, 1)
        row.addWidget(button)
        return edit, row

    @staticmethod
    def _double_spin(value: float, minimum: float, maximum: float, decimals: int) -> QDoubleSpinBox:
        spin = QDoubleSpinBox()
        spin.setRange(minimum, maximum)
        spin.setDecimals(decimals)
        spin.setValue(value)
        return spin

    def _connect_runner(self) -> None:
        self.runner.task_started.connect(self._task_started)
        self.runner.task_progress.connect(self._task_progress)
        self.runner.task_log.connect(self._task_log)
        self.runner.task_finished.connect(self._task_finished)
        self.runner.task_failed.connect(self._task_failed)
        self.runner.running_changed.connect(self._running_changed)

    @Slot()
    def _choose_source(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "选择道路变化检测数据目录", self.source_edit.text())
        if path:
            self.source_edit.setText(path)

    @Slot()
    def _choose_output(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "选择成果输出目录", self.output_edit.text())
        if path:
            self.output_edit.setText(path)
            self._refresh_rerun_selectors()

    @Slot(bool)
    def _toggle_advanced(self, visible: bool) -> None:
        self.advanced_toggle.setArrowType(Qt.DownArrow if visible else Qt.RightArrow)
        self.advanced_widget.setVisible(visible)

    @Slot(bool)
    def _toggle_log(self, visible: bool) -> None:
        self.log_toggle.setText("收起日志" if visible else "查看日志")
        self.log_view.setVisible(visible)

    @Slot()
    def scan_source(self) -> None:
        try:
            self.catalog = scan_data_source(self.source_edit.text(), self.runner.paths.root)
        except Exception as exc:
            self.catalog = None
            self.data_status.setText(f"✗ {exc}")
            self._show_error("扫描数据失败", str(exc))
            return
        self.area_combo.clear()
        self.area_combo.addItems(self.catalog.area_ids)
        if not self.output_edit.text().strip():
            self.output_edit.setText(str(self.catalog.suggested_output))
        self.data_status.setText(f"✓ 已识别 {len(self.catalog.areas)} 个区域")
        self._area_changed(self.area_combo.currentText())
        self._refresh_rerun_selectors()

    @Slot(str)
    def _area_changed(self, area_id: str) -> None:
        while self.period_layout.count():
            item = self.period_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self._period_checks.clear()
        if self.catalog is None or area_id not in self.catalog.areas:
            return
        area = self.catalog.areas[area_id]
        for period in area.periods:
            check = QCheckBox(period, self.period_widget)
            check.setChecked(True)
            self.period_layout.addWidget(check)
            self._period_checks[period] = check
        self.data_status.setText(
            f"✓ 验证区\n✓ {len(area.periods)} 期影像 TXT\n✓ 输出位置由插件独立管理"
        )
        self._refresh_rerun_selectors()

    def _request(self) -> RunRequest:
        if self.catalog is None:
            raise ValueError("请先选择并扫描数据目录。")
        output_text = self.output_edit.text().strip()
        if not output_text:
            raise ValueError("请选择成果输出目录。")
        periods = tuple(name for name, check in self._period_checks.items() if check.isChecked())
        return RunRequest(
            catalog=self.catalog,
            area_id=self.area_combo.currentText(),
            periods=periods,
            output_root=Path(output_text),
            execution_profile=str(self.profile_combo.currentData()),
            device=str(self.device_combo.currentData()),
            absolute=str(self.absolute_spin.value()),
            ratio=str(self.ratio_spin.value()),
            tolerance=str(self.tolerance_spin.value()),
            pixel_size=str(self.pixel_size_spin.value()),
            rescale=str(self.rescale_combo.currentData()),
            junction_node_mode=str(self.junction_combo.currentData()),
        )

    @Slot()
    def run_full(self) -> None:
        try:
            self.runner.start_full(self._request())
        except Exception as exc:
            self._show_error("无法启动任务", str(exc))

    @Slot()
    def rerun_period(self) -> None:
        try:
            output, area = self._rerun_context()
            period = self.period_rerun_combo.currentText()
            if not period:
                raise ValueError("没有可重跑的期次。")
            self.runner.start_rerun_period(output, area, period)
        except Exception as exc:
            self._show_error("无法局部重跑", str(exc))

    @Slot()
    def rerun_change(self) -> None:
        try:
            output, area = self._rerun_context()
            value = self.change_rerun_combo.currentData()
            if not isinstance(value, tuple) or len(value) != 2:
                raise ValueError("没有可重跑的变化对。")
            self.runner.start_rerun_change(output, area, value[0], value[1])
        except Exception as exc:
            self._show_error("无法局部重跑", str(exc))

    def _rerun_context(self) -> tuple[Path, str]:
        output_text = self.output_edit.text().strip()
        area = self.area_combo.currentText().strip()
        if not output_text or not area:
            raise ValueError("请先选择输出目录和区域。")
        return Path(output_text), area

    def _refresh_rerun_selectors(self) -> None:
        self.period_rerun_combo.clear()
        self.change_rerun_combo.clear()
        output = self.output_edit.text().strip()
        area = self.area_combo.currentText().strip()
        manifest_path = latest_pipeline_manifest(output) if output else None
        manifest = read_json_object(manifest_path) if manifest_path else None
        if not manifest or not area:
            self._set_rerun_enabled(False)
            return
        periods = []
        for entry in manifest.get("period_results") or []:
            if isinstance(entry, dict) and str(entry.get("grid")) == area:
                period = str(entry.get("period") or "")
                if period and period not in periods:
                    periods.append(period)
        for period in periods:
            self.period_rerun_combo.addItem(period)
        for entry in manifest.get("change_results") or []:
            if not isinstance(entry, dict) or str(entry.get("grid")) != area:
                continue
            before, after = str(entry.get("before_period") or ""), str(entry.get("after_period") or "")
            if before and after:
                self.change_rerun_combo.addItem(f"{before} → {after}", (before, after))
        self._set_rerun_enabled(bool(periods or self.change_rerun_combo.count()))

    def _set_rerun_enabled(self, enabled: bool) -> None:
        self.period_rerun_button.setEnabled(enabled and self.period_rerun_combo.count() > 0)
        self.change_rerun_button.setEnabled(enabled and self.change_rerun_combo.count() > 0)

    @Slot(dict)
    def _task_started(self, payload: dict) -> None:
        self.status_label.setText("任务正在运行")
        self.progress_bar.setValue(0)
        self._task_log("启动：" + " ".join(map(str, payload.get("command") or [])))

    @Slot(dict)
    def _task_progress(self, payload: dict) -> None:
        stage = str(payload.get("stage") or "处理中")
        status = str(payload.get("status") or "running")
        self.status_label.setText(f"{stage} · {status}")
        progress = payload.get("progress", -1)
        if isinstance(progress, (int, float)) and progress >= 0:
            self.progress_bar.setValue(round(float(progress) * 100))
        area = str(payload.get("grid") or payload.get("area_id") or "")
        period = str(payload.get("period") or "")
        if not period and payload.get("before_period") and payload.get("after_period"):
            period = f"{payload['before_period']} → {payload['after_period']}"
        context = " · ".join(value for value in (area, period, stage) if value)
        self.context_label.setText("当前：" + (context or stage))

    @Slot(str)
    def _task_log(self, message: str) -> None:
        if message:
            self.log_view.appendPlainText(message)

    @Slot(dict)
    def _task_finished(self, _payload: dict) -> None:
        self.status_label.setText("任务已完成")
        self.progress_bar.setValue(100)
        self._refresh_rerun_selectors()

    @Slot(str)
    def _task_failed(self, message: str) -> None:
        self.status_label.setText(message)
        self._task_log(message)
        if message != "任务已取消。":
            self.log_toggle.setChecked(True)

    @Slot(bool)
    def _running_changed(self, running: bool) -> None:
        self.run_button.setEnabled(not running)
        self.scan_button.setEnabled(not running)
        self.cancel_button.setEnabled(running)
        if running:
            self._set_rerun_enabled(False)
        else:
            self._refresh_rerun_selectors()

    def _show_error(self, title: str, message: str) -> None:
        self.status_label.setText(message)
        QMessageBox.critical(self, title, message)

