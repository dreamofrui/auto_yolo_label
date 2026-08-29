"""Infer module page for the desktop workbench."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from core.inferencer import InferConfig, InferResult
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
from gui.workers.infer_worker import InferWorker, InferWorkerOutcome
from utils.exceptions import ErrorCode
from utils.task_registry import TaskHandle, TaskRegistry


class InferWorkerProtocol(Protocol):
    """Worker shape used by InferPage."""

    def run(self, config: InferConfig) -> InferWorkerOutcome:
        """Run inference and return a worker outcome."""


class InferPage(QWidget):
    """Interactive Infer page with Flow and Independent modes."""

    def __init__(
        self,
        worker: InferWorkerProtocol | None = None,
        registry: TaskRegistry | None = None,
        task_runner: TaskRunner | None = None,
        defaults: ToolDefaults | None = None,
    ) -> None:
        super().__init__()
        self.setObjectName("inferPage")
        if registry is None and worker is None:
            registry = TaskRegistry(Path.home() / ".autolabeler" / "tasks")
        self._registry = registry
        self._worker = worker or InferWorker(registry=self._registry)
        self._task_runner = task_runner or ImmediateTaskRunner()
        self._defaults = defaults or ToolDefaults()
        self._mode = "flow"
        self._infer_running = False
        self._cancel_pending = False
        self._progress_timer = QTimer(self)
        self._progress_timer.setInterval(750)
        self._progress_timer.timeout.connect(self.refresh_running_progress)

        root = QHBoxLayout(self)
        configure_tool_root(root)

        self.left_main_panel = QFrame()
        self.left_main_panel.setObjectName("leftMainPanel")
        left = QVBoxLayout(self.left_main_panel)
        configure_left_panel(left)

        eyebrow = QLabel("Flow / Independent")
        eyebrow.setObjectName("eyebrow")
        title = QLabel("推理")
        title.setObjectName("toolTitle")
        subtitle = QLabel("使用模型生成预测标签")
        subtitle.setObjectName("smallTitle")
        copy = QLabel(
            "Flow 模式默认推理 mapping 中未抽样图片；独立模式递归处理图片文件夹，不创建 mapping。"
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

        form = QGridLayout()
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(10)
        self.model_input = PathPicker(
            mode="file",
            placeholder="模型 .pt 文件",
            dialog_title="选择模型文件",
            file_filter="PyTorch weights (*.pt);;All Files (*)",
        )
        self.site_input = PathPicker(
            placeholder="已扫描站点路径",
            dialog_title="选择站点路径",
        )
        self.image_folder_input = PathPicker(
            placeholder="独立图片文件夹",
            dialog_title="选择图片文件夹",
        )
        self.output_root_input = PathPicker(
            placeholder="独立推理输出根目录",
            dialog_title="选择输出根目录",
        )
        self.confidence_input = _line_input(
            value=default_text(self._defaults, "infer", "confidence", "0.25")
        )
        self.iou_input = _line_input(
            value=default_text(self._defaults, "infer", "iou", "0.7")
        )
        self.iou_input.setToolTip(
            "NMS 重叠阈值：重叠超过该 IoU 的候选框会被合并/抑制；越低越容易去重，越高越容易保留重叠框。"
        )
        self.batch_input = _line_input(
            value=default_text(self._defaults, "infer", "batch_size", "-1")
        )
        self.label_y_offset_input = _line_input(
            value=default_text(self._defaults, "infer", "label_y_offset_px", "0")
        )
        self.device_input = _combo(
            ("auto", "cpu", "gpu"),
            current=default_text(self._defaults, "infer", "device", "auto"),
        )

        self._source_label = QLabel("站点路径")
        form.addWidget(QLabel("模型文件"), 0, 0)
        form.addWidget(self.model_input, 0, 1)
        form.addWidget(self._source_label, 1, 0)
        form.addWidget(self.site_input, 1, 1)
        form.addWidget(self.image_folder_input, 1, 1)
        self._output_label = QLabel("输出根目录")
        form.addWidget(self._output_label, 2, 0)
        form.addWidget(self.output_root_input, 2, 1)

        self.flow_source_unsampled = QPushButton("未抽样图片（默认）")
        self.flow_source_unsampled.setCheckable(True)
        self.flow_source_unsampled.setChecked(True)
        self.flow_source_unsampled.setObjectName("tabButtonActive")
        self.flow_source_all = QPushButton("全部扫描图片（含已抽样）")
        self.flow_source_all.setCheckable(True)
        self.flow_source_all.setObjectName("tabButton")
        self.flow_source_note = QLabel(_FLOW_SOURCE_HELP)
        self.flow_source_note.setObjectName("formPlaceholder")
        self.flow_source_note.setProperty("feedbackRole", "explanation")
        constrain_feedback_label(self.flow_source_note)
        self.run_path_preview = QLabel("预计 run：选择站点后创建 run_YYYYMMDD_HHMMSS")
        self.run_path_preview.setObjectName("formPlaceholder")
        self.run_path_preview.setProperty("feedbackRole", "output")
        constrain_feedback_label(self.run_path_preview)
        flow_source_group = QButtonGroup(self)
        flow_source_group.addButton(self.flow_source_unsampled)
        flow_source_group.addButton(self.flow_source_all)
        self.flow_source_unsampled.clicked.connect(self.update_flow_source_buttons)
        self.flow_source_all.clicked.connect(self.update_flow_source_buttons)
        flow_source_row = QHBoxLayout()
        flow_source_row.addWidget(self.flow_source_unsampled)
        flow_source_row.addWidget(self.flow_source_all)
        flow_source_row.addStretch(1)
        self.source_choice_panel = QFrame()
        self.source_choice_panel.setObjectName("sourceChoicePanel")
        source_choice_layout = QVBoxLayout(self.source_choice_panel)
        source_choice_layout.setContentsMargins(12, 10, 12, 10)
        source_choice_layout.setSpacing(8)
        source_choice_title = QLabel("推理来源")
        source_choice_title.setObjectName("fieldLabel")
        source_choice_layout.addWidget(source_choice_title)
        source_choice_layout.addLayout(flow_source_row)
        source_choice_layout.addWidget(self.flow_source_note)
        source_choice_layout.addWidget(self.run_path_preview)

        self.common_options_panel = QFrame()
        self.common_options_panel.setObjectName("commonOptionsPanel")
        common_options = QGridLayout(self.common_options_panel)
        common_options.setContentsMargins(12, 10, 12, 10)
        common_options.setHorizontalSpacing(12)
        common_options.setVerticalSpacing(8)
        common_fields = (
            ("confidence", self.confidence_input),
            ("IoU", self.iou_input),
            ("batch", self.batch_input),
            ("device", self.device_input),
        )
        for row, (label, widget) in enumerate(common_fields):
            common_options.addWidget(QLabel(label), row, 0)
            common_options.addWidget(widget, row, 1)

        self.advanced_toggle_button = QPushButton("高级参数")
        self.advanced_toggle_button.setCheckable(True)
        self.advanced_toggle_button.setObjectName("advancedToggleButton")
        self.advanced_toggle_button.clicked.connect(self.toggle_advanced_options)

        self.advanced_options_panel = QFrame()
        self.advanced_options_panel.setObjectName("advancedOptionsPanel")
        advanced = QGridLayout(self.advanced_options_panel)
        advanced.setContentsMargins(12, 10, 12, 10)
        advanced.setHorizontalSpacing(12)
        advanced.setVerticalSpacing(8)
        self.overwrite_output_checkbox = QCheckBox("允许覆盖已有 run 输出目录")
        self.overwrite_output_checkbox.setObjectName("riskCheckbox")
        self.overwrite_output_checkbox.setProperty("feedbackRole", "riskConfirm")
        self.overwrite_output_checkbox.setChecked(False)
        self.overwrite_output_checkbox.setToolTip(
            "通常每次会自动生成新的 run_YYYYMMDD_HHMMSS；仅在明确需要复用固定输出目录时启用。"
        )
        advanced.addWidget(self.overwrite_output_checkbox, 0, 0, 1, 2)
        advanced.addWidget(QLabel("label Y offset px"), 1, 0)
        advanced.addWidget(self.label_y_offset_input, 1, 1)
        self.advanced_options_panel.setVisible(False)

        self.result_summary = QLabel("等待推理参数。")
        self.result_summary.setObjectName("formPlaceholder")
        self.result_summary.setProperty("feedbackRole", "result")
        constrain_feedback_label(self.result_summary)
        self.progress_label = QLabel("进度：等待开始")
        self.progress_label.setObjectName("mutedText")
        self.progress_label.setProperty("feedbackRole", "status")
        self.progress_label.setWordWrap(True)
        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("taskProgressBar")
        self.progress_bar.setRange(0, 1)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        actions = QHBoxLayout()
        self.preflight_button = QPushButton("风险说明")
        self.preflight_button.setObjectName("secondaryButton")
        self.preflight_button.clicked.connect(self.show_risk_note)
        self.stop_button = QPushButton("停止推理")
        self.stop_button.setObjectName("secondaryButton")
        self.stop_button.setEnabled(False)
        self.stop_button.setToolTip("请求停止当前推理；正在运行的 YOLO 批次完成后生效。")
        self.stop_button.clicked.connect(self.stop_infer)
        self.run_button = QPushButton("开始推理")
        self.run_button.setObjectName("primaryButton")
        self.run_button.clicked.connect(self.run_infer)
        actions.addStretch(1)
        actions.addWidget(self.preflight_button)
        actions.addWidget(self.stop_button)
        actions.addWidget(self.run_button)

        left.addWidget(eyebrow)
        left.addWidget(title)
        left.addWidget(subtitle)
        left.addWidget(copy)
        left.addLayout(mode_row)
        left.addWidget(self.mode_note)
        left.addLayout(form)
        left.addWidget(self.source_choice_panel)
        left.addWidget(self.common_options_panel)
        left.addWidget(self.advanced_toggle_button)
        left.addWidget(self.advanced_options_panel)
        left.addWidget(self.result_summary)
        left.addWidget(self.progress_label)
        left.addWidget(self.progress_bar)
        self.log_box = build_log_box("[ready] 等待推理参数")
        left.addWidget(self.log_box, 1)
        left.addStretch(1)
        left.addLayout(actions)

        self.ai_assistant_panel = build_ai_assistant_panel(
            context="推理页用于使用模型生成预测标签"
        )
        self.right_support_panel = self.ai_assistant_panel

        root.addWidget(wrap_scroll_panel(self.left_main_panel), 1)
        root.addWidget(self.right_support_panel, 0)
        self.site_input.textChanged.connect(self.update_flow_output_note)
        self.output_root_input.textChanged.connect(self.update_flow_output_note)
        self.set_mode("flow")

    def apply_defaults(self, defaults: ToolDefaults) -> None:
        """Apply non-path default parameters to the page."""
        self._defaults = defaults
        self.confidence_input.setText(
            default_text(defaults, "infer", "confidence", "0.25")
        )
        self.iou_input.setText(default_text(defaults, "infer", "iou", "0.7"))
        self.batch_input.setText(default_text(defaults, "infer", "batch_size", "-1"))
        self.label_y_offset_input.setText(
            default_text(defaults, "infer", "label_y_offset_px", "0")
        )
        self.device_input.setCurrentText(default_text(defaults, "infer", "device", "auto"))
        self.overwrite_output_checkbox.setChecked(False)

    def set_mode(self, mode: str) -> None:
        """Switch Infer mode."""
        self._mode = mode
        is_flow = mode == "flow"
        self.site_input.setVisible(is_flow)
        self.image_folder_input.setVisible(not is_flow)
        self.output_root_input.setVisible(not is_flow)
        self._output_label.setVisible(not is_flow)
        self.source_choice_panel.setVisible(is_flow)
        self._source_label.setText("站点路径" if is_flow else "图片文件夹")
        if is_flow:
            self.mode_note.setText("Flow 输出固定在站点 .autolabeler/inference_results/ 下，每次自动创建 run。")
            self.flow_mode_button.setObjectName("tabButtonActive")
            self.independent_mode_button.setObjectName("tabButton")
        else:
            self.mode_note.setText("独立模式递归推理图片文件夹，不读取或更新 mapping，不复制原图。")
            self.flow_mode_button.setObjectName("tabButton")
            self.independent_mode_button.setObjectName("tabButtonActive")
        for button in (self.flow_mode_button, self.independent_mode_button):
            button.style().unpolish(button)
            button.style().polish(button)
        self.update_flow_output_note()
        self.update_flow_source_buttons()

    def toggle_advanced_options(self) -> None:
        """Show or hide less-common inference options."""
        expanded = self.advanced_toggle_button.isChecked()
        self.advanced_options_panel.setVisible(expanded)
        self.advanced_toggle_button.setText("收起高级参数" if expanded else "高级参数")

    def update_flow_source_buttons(self) -> None:
        """Keep the Flow source segmented buttons visually explicit."""
        pairs = (
            (self.flow_source_unsampled, self.flow_source_unsampled.isChecked()),
            (self.flow_source_all, self.flow_source_all.isChecked()),
        )
        for button, checked in pairs:
            button.setObjectName("tabButtonActive" if checked else "tabButton")
            button.style().unpolish(button)
            button.style().polish(button)

    def update_flow_output_note(self) -> None:
        """Render fixed Flow output root or Independent behavior note."""
        if self._mode != "flow":
            self.flow_source_note.setText("独立输出会创建 run_YYYYMMDD_HHMMSS，并在 run/labels 下保留相对目录。")
            output_text = self.output_root_input.text().strip() or "输出根目录"
            self.run_path_preview.setText(
                f"预计 run：{output_text}/run_YYYYMMDD_HHMMSS"
            )
            return
        site_text = self.site_input.text().strip()
        self.flow_source_note.setText(_FLOW_SOURCE_HELP)
        if not site_text:
            self.run_path_preview.setText("预计 run：选择站点后创建 run_YYYYMMDD_HHMMSS")
            return
        output_root = Path(site_text) / ".autolabeler" / "inference_results"
        self.run_path_preview.setText(f"预计 run：{output_root / 'run_YYYYMMDD_HHMMSS'}")

    def show_risk_note(self) -> None:
        """Show inference safety note."""
        if self._mode == "flow":
            self.result_summary.setText(_FLOW_SOURCE_HELP)
        else:
            self.result_summary.setText("独立模式会递归推理所选文件夹；输出在 run/labels 下，不改源图。")

    def run_infer(self) -> None:
        """Build InferConfig and run the worker."""
        try:
            config = self._build_config()
        except (TypeError, ValueError) as exc:
            self._show_error("参数格式错误", str(exc))
            return
        self.result_summary.setText("推理运行中...")
        self.progress_label.setText("进度：准备推理")
        self.progress_bar.setRange(0, 1)
        self.progress_bar.setValue(0)
        self.run_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self._cancel_pending = False
        self._infer_running = True
        self._progress_timer.start()
        self._task_runner.run(
            lambda: self._worker.run(config),
            self._handle_infer_outcome,
            lambda exc: self._show_error("推理失败", str(exc)),
        )

    def stop_infer(self) -> None:
        """Request cancellation for the active inference task."""
        task = self._active_infer_task()
        self._cancel_pending = True
        self.stop_button.setEnabled(False)
        self.result_summary.setText("已发送停止请求，当前批次完成后停止。")
        self.progress_label.setText("进度：正在停止推理...")
        if self._registry is None or task is None:
            return
        self._registry.cancel(task.task_id)

    def refresh_running_progress(self) -> None:
        """Render the latest active infer task progress from TaskRegistry."""
        if self._registry is None:
            return
        task = self._active_infer_task()
        if task is None:
            if self._infer_running:
                self.progress_label.setText("进度：等待任务登记")
                self.progress_bar.setRange(0, 0)
                return
            if self._progress_timer.isActive():
                self._progress_timer.stop()
            self.stop_button.setEnabled(False)
            return
        if self._cancel_pending and not task.is_cancel_requested:
            task = self._registry.cancel(task.task_id)
        self.stop_button.setEnabled(not task.is_cancel_requested)
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

    def _handle_infer_outcome(self, outcome: InferWorkerOutcome) -> None:
        self._infer_running = False
        self._cancel_pending = False
        self._progress_timer.stop()
        self.run_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        if not outcome.success or outcome.result is None:
            error = outcome.error
            if error is not None and error.code == ErrorCode.TASK_CANCELLED.value:
                self._show_cancelled(error.message)
                return
            message = "推理失败"
            details = "" if error is None else f"{error.code}: {error.message}"
            self._show_error(message, details)
            return
        self._show_success(outcome.result)

    def _build_config(self) -> InferConfig:
        model_path = _required_path(self.model_input, "请选择模型文件")
        common = {
            "model_path": model_path,
            "confidence": float(self.confidence_input.text().strip()),
            "iou": float(self.iou_input.text().strip()),
            "batch_size": int(self.batch_input.text().strip()),
            "device": self.device_input.currentText().strip() or "auto",
            "overwrite_output": self.overwrite_output_checkbox.isChecked(),
            "label_y_offset_px": float(self.label_y_offset_input.text().strip() or "0"),
        }
        if self._mode == "flow":
            return InferConfig(
                site_folder=_required_path(self.site_input, "请选择站点路径"),
                image_source="all" if self.flow_source_all.isChecked() else "unsampled",
                **common,
            )
        image_folder = _required_path(self.image_folder_input, "请选择图片文件夹")
        return InferConfig(
            site_folder=image_folder,
            output_base_dir=_required_path(self.output_root_input, "请选择输出根目录"),
            image_source="folder",
            image_folder=image_folder,
            **common,
        )

    def _show_success(self, result: InferResult) -> None:
        self.stop_button.setEnabled(False)
        stats = result.statistics
        self.progress_bar.setRange(0, max(stats.pending, 1))
        self.progress_bar.setValue(stats.processed)
        self.progress_label.setText(f"进度：{stats.processed}/{stats.pending} (100%) · 推理完成")
        self.result_summary.setText(
            f"推理完成：处理 {stats.processed}，有目标 {stats.predicted}，空预测 {stats.empty_prediction}"
        )
        self.log_box.setPlainText(
            "\n".join(
                (
                    "[succeeded] 推理完成",
                    f"run: {result.run_id}",
                    f"output: {result.inference_output_dir}",
                    f"config: {result.config_path}",
                    f"classes: {result.classes_path or '未导出'}",
                    f"processed: {stats.processed}",
                    f"failed: {stats.failed}",
                )
            )
        )

    def _show_error(self, message: str, details: str) -> None:
        self._infer_running = False
        self._cancel_pending = False
        self._progress_timer.stop()
        self.run_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        text = message if not details else f"{message}：{details}"
        self.result_summary.setText(text)
        self.progress_label.setText(f"进度：{text}")
        self.log_box.setPlainText(f"[failed] {text}")

    def _show_cancelled(self, details: str) -> None:
        self._infer_running = False
        self._cancel_pending = False
        self._progress_timer.stop()
        self.run_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        text = "推理已停止" if not details else f"推理已停止：{details}"
        self.result_summary.setText(text)
        self.progress_label.setText(f"进度：{text}")
        self.log_box.setPlainText(f"[cancelled] {text}")

    def _active_infer_task(self) -> TaskHandle | None:
        """Return the newest queued/running inference task, if any."""
        if self._registry is None:
            return None
        tasks = [
            task
            for task in self._registry.list_tasks()
            if task.task_type == "infer" and task.status in {"queued", "running"}
        ]
        if not tasks:
            return None
        return sorted(tasks, key=lambda item: item.created_at)[-1]


def _line_input(value: str = "", placeholder: str = "") -> QLineEdit:
    field = QLineEdit()
    if value:
        field.setText(value)
    if placeholder:
        field.setPlaceholderText(placeholder)
    field.setObjectName("formInput")
    return field


def _combo(items: tuple[str, ...], current: str) -> QComboBox:
    field = QComboBox()
    field.addItems(items)
    field.setCurrentText(current)
    field.setObjectName("formInput")
    return field


def _required_path(field: QLineEdit, message: str) -> Path:
    text = field.text().strip()
    if not text:
        raise ValueError(message)
    return Path(text)


_FLOW_SOURCE_HELP = (
    "未抽样：仅推理 mapping.json 中 sampled=false 的图片；已推理过也会再次推理。"
    "全部扫描：推理 mapping.json 中所有图片，包含已抽样、已人工标注或已推理图片，"
    "适合全量重跑/模型检查。运行后只更新 inferred，不改变 sampled。"
)
