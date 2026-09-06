"""Convert module page for the desktop workbench."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.converter import (
    XmlDatasetAnalysis,
    XmlDatasetAnalyzeConfig,
    XmlDatasetConvertConfig,
    XmlDatasetConvertResult,
)
from gui.path_picker import PathPicker
from gui.task_runner import ImmediateTaskRunner, TaskRunner
from gui.tool_page_chrome import (
    build_ai_assistant_panel,
    build_log_box,
    configure_left_panel,
    configure_tool_root,
    constrain_feedback_label,
    wrap_scroll_panel,
)
from gui.tool_defaults import ToolDefaults, default_text
from gui.workers.convert_worker import (
    ConvertWorker,
    XmlDatasetAnalyzeWorkerOutcome,
    XmlDatasetConvertWorkerOutcome,
)
from utils.task_registry import TaskRegistry


class ConvertWorkerProtocol(Protocol):
    """Worker shape used by ConvertPage."""

    def analyze_xml_dataset(
        self, config: XmlDatasetAnalyzeConfig
    ) -> XmlDatasetAnalyzeWorkerOutcome:
        """Analyze XML dataset conversion."""

    def convert_xml_dataset(
        self, config: XmlDatasetConvertConfig
    ) -> XmlDatasetConvertWorkerOutcome:
        """Convert confirmed XML dataset."""


class ConvertPage(QWidget):
    """Interactive XML directory to YOLO dataset conversion page."""

    def __init__(
        self,
        worker: ConvertWorkerProtocol | None = None,
        registry: TaskRegistry | None = None,
        task_runner: TaskRunner | None = None,
        defaults: ToolDefaults | None = None,
    ) -> None:
        super().__init__()
        self.setObjectName("convertPage")
        if registry is None:
            registry = TaskRegistry(Path.home() / ".autolabeler" / "tasks")
        self._registry = registry
        self._worker = worker or ConvertWorker(registry=registry)
        self._task_runner = task_runner or ImmediateTaskRunner()
        self._defaults = defaults or ToolDefaults()
        self._analysis: XmlDatasetAnalysis | None = None
        self._analyzed_source: Path | None = None
        self._analyzed_output: Path | None = None
        self._convert_running = False
        self._progress_timer = QTimer(self)
        self._progress_timer.setInterval(750)
        self._progress_timer.timeout.connect(self.refresh_running_progress)

        root = QHBoxLayout(self)
        configure_tool_root(root)

        self.left_main_panel = QFrame()
        self.left_main_panel.setObjectName("leftMainPanel")
        left = QVBoxLayout(self.left_main_panel)
        configure_left_panel(left)

        eyebrow = QLabel("XML -> YOLO dataset")
        eyebrow.setObjectName("eyebrow")
        title = QLabel("转换")
        title.setObjectName("toolTitle")
        subtitle = QLabel("图片与 XML 目录生成标准 YOLO 数据集")
        subtitle.setObjectName("smallTitle")
        copy = QLabel(
            "转换不依赖 mapping，不做抽样策略，只按 train/val 比例复制有效图片和 XML 派生标签。"
        )
        copy.setObjectName("mutedText")
        copy.setWordWrap(True)

        form = QGridLayout()
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(10)
        self.source_input = PathPicker(
            placeholder="包含图片和 XML 的源目录",
            dialog_title="选择源目录",
        )
        self.output_input = PathPicker(
            placeholder="输出 YOLO 数据集目录",
            dialog_title="选择输出目录",
        )
        self.train_ratio_input = _line_input(
            value=default_text(self._defaults, "convert", "train_ratio", "0.9")
        )
        self.provided_classes_input = PathPicker(
            mode="file",
            placeholder="可选 classes.txt，留空则从 XML 收集",
            dialog_title="选择 classes.txt",
            file_filter="Text files (*.txt);;All Files (*)",
        )
        self.overwrite_checkbox = QCheckBox("允许清理/覆盖非空输出目录")
        self.overwrite_checkbox.setObjectName("riskCheckbox")
        self.overwrite_checkbox.setProperty("feedbackRole", "riskConfirm")
        self.overwrite_checkbox.setChecked(False)

        self.train_ratio_label = QLabel("训练比例")
        self.classes_file_label = QLabel("类别文件")
        fields = (
            ("源目录", self.source_input),
            ("输出目录", self.output_input),
            (self.train_ratio_label, self.train_ratio_input),
            (self.classes_file_label, self.provided_classes_input),
            ("输出策略", self.overwrite_checkbox),
        )
        for row, (label, widget) in enumerate(fields):
            label_widget = label if isinstance(label, QLabel) else QLabel(label)
            form.addWidget(label_widget, row, 0)
            form.addWidget(widget, row, 1)

        self.classes_box = QTextEdit()
        self.classes_box.setObjectName("logBox")
        self.classes_box.setPlaceholderText("分析后在这里显示类别顺序，每行一个类别")
        self.classes_box.setMinimumHeight(68)
        self.classes_box.setMaximumHeight(88)
        self.confirm_classes_checkbox = QCheckBox("我确认类别顺序用于生成 classes.txt 与 data.yaml")
        self.confirm_classes_checkbox.setObjectName("riskCheckbox")
        self.confirm_classes_checkbox.setProperty("feedbackRole", "riskConfirm")
        self.confirm_classes_checkbox.setToolTip(
            "分析通过后确认类别顺序；勾选确认不会要求重新分析。"
        )
        self.result_summary = QLabel("先分析目录，再确认类别顺序并转换。")
        self.result_summary.setObjectName("formPlaceholder")
        self.result_summary.setProperty("feedbackRole", "result")
        constrain_feedback_label(self.result_summary)
        self.analysis_panel = QFrame()
        self.analysis_panel.setObjectName("preflightPanel")
        analysis_layout = QGridLayout(self.analysis_panel)
        analysis_layout.setContentsMargins(10, 8, 10, 8)
        analysis_layout.setHorizontalSpacing(8)
        self.analysis_class_summary = QLabel("类别确认：等待分析")
        self.analysis_class_summary.setObjectName("preflightSummary")
        self.analysis_class_summary.setProperty("feedbackRole", "output")
        constrain_feedback_label(self.analysis_class_summary)
        self.analysis_risk_summary = QLabel("输出风险：等待分析")
        self.analysis_risk_summary.setObjectName("preflightSummary")
        self.analysis_risk_summary.setProperty("feedbackRole", "risk")
        constrain_feedback_label(self.analysis_risk_summary)
        analysis_layout.addWidget(self.analysis_class_summary, 0, 0)
        analysis_layout.addWidget(self.analysis_risk_summary, 0, 1)
        self.analysis_panel.setVisible(False)
        self.progress_label = QLabel("进度：等待开始")
        self.progress_label.setObjectName("mutedText")
        self.progress_label.setProperty("feedbackRole", "status")
        constrain_feedback_label(self.progress_label)
        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("taskProgressBar")
        self.progress_bar.setRange(0, 1)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)

        actions = QHBoxLayout()
        self.analyze_button = QPushButton("分析目录")
        self.analyze_button.setObjectName("secondaryButton")
        self.analyze_button.clicked.connect(self.run_analyze)
        self.convert_button = QPushButton("开始转换")
        self.convert_button.setObjectName("primaryButton")
        self.convert_button.clicked.connect(self.run_convert)
        actions.addWidget(self.analyze_button)
        actions.addWidget(self.convert_button)
        actions.addStretch(1)

        left.addWidget(eyebrow)
        left.addWidget(title)
        left.addWidget(subtitle)
        left.addWidget(copy)
        left.addLayout(form)
        left.addWidget(QLabel("类别顺序"))
        left.addWidget(self.classes_box)
        left.addWidget(self.confirm_classes_checkbox)
        left.addWidget(self.result_summary)
        left.addWidget(self.analysis_panel)
        left.addWidget(self.progress_label)
        left.addWidget(self.progress_bar)
        self.log_box = build_log_box("[ready] 等待目录分析")
        self.log_box.setMinimumHeight(84)
        self.log_box.setMaximumHeight(112)
        left.addWidget(self.log_box, 0)
        left.addStretch(1)
        left.addLayout(actions)

        self.ai_assistant_panel = build_ai_assistant_panel(
            context="转换页用于把图片与 XML 目录生成标准 YOLO 数据集"
        )
        self.right_support_panel = self.ai_assistant_panel

        self.left_scroll_area = wrap_scroll_panel(self.left_main_panel)
        root.addWidget(self.left_scroll_area, 1)
        root.addWidget(self.right_support_panel, 0)

        for field in (
            self.source_input,
            self.output_input,
            self.train_ratio_input,
            self.provided_classes_input,
        ):
            field.textChanged.connect(self._invalidate_analysis)
        self.overwrite_checkbox.stateChanged.connect(self._invalidate_analysis)
        self.confirm_classes_checkbox.stateChanged.connect(self._sync_action_state)
        self._sync_action_state()

    def apply_defaults(self, defaults: ToolDefaults) -> None:
        """Apply non-path default parameters to the page."""
        self._defaults = defaults
        self.train_ratio_input.setText(
            default_text(defaults, "convert", "train_ratio", "0.9")
        )
        self.overwrite_checkbox.setChecked(False)
        self._invalidate_analysis()

    def run_analyze(self) -> None:
        """Analyze XML dataset conversion inputs."""
        try:
            config = self._build_analyze_config()
        except (TypeError, ValueError, OSError) as exc:
            self._show_error("参数格式错误", str(exc))
            return
        self.result_summary.setText("分析运行中...")
        self._task_runner.run(
            lambda: self._worker.analyze_xml_dataset(config),
            lambda outcome: self._handle_analyze_outcome(config, outcome),
            lambda exc: self._show_error("分析失败", str(exc)),
        )

    def _handle_analyze_outcome(
        self,
        config: XmlDatasetAnalyzeConfig,
        outcome: XmlDatasetAnalyzeWorkerOutcome,
    ) -> None:
        if not outcome.success or outcome.analysis is None:
            error = outcome.error
            details = "" if error is None else f"{error.code}: {error.message}"
            self._show_error("分析失败", details)
            return
        self._analysis = outcome.analysis
        self._analyzed_source = config.source_dir
        self._analyzed_output = config.output_dir
        self.confirm_classes_checkbox.setChecked(False)
        self._show_analysis(outcome.analysis)
        self._sync_action_state()
        QTimer.singleShot(0, lambda: self._scroll_actions_into_view(retries=2))

    def run_convert(self) -> None:
        """Convert after analysis and class confirmation."""
        if self._analysis is None:
            self.result_summary.setText("请先分析目录，再开始转换。")
            return
        classes = _classes_from_text(self.classes_box.toPlainText())
        if not self.confirm_classes_checkbox.isChecked() or not classes:
            self.result_summary.setText("请确认类别顺序后，再开始转换。")
            return
        try:
            config = XmlDatasetConvertConfig(
                source_dir=_required_path(self.source_input, "请选择源目录"),
                output_dir=_required_path(self.output_input, "请选择输出目录"),
                confirmed_classes=classes,
                train_ratio=float(self.train_ratio_input.text().strip()),
                overwrite_output=self.overwrite_checkbox.isChecked(),
            )
        except (TypeError, ValueError) as exc:
            self._show_error("参数格式错误", str(exc))
            return
        self.result_summary.setText("转换运行中...")
        self.progress_label.setText("进度：准备转换")
        self.progress_bar.setRange(0, 1)
        self.progress_bar.setValue(0)
        self.analyze_button.setEnabled(False)
        self.convert_button.setEnabled(False)
        self._convert_running = True
        self._progress_timer.start()
        self._task_runner.run(
            lambda: self._worker.convert_xml_dataset(config),
            self._handle_convert_outcome,
            lambda exc: self._show_error("转换失败", str(exc)),
        )

    def refresh_running_progress(self) -> None:
        """Render the latest active convert task progress from TaskRegistry."""
        tasks = [
            task
            for task in self._registry.list_tasks()
            if task.task_type == "convert" and task.status in {"queued", "running"}
        ]
        if not tasks:
            if self._convert_running:
                self.progress_label.setText("进度：等待任务登记")
                self.progress_bar.setRange(0, 0)
                return
            if self._progress_timer.isActive():
                self._progress_timer.stop()
            return
        task = sorted(tasks, key=lambda item: item.created_at)[-1]
        total = max(task.progress_total, 0)
        current = max(task.progress_current, 0)
        message = task.progress_message or "等待"
        if total > 0:
            bounded_current = min(current, total)
            percent = int((bounded_current / total) * 100)
            self.progress_bar.setRange(0, total)
            self.progress_bar.setValue(bounded_current)
            self.progress_label.setText(
                f"进度：{bounded_current}/{total} ({percent}%) · {message}"
            )
            return
        self.progress_bar.setRange(0, 0)
        self.progress_label.setText(f"进度：{message}")

    def _handle_convert_outcome(
        self, outcome: XmlDatasetConvertWorkerOutcome
    ) -> None:
        self._convert_running = False
        self._progress_timer.stop()
        self.analyze_button.setEnabled(True)
        if not outcome.success or outcome.result is None:
            error = outcome.error
            details = "" if error is None else f"{error.code}: {error.message}"
            self._show_error("转换失败", details)
            return
        self._show_success(outcome.result)
        self._analysis = None
        self.confirm_classes_checkbox.setChecked(False)
        self._sync_action_state()

    def _build_analyze_config(self) -> XmlDatasetAnalyzeConfig:
        return XmlDatasetAnalyzeConfig(
            source_dir=_required_path(self.source_input, "请选择源目录"),
            output_dir=_required_path(self.output_input, "请选择输出目录"),
            train_ratio=float(self.train_ratio_input.text().strip()),
            classes=_read_classes_file(self.provided_classes_input.text().strip()),
            overwrite_output=self.overwrite_checkbox.isChecked(),
        )

    def _invalidate_analysis(self, *_args: object) -> None:
        self._analysis = None
        self.confirm_classes_checkbox.setChecked(False)
        self.analysis_panel.setVisible(False)
        self._sync_action_state()

    def _sync_action_state(self, *_args: object) -> None:
        """Keep conversion gated by analysis and explicit class confirmation."""
        analysis_ok = (
            self._analysis is not None
            and bool(self._analysis.collected_classes)
            and not self._analysis.blocking_issues
            and not self._analysis.output_conflicts
        )
        self.confirm_classes_checkbox.setEnabled(analysis_ok)
        self.convert_button.setEnabled(
            analysis_ok and self.confirm_classes_checkbox.isChecked()
        )

    def _scroll_actions_into_view(self, *, retries: int = 0) -> None:
        """Keep conversion actions reachable after analysis expands the form."""
        try:
            self.left_main_panel.adjustSize()
            self.left_scroll_area.ensureWidgetVisible(self.analyze_button, 0, 18)
        except RuntimeError:
            return
        if retries > 0:
            QTimer.singleShot(
                0, lambda: self._scroll_actions_into_view(retries=retries - 1)
            )

    def _show_analysis(self, analysis: XmlDatasetAnalysis) -> None:
        status = "分析完成" if not analysis.blocking_issues else "分析阻断"
        self.result_summary.setText(
            f"{status}：有效配对 {analysis.valid_pair_count}，跳过图片 "
            f"{analysis.skipped_image_count}，跳过 XML {analysis.skipped_xml_count}"
        )
        if not analysis.blocking_issues and not analysis.output_conflicts:
            self.result_summary.setText(
                f"{self.result_summary.text()}；请确认类别顺序后开始转换。"
            )
        self.classes_box.setPlainText("\n".join(analysis.collected_classes))
        self.analysis_panel.setVisible(True)
        self.analysis_class_summary.setText(
            f"类别确认：{len(analysis.collected_classes)} 类，"
            "可在上方调整，等待确认"
        )
        overwrite_status = "已允许清理/覆盖" if self.overwrite_checkbox.isChecked() else "不清理非空输出"
        self.analysis_risk_summary.setText(
            f"输出风险：阻断 {len(analysis.blocking_issues)}，"
            f"冲突 {len(analysis.output_conflicts)}，{overwrite_status}，"
            f"跳过图片 {analysis.skipped_image_count}"
        )
        lines = [
            f"[analysis] {status}",
            f"valid_pairs: {analysis.valid_pair_count}",
            f"skipped_images: {analysis.skipped_image_count}",
            f"skipped_xml: {analysis.skipped_xml_count}",
            f"classes: {', '.join(analysis.collected_classes)}",
        ]
        for issue in analysis.blocking_issues:
            lines.append(f"blocker: {issue}")
        for conflict in analysis.output_conflicts:
            lines.append(f"conflict: {conflict}")
        self.log_box.setPlainText("\n".join(lines))

    def _show_success(self, result: XmlDatasetConvertResult) -> None:
        self.progress_bar.setRange(0, max(result.total_pairs, 1))
        self.progress_bar.setValue(result.total_pairs)
        self.progress_label.setText(
            f"进度：{result.total_pairs}/{result.total_pairs} (100%) · 转换完成"
        )
        self.result_summary.setText(
            f"转换完成：有效 {result.total_pairs}，训练 {result.train_count}，"
            f"验证 {result.val_count}，输出 {result.dataset_dir}"
        )
        self.log_box.setPlainText(
            "\n".join(
                (
                    "[succeeded] 转换完成",
                    f"dataset: {result.dataset_dir}",
                    f"classes: {result.class_count}",
                    f"data.yaml: {result.paths.data_yaml}",
                    f"skipped_images: {result.skipped_image_count}",
                    f"skipped_xml: {result.skipped_xml_count}",
                )
            )
        )

    def _show_error(self, message: str, details: str) -> None:
        self._convert_running = False
        self._progress_timer.stop()
        self.analyze_button.setEnabled(True)
        self._sync_action_state()
        text = message if not details else f"{message}：{details}"
        self.result_summary.setText(text)
        self.progress_label.setText(f"进度：{text}")
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


def _read_classes_file(text: str) -> list[str] | None:
    if not text:
        return None
    return _classes_from_text(Path(text).read_text(encoding="utf-8"))


def _classes_from_text(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]
