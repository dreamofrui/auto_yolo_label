"""Sample module page for the desktop workbench."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from core.sampler import (
    IndependentSampleConfig,
    SampleConfig,
    SamplePreflightResult,
    SampleResult,
)
from gui.workers.sample_worker import SampleWorker
from gui.task_runner import ImmediateTaskRunner, TaskRunner
from gui.path_picker import PathPicker
from gui.tool_page_chrome import (
    build_ai_assistant_panel,
    build_log_box,
    configure_left_panel,
    configure_tool_root,
    constrain_feedback_label,
    wrap_scroll_panel,
)
from gui.tool_defaults import ToolDefaults, default_text
from utils.task_registry import TaskRegistry


class SamplePage(QWidget):
    """Interactive Sample page with Flow and Independent modes."""

    back_requested = Signal()

    def __init__(
        self,
        worker: object | None = None,
        registry: TaskRegistry | None = None,
        task_runner: TaskRunner | None = None,
        defaults: ToolDefaults | None = None,
    ) -> None:
        super().__init__()
        self.setObjectName("samplePage")
        self._worker = worker or SampleWorker(registry=registry)
        self._task_runner = task_runner or ImmediateTaskRunner()
        self._defaults = defaults or ToolDefaults()
        self._mode = "flow"

        root = QHBoxLayout(self)
        configure_tool_root(root)

        self.left_main_panel = QFrame()
        self.left_main_panel.setObjectName("leftMainPanel")
        left = QVBoxLayout(self.left_main_panel)
        configure_left_panel(left)

        eyebrow = QLabel("Flow / Independent")
        eyebrow.setObjectName("eyebrow")
        title = QLabel("抽样")
        title.setObjectName("toolTitle")
        subtitle = QLabel("抽取训练样本并生成标准 YOLO 数据集")
        subtitle.setObjectName("smallTitle")
        copy = QLabel(
            "Flow 模式使用 mapping 复制样本；独立模式不依赖 mapping，会移动选中的图片和同名标签。"
        )
        copy.setObjectName("mutedText")
        copy.setWordWrap(True)

        mode_row = QHBoxLayout()
        self.flow_mode_button = QPushButton("Flow 模式")
        self.flow_mode_button.setCheckable(True)
        self.flow_mode_button.setChecked(True)
        self.flow_mode_button.setObjectName("tabButtonActive")
        self.independent_mode_button = QPushButton("独立模式")
        self.independent_mode_button.setCheckable(True)
        self.independent_mode_button.setObjectName("tabButton")
        mode_group = QButtonGroup(self)
        mode_group.addButton(self.flow_mode_button)
        mode_group.addButton(self.independent_mode_button)
        self.flow_mode_button.clicked.connect(lambda: self.set_mode("flow"))
        self.independent_mode_button.clicked.connect(lambda: self.set_mode("independent"))
        mode_row.addWidget(self.flow_mode_button)
        mode_row.addWidget(self.independent_mode_button)
        mode_row.addStretch(1)

        self.mode_note = QLabel("")
        self.mode_note.setObjectName("formPlaceholder")
        self.mode_note.setProperty("feedbackRole", "explanation")
        constrain_feedback_label(self.mode_note)
        self.mapping_status = QLabel("Mapping 状态：请选择站点路径。")
        self.mapping_status.setObjectName("formPlaceholder")
        self.mapping_status.setProperty("feedbackRole", "status")
        constrain_feedback_label(self.mapping_status)

        form = QGridLayout()
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(10)

        self.flow_site_input = PathPicker(
            placeholder="已扫描站点路径",
            dialog_title="选择站点路径",
        )
        self.independent_source_input = PathPicker(
            placeholder="独立图片源路径",
            dialog_title="选择图片源路径",
        )
        self.output_input = PathPicker(
            placeholder="输出路径",
            dialog_title="选择输出路径",
        )
        self.classes_input = PathPicker(
            mode="file",
            placeholder="可选 classes.txt 路径",
            dialog_title="选择 classes.txt",
            file_filter="Text files (*.txt);;All Files (*)",
        )
        self.count_input = _line_input(value=default_text(self._defaults, "sample", "count", "40"))
        self.ratio_input = _line_input(value=default_text(self._defaults, "sample", "ratio", "0.3"))
        self.min_count_input = _line_input(value=default_text(self._defaults, "sample", "min_count", "20"))
        self.max_count_input = _line_input(value=default_text(self._defaults, "sample", "max_count", "50"))
        self.full_threshold_input = _line_input(value=default_text(self._defaults, "sample", "full_threshold", "35"))
        self.train_ratio_input = _line_input(value=default_text(self._defaults, "sample", "train_ratio", "0.9"))

        self._source_label = QLabel("站点路径")
        self._source_label.setObjectName("fieldLabel")
        form.addWidget(self._source_label, 0, 0)
        form.addWidget(self.flow_site_input, 0, 1)
        form.addWidget(self.independent_source_input, 0, 1)
        form.addWidget(QLabel("输出路径"), 1, 0)
        form.addWidget(self.output_input, 1, 1)
        self._classes_label = QLabel("类别文件")
        form.addWidget(self._classes_label, 2, 0)
        form.addWidget(self.classes_input, 2, 1)
        self._output_format_label = QLabel("输出格式")
        form.addWidget(self._output_format_label, 3, 0)
        form.addWidget(self._build_output_format_controls(), 3, 1)
        form.addWidget(QLabel("策略"), 4, 0)
        form.addWidget(self._build_strategy_controls(), 4, 1)
        self._count_label = QLabel("计数")
        self._ratio_label = QLabel("比例")
        self._min_max_label = QLabel("最小/最大")
        self._full_threshold_label = QLabel("全量阈值")
        form.addWidget(self._count_label, 5, 0)
        form.addWidget(self.count_input, 5, 1)
        form.addWidget(self._ratio_label, 6, 0)
        form.addWidget(self.ratio_input, 6, 1)
        form.addWidget(self._min_max_label, 7, 0)
        self._min_max_inputs = _two_inputs(self.min_count_input, self.max_count_input)
        form.addWidget(self._min_max_inputs, 7, 1)
        form.addWidget(self._full_threshold_label, 8, 0)
        form.addWidget(self.full_threshold_input, 8, 1)
        form.addWidget(QLabel("训练比例"), 9, 0)
        form.addWidget(self.train_ratio_input, 9, 1)

        self.result_summary = QLabel("等待预检或执行。")
        self.result_summary.setObjectName("formPlaceholder")
        self.result_summary.setProperty("feedbackRole", "result")
        constrain_feedback_label(self.result_summary)
        self.preflight_panel = QFrame()
        self.preflight_panel.setObjectName("preflightPanel")
        preflight_layout = QGridLayout(self.preflight_panel)
        preflight_layout.setContentsMargins(10, 8, 10, 8)
        preflight_layout.setHorizontalSpacing(8)
        self.preflight_impact_summary = QLabel("预计输出：等待预检")
        self.preflight_impact_summary.setObjectName("preflightSummary")
        self.preflight_impact_summary.setProperty("feedbackRole", "output")
        constrain_feedback_label(self.preflight_impact_summary)
        self.preflight_risk_summary = QLabel("阻断与风险：等待预检")
        self.preflight_risk_summary.setObjectName("preflightSummary")
        self.preflight_risk_summary.setProperty("feedbackRole", "risk")
        constrain_feedback_label(self.preflight_risk_summary)
        preflight_layout.addWidget(self.preflight_impact_summary, 0, 0)
        preflight_layout.addWidget(self.preflight_risk_summary, 0, 1)
        self.confirm_move_checkbox = QPushButton("确认移动风险")
        self.confirm_move_checkbox.setCheckable(True)
        self.confirm_move_checkbox.setObjectName("confirmCheckbox")
        self.confirm_move_checkbox.setProperty("buttonRole", "riskConfirm")

        actions = QHBoxLayout()
        self.preflight_button = QPushButton("预检")
        self.preflight_button.setObjectName("secondaryButton")
        self.preflight_button.clicked.connect(self.run_preflight)
        self.run_button = QPushButton("开始抽样")
        self.run_button.setObjectName("primaryButton")
        self.run_button.clicked.connect(self.run_sample)
        actions.addStretch(1)
        actions.addWidget(self.preflight_button)
        actions.addWidget(self.run_button)

        left.addWidget(eyebrow)
        left.addWidget(title)
        left.addWidget(subtitle)
        left.addWidget(copy)
        left.addLayout(mode_row)
        left.addWidget(self.mode_note)
        left.addWidget(self.mapping_status)
        left.addLayout(form)
        left.addWidget(self.confirm_move_checkbox)
        left.addWidget(self.result_summary)
        left.addWidget(self.preflight_panel)
        self.log_box = build_log_box("[ready] 等待抽样参数")
        self.log_box.setMinimumHeight(72)
        self.log_box.setMaximumHeight(96)
        left.addWidget(self.log_box, 0)
        left.addLayout(actions)

        self.ai_assistant_panel = build_ai_assistant_panel(
            context="抽样页用于按 Flow 或独立模式生成 YOLO 训练数据集"
        )
        self.right_support_panel = self.ai_assistant_panel

        root.addWidget(wrap_scroll_panel(self.left_main_panel), 1)
        root.addWidget(self.right_support_panel, 0)
        self.flow_site_input.textChanged.connect(self.update_mapping_status)
        for button in (
            self.count_strategy_button,
            self.ratio_strategy_button,
            self.mixed_strategy_button,
        ):
            button.clicked.connect(self.update_strategy_fields)
        for button in (self.xml_output_button, self.yolo_output_button):
            button.clicked.connect(self.update_output_format_fields)
        self.set_mode("flow")
        self.apply_defaults(self._defaults)

    def current_mode(self) -> str:
        """Return current Sample page mode."""
        return self._mode

    def apply_defaults(self, defaults: ToolDefaults) -> None:
        """Apply non-path default parameters to the page."""
        self._defaults = defaults
        mode = default_text(defaults, "sample", "mode", "mixed")
        if mode == "count":
            self.count_strategy_button.setChecked(True)
        elif mode == "ratio":
            self.ratio_strategy_button.setChecked(True)
        else:
            self.mixed_strategy_button.setChecked(True)
        self.count_input.setText(default_text(defaults, "sample", "count", "40"))
        self.ratio_input.setText(default_text(defaults, "sample", "ratio", "0.3"))
        self.min_count_input.setText(default_text(defaults, "sample", "min_count", "20"))
        self.max_count_input.setText(default_text(defaults, "sample", "max_count", "50"))
        self.full_threshold_input.setText(default_text(defaults, "sample", "full_threshold", "35"))
        self.train_ratio_input.setText(default_text(defaults, "sample", "train_ratio", "0.9"))
        self.confirm_move_checkbox.setChecked(False)
        self.update_strategy_fields()
        self.update_output_format_fields()

    def set_mode(self, mode: str) -> None:
        """Switch Sample mode."""
        self._mode = mode
        is_flow = mode == "flow"
        self.flow_site_input.setVisible(is_flow)
        self.independent_source_input.setVisible(not is_flow)
        self._source_label.setText("站点路径" if is_flow else "图片源路径")
        if is_flow:
            self.mapping_status.setVisible(True)
            self._classes_label.setVisible(False)
            self.classes_input.setVisible(False)
            self._output_format_label.setVisible(False)
            self.output_format_controls.setVisible(False)
            self.confirm_move_checkbox.setVisible(False)
            self.mode_note.setText("Flow 模式依赖扫描生成的 mapping.json，会复制样本，不移动原始图片。")
            self.flow_mode_button.setObjectName("tabButtonActive")
            self.independent_mode_button.setObjectName("tabButton")
        else:
            self.mapping_status.setVisible(False)
            self._output_format_label.setVisible(True)
            self.output_format_controls.setVisible(True)
            self.confirm_move_checkbox.setVisible(True)
            self.mode_note.setText(
                "独立模式不创建 mapping，会移动选中图片。默认输出扁平 XML 标注目录，适合先用 LabelImg 人工标注；YOLO 输出可选。"
            )
            self.flow_mode_button.setObjectName("tabButton")
            self.independent_mode_button.setObjectName("tabButtonActive")
        for button in (self.flow_mode_button, self.independent_mode_button):
            button.style().unpolish(button)
            button.style().polish(button)
        self.update_mapping_status()
        self.update_strategy_fields()
        self.update_output_format_fields()

    def update_output_format_fields(self) -> None:
        """Show metadata fields required by the selected Independent output format."""
        is_independent_yolo = self._mode == "independent" and self.yolo_output_button.isChecked()
        self._classes_label.setVisible(is_independent_yolo)
        self.classes_input.setVisible(is_independent_yolo)

    def update_mapping_status(self) -> None:
        """Show the expected Flow mapping path status."""
        text = self.flow_site_input.text().strip()
        if not text:
            self.mapping_status.setText("Mapping 状态：请选择站点路径。")
            self.mapping_status.setToolTip("")
            return
        mapping_path = Path(text) / ".autolabeler" / "mapping.json"
        self.mapping_status.setToolTip(str(mapping_path))
        if mapping_path.exists():
            self.mapping_status.setText("Mapping 状态：已找到 .autolabeler/mapping.json")
            return
        self.mapping_status.setText("Mapping 状态：未找到 .autolabeler/mapping.json，请先扫描站点。")

    def update_strategy_fields(self) -> None:
        """Only show fields used by the selected sampling strategy."""
        strategy = self._checked_strategy()
        show_count = strategy == "count"
        show_ratio = strategy in {"ratio", "mixed"}
        show_mixed = strategy == "mixed"
        self._count_label.setVisible(show_count)
        self.count_input.setVisible(show_count)
        self._ratio_label.setVisible(show_ratio)
        self.ratio_input.setVisible(show_ratio)
        self._min_max_label.setVisible(show_mixed)
        self._min_max_inputs.setVisible(show_mixed)
        self._full_threshold_label.setVisible(True)
        self.full_threshold_input.setVisible(True)

    def run_preflight(self) -> None:
        """Run real sampler preflight and render estimates."""
        try:
            config = self._build_config()
        except (TypeError, ValueError) as exc:
            self._show_error("参数格式错误", str(exc))
            return
        self.result_summary.setText("预检运行中...")
        self._task_runner.run(
            lambda: (
                self._worker.preflight(config)  # type: ignore[attr-defined]
                if self._mode == "flow"
                else self._worker.preflight_independent(config)  # type: ignore[attr-defined]
            ),
            self._handle_preflight_outcome,
            lambda exc: self._show_error("预检失败", str(exc)),
        )

    def run_sample(self) -> None:
        """Build config from form values and run the Sample worker."""
        try:
            config = self._build_config()
            if self._mode == "independent" and not self.confirm_move_checkbox.isChecked():
                self.result_summary.setText("确认会移动选中图片及可迁移标签后，才能开始独立抽样。")
                return
        except (TypeError, ValueError) as exc:
            self._show_error("参数格式错误", str(exc))
            return
        self.result_summary.setText("抽样运行中...")
        self._task_runner.run(
            lambda: (
                self._worker.run(config)  # type: ignore[attr-defined]
                if self._mode == "flow"
                else self._worker.run_independent(config)  # type: ignore[attr-defined]
            ),
            self._handle_run_outcome,
            lambda exc: self._show_error("抽样失败", str(exc)),
        )

    def _handle_preflight_outcome(self, outcome) -> None:
        if not outcome.success or outcome.result is None:
            error = outcome.error
            message = "预检失败"
            details = "" if error is None else f"{error.code}: {error.message}"
            self._show_error(message, details)
            return
        self._show_preflight(outcome.result)

    def _handle_run_outcome(self, outcome) -> None:
        if not outcome.success or outcome.result is None:
            error = outcome.error
            message = "抽样失败"
            details = "" if error is None else f"{error.code}: {error.message}"
            self._show_error(message, details)
            return

        self._show_success(outcome.result)

    def _build_config(self) -> SampleConfig | IndependentSampleConfig:
        if self._mode == "flow":
            source_key = "site_folder"
            source_path = _required_path(self.flow_site_input, "请选择站点路径")
        else:
            source_key = "source_dir"
            source_path = _required_path(self.independent_source_input, "请选择图片源路径")
        common = {
            "output_dir": _required_path(self.output_input, "请选择输出路径"),
            "mode": self._checked_strategy(),
            "count": int(self.count_input.text().strip()),
            "ratio": float(self.ratio_input.text().strip()),
            "min_count": int(self.min_count_input.text().strip()),
            "max_count": int(self.max_count_input.text().strip()),
            "full_threshold": int(self.full_threshold_input.text().strip()),
            "train_ratio": float(self.train_ratio_input.text().strip()),
        }
        if self._mode == "flow":
            return SampleConfig(
                **{source_key: source_path},
                **common,
            )
        return IndependentSampleConfig(
            **{source_key: source_path},
            output_format=self._checked_output_format(),
            classes=_read_classes(self.classes_input.text().strip()),
            **common,
        )

    def _checked_strategy(self) -> str:
        if self.ratio_strategy_button.isChecked():
            return "ratio"
        if self.mixed_strategy_button.isChecked():
            return "mixed"
        return "count"

    def _checked_output_format(self) -> str:
        if self.yolo_output_button.isChecked():
            return "yolo"
        return "xml"

    def _build_output_format_controls(self) -> QWidget:
        self.output_format_controls = QWidget()
        self.output_format_controls.setMinimumHeight(38)
        row = QHBoxLayout(self.output_format_controls)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)
        self.xml_output_button = QPushButton("XML")
        self.yolo_output_button = QPushButton("YOLO")
        group = QButtonGroup(self)
        for button in (self.xml_output_button, self.yolo_output_button):
            button.setCheckable(True)
            button.setObjectName("secondaryButton")
            button.setMinimumWidth(72)
            group.addButton(button)
            row.addWidget(button)
        self.xml_output_button.setChecked(True)
        row.addStretch(1)
        return self.output_format_controls

    def _build_strategy_controls(self) -> QWidget:
        wrapper = QWidget()
        wrapper.setMinimumHeight(38)
        row = QHBoxLayout(wrapper)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)
        self.count_strategy_button = QPushButton("count")
        self.ratio_strategy_button = QPushButton("ratio")
        self.mixed_strategy_button = QPushButton("mixed")
        group = QButtonGroup(self)
        for button in (
            self.count_strategy_button,
            self.ratio_strategy_button,
            self.mixed_strategy_button,
        ):
            button.setCheckable(True)
            button.setObjectName("secondaryButton")
            button.setMinimumWidth(64)
            group.addButton(button)
            row.addWidget(button)
        self.mixed_strategy_button.setChecked(True)
        row.addStretch(1)
        return wrapper

    def _show_success(self, result: SampleResult) -> None:
        stats = result.statistics
        if result.output_format == "xml":
            summary = f"抽样完成：选中 {stats.sampled_count}，XML 标注目录 {result.dataset_dir}"
        else:
            summary = (
                f"抽样完成：选中 {stats.sampled_count}，训练 {stats.train_count}，"
                f"验证 {stats.val_count}，输出 {result.dataset_dir}"
            )
        self.result_summary.setText(summary)
        lines = [
            "[succeeded] 抽样完成",
            f"format: {result.output_format}",
            f"output: {result.dataset_dir}",
            f"sampled: {stats.sampled_count}",
        ]
        if result.output_format == "yolo":
            lines.append(f"data.yaml: {result.data_yaml}")
        self.log_box.setPlainText("\n".join(lines))

    def _show_preflight(self, result: SamplePreflightResult) -> None:
        stats = result.statistics
        status = "预检通过" if result.can_execute else "预检阻断"
        summary = (
            f"{status}：选中 {stats.sampled_count}，训练 {stats.train_count}，"
            f"验证 {stats.val_count}，复制 {result.copy_count}，移动 {result.move_count}"
        )
        if result.issues:
            summary = f"{summary}，问题 {len(result.issues)} 条"
        self.result_summary.setText(summary)
        blockers = sum(1 for issue in result.issues if issue.severity == "blocker")
        warnings = len(result.issues) - blockers
        self.preflight_impact_summary.setText(
            "预计输出："
            f"选中 {stats.sampled_count}，训练 {stats.train_count}，"
            f"验证 {stats.val_count}，复制 {result.copy_count}，移动 {result.move_count}"
        )
        self.preflight_risk_summary.setText(
            f"阻断与风险：阻断 {blockers}，警告 {warnings}，"
            f"分组 {result.total_groups}"
        )
        lines = [
            "[preflight] " + status,
            f"mode: {result.mode}",
            f"format: {result.output_format}",
            f"groups: {result.total_groups}",
            f"sampled: {stats.sampled_count}",
            f"train: {stats.train_count}",
            f"val: {stats.val_count}",
            f"copy: {result.copy_count}",
            f"move: {result.move_count}",
        ]
        for issue in result.issues:
            lines.append(
                f"{issue.severity}: {issue.code} - {issue.message} ({issue.detail})"
            )
        self.log_box.setPlainText("\n".join(lines))

    def _show_error(self, message: str, details: str) -> None:
        text = message if not details else f"{message}：{details}"
        self.result_summary.setText(text)
        self.log_box.setPlainText(f"[failed] {text}")


def _line_input(value: str = "", placeholder: str = "") -> QLineEdit:
    field = QLineEdit()
    if value:
        field.setText(value)
    if placeholder:
        field.setPlaceholderText(placeholder)
    field.setObjectName("formInput")
    return field


def _required_path(field: QLineEdit, message: str) -> Path:
    text = field.text().strip()
    if not text:
        raise ValueError(message)
    return Path(text)


def _read_classes(text: str) -> list[str] | None:
    if not text:
        return None
    path = Path(text)
    classes = [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    return classes


def _two_inputs(left: QLineEdit, right: QLineEdit) -> QWidget:
    wrapper = QWidget()
    row = QHBoxLayout(wrapper)
    row.setContentsMargins(0, 0, 0, 0)
    row.setSpacing(8)
    row.addWidget(left)
    row.addWidget(right)
    return wrapper
