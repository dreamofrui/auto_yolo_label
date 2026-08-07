"""Train module page for the desktop workbench."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
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

from core.trainer import TrainConfig, TrainResult
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
from gui.workers.train_worker import TrainWorker, TrainWorkerOutcome
from utils.exceptions import ErrorCode
from utils.task_registry import TaskHandle, TaskRegistry

_TRAIN_DEVICE_OPTIONS = (
    ("auto", "auto"),
    ("cpu", "cpu"),
    ("All GPUs", "gpu"),
    ("GPU 0", "0"),
    ("GPU 1", "1"),
    ("GPU 0+1", "0,1"),
)


class TrainWorkerProtocol(Protocol):
    """Worker shape used by TrainPage."""

    def run(self, config: TrainConfig) -> TrainWorkerOutcome:
        """Run training and return a worker outcome."""


class TrainPage(QWidget):
    """Interactive Train page for standard YOLO datasets."""

    def __init__(
        self,
        worker: TrainWorkerProtocol | None = None,
        registry: TaskRegistry | None = None,
        task_runner: TaskRunner | None = None,
        defaults: ToolDefaults | None = None,
    ) -> None:
        super().__init__()
        self.setObjectName("trainPage")
        if registry is None and worker is None:
            registry = TaskRegistry(Path.home() / ".autolabeler" / "tasks")
        self._registry = registry
        self._worker = worker or TrainWorker(registry=registry)
        self._task_runner = task_runner or ImmediateTaskRunner()
        self._defaults = defaults or ToolDefaults()
        self._train_running = False
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

        eyebrow = QLabel("YOLO dataset")
        eyebrow.setObjectName("eyebrow")
        title = QLabel("训练")
        title.setObjectName("toolTitle")
        subtitle = QLabel("从标准 YOLO 数据集训练模型")
        subtitle.setObjectName("smallTitle")
        copy = QLabel(
            "训练前会校验 data.yaml、训练图片、训练标签和类别。验证集为空会提示，但不阻断。"
        )
        copy.setObjectName("mutedText")
        copy.setWordWrap(True)

        form = QGridLayout()
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(10)
        self.dataset_input = PathPicker(
            placeholder="YOLO 数据集目录",
            dialog_title="选择数据集目录",
        )
        self.model_input = PathPicker(
            mode="file",
            placeholder="初始模型 .pt",
            dialog_title="选择初始模型",
            file_filter="PyTorch weights (*.pt);;All Files (*)",
        )
        self.output_input = PathPicker(
            placeholder="训练输出目录",
            dialog_title="选择训练输出目录",
        )
        self.device_input = _combo(
            _device_option_labels(),
            current=default_text(self._defaults, "train", "device", "auto"),
        )
        self.epochs_input = _line_input(
            value=default_text(self._defaults, "train", "epochs", "2")
        )
        self.image_size_input = _line_input(
            value=default_text(self._defaults, "train", "image_size", "640")
        )
        self.batch_input = _line_input(
            value=default_text(self._defaults, "train", "batch_size", "-1")
        )
        self.patience_input = _line_input(
            value=default_text(self._defaults, "train", "patience", "50")
        )
        self.workers_input = _line_input(
            value=default_text(self._defaults, "train", "workers", "8")
        )
        self.optimizer_input = _combo(
            ("AdamW", "SGD", "Adam", "auto"),
            current=default_text(self._defaults, "train", "optimizer", "AdamW"),
        )
        self.lr0_input = _line_input(
            value=default_text(self._defaults, "train", "lr0", "0.01")
        )
        self.box_input = _line_input(
            value=default_text(self._defaults, "train", "box", "7.5")
        )
        self.cls_input = _line_input(
            value=default_text(self._defaults, "train", "cls", "0.5")
        )
        self.dfl_input = _line_input(
            value=default_text(self._defaults, "train", "dfl", "1.5")
        )
        self.scale_input = _line_input(
            value=default_text(self._defaults, "train", "scale", "0.5")
        )
        self.cache_input = _combo(
            ("ram", "disk", "false", "true"),
            current=default_text(self._defaults, "train", "cache", "ram"),
        )
        self.run_name_input = _line_input(
            value="",
            placeholder="留空自动创建 train/run",
        )
        self.overwrite_output_checkbox = QCheckBox("允许覆盖固定 run 输出")
        self.overwrite_output_checkbox.setObjectName("formCheckBox")
        self.overwrite_output_checkbox.setProperty("feedbackRole", "riskConfirm")
        self.overwrite_output_checkbox.setChecked(False)

        basic_fields = (
            ("数据集目录", self.dataset_input),
            ("初始模型", self.model_input),
            ("输出目录", self.output_input),
        )
        for row, (label, widget) in enumerate(basic_fields):
            form.addWidget(QLabel(label), row, 0)
            form.addWidget(widget, row, 1)

        self.common_options_panel = QFrame()
        self.common_options_panel.setObjectName("commonOptionsPanel")
        common = QGridLayout(self.common_options_panel)
        common.setContentsMargins(12, 10, 12, 10)
        common.setHorizontalSpacing(12)
        common.setVerticalSpacing(8)
        common_fields = (
            ("设备", self.device_input),
            ("epochs", self.epochs_input),
            ("image size", self.image_size_input),
            ("batch", self.batch_input),
        )
        for row, (label, widget) in enumerate(common_fields):
            common.addWidget(QLabel(label), row, 0)
            common.addWidget(widget, row, 1)

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
        advanced_fields = (
            ("patience", self.patience_input),
            ("workers", self.workers_input),
            ("optimizer", self.optimizer_input),
            ("lr0", self.lr0_input),
            ("box", self.box_input),
            ("cls", self.cls_input),
            ("dfl", self.dfl_input),
            ("scale", self.scale_input),
            ("cache", self.cache_input),
            ("run name", self.run_name_input),
        )
        for row, (label, widget) in enumerate(advanced_fields):
            advanced.addWidget(QLabel(label), row, 0)
            advanced.addWidget(widget, row, 1)
        advanced.addWidget(self.overwrite_output_checkbox, len(advanced_fields), 1)
        self.advanced_options_panel.setVisible(False)

        self.result_summary = QLabel("等待数据集检查或训练。")
        self.result_summary.setObjectName("formPlaceholder")
        self.result_summary.setProperty("feedbackRole", "result")
        constrain_feedback_label(self.result_summary)
        self.runtime_panel = QFrame()
        self.runtime_panel.setObjectName("runtimePanel")
        runtime_layout = QVBoxLayout(self.runtime_panel)
        runtime_layout.setContentsMargins(10, 8, 10, 8)
        runtime_layout.setSpacing(4)
        self.runtime_status_label = QLabel("等待训练")
        self.runtime_status_label.setObjectName("smallTitle")
        self.runtime_detail_label = QLabel("设备：待选择；epoch：等待；输出目录：待选择")
        self.runtime_detail_label.setObjectName("mutedText")
        self.runtime_detail_label.setProperty("feedbackRole", "status")
        constrain_feedback_label(self.runtime_detail_label)
        runtime_layout.addWidget(self.runtime_status_label)
        runtime_layout.addWidget(self.runtime_detail_label)
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
        self.preflight_button = QPushButton("检查说明")
        self.preflight_button.setObjectName("secondaryButton")
        self.preflight_button.clicked.connect(self.show_preflight_note)
        self.stop_button = QPushButton("停止训练")
        self.stop_button.setObjectName("secondaryButton")
        self.stop_button.setEnabled(False)
        self.stop_button.setToolTip("请求停止当前训练；正在运行的 epoch 完成后生效。")
        self.stop_button.clicked.connect(self.stop_train)
        self.run_button = QPushButton("开始训练")
        self.run_button.setObjectName("primaryButton")
        self.run_button.clicked.connect(self.run_train)
        actions.addStretch(1)
        actions.addWidget(self.preflight_button)
        actions.addWidget(self.stop_button)
        actions.addWidget(self.run_button)

        left.addWidget(eyebrow)
        left.addWidget(title)
        left.addWidget(subtitle)
        left.addWidget(copy)
        left.addLayout(form)
        left.addWidget(self.common_options_panel)
        left.addWidget(self.advanced_toggle_button)
        left.addWidget(self.advanced_options_panel)
        left.addWidget(self.result_summary)
        left.addWidget(self.runtime_panel)
        left.addWidget(self.progress_label)
        left.addWidget(self.progress_bar)
        self.log_box = build_log_box("[ready] 等待训练参数")
        left.addWidget(self.log_box, 1)
        left.addStretch(1)
        left.addLayout(actions)

        self.ai_assistant_panel = build_ai_assistant_panel(
            context="训练页用于从标准 YOLO 数据集训练模型"
        )
        self.right_support_panel = self.ai_assistant_panel

        root.addWidget(wrap_scroll_panel(self.left_main_panel), 1)
        root.addWidget(self.right_support_panel, 0)

    def apply_defaults(self, defaults: ToolDefaults) -> None:
        """Apply non-path default parameters to the page."""
        self._defaults = defaults
        _set_combo_value(
            self.device_input,
            _device_label_for_value(default_text(defaults, "train", "device", "auto")),
        )
        self.epochs_input.setText(default_text(defaults, "train", "epochs", "2"))
        self.image_size_input.setText(default_text(defaults, "train", "image_size", "640"))
        self.batch_input.setText(default_text(defaults, "train", "batch_size", "-1"))
        self.patience_input.setText(default_text(defaults, "train", "patience", "50"))
        self.workers_input.setText(default_text(defaults, "train", "workers", "8"))
        self.optimizer_input.setCurrentText(
            default_text(defaults, "train", "optimizer", "AdamW")
        )
        self.lr0_input.setText(default_text(defaults, "train", "lr0", "0.01"))
        self.box_input.setText(default_text(defaults, "train", "box", "7.5"))
        self.cls_input.setText(default_text(defaults, "train", "cls", "0.5"))
        self.dfl_input.setText(default_text(defaults, "train", "dfl", "1.5"))
        self.scale_input.setText(default_text(defaults, "train", "scale", "0.5"))
        self.cache_input.setCurrentText(default_text(defaults, "train", "cache", "ram"))
        self.run_name_input.setText("")
        self.overwrite_output_checkbox.setChecked(False)

    def toggle_advanced_options(self) -> None:
        """Show or hide less-common training options."""
        expanded = self.advanced_toggle_button.isChecked()
        self.advanced_options_panel.setVisible(expanded)
        self.advanced_toggle_button.setText("收起高级参数" if expanded else "高级参数")

    def show_preflight_note(self) -> None:
        """Show training validation rules without running YOLO."""
        self.result_summary.setText(
            "检查：data.yaml/classes/train images/train labels 必须有效；验证集为空只提示。"
        )

    def run_train(self) -> None:
        """Build TrainConfig from form values and run the train worker."""
        try:
            config = self._build_config()
        except (TypeError, ValueError) as exc:
            self._show_error("参数格式错误", str(exc))
            return
        self.result_summary.setText("训练运行中...")
        self.runtime_status_label.setText("训练运行中")
        self.runtime_detail_label.setText(
            f"设备：{config.device}；epoch：0/{config.epochs}；输出目录：{config.output_dir}"
        )
        self.progress_label.setText("进度：准备训练")
        self.progress_bar.setRange(0, 1)
        self.progress_bar.setValue(0)
        self.run_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self._cancel_pending = False
        self._train_running = True
        self._progress_timer.start()
        self._task_runner.run(
            lambda: self._worker.run(config),
            self._handle_train_outcome,
            lambda exc: self._show_error("训练失败", str(exc)),
        )

    def stop_train(self) -> None:
        """Request cancellation for the active training task."""
        task = self._active_train_task()
        self._cancel_pending = True
        self.stop_button.setEnabled(False)
        self.result_summary.setText("已发送停止请求，当前 epoch 完成后停止。")
        self.runtime_status_label.setText("正在停止训练")
        self.progress_label.setText("进度：正在停止训练...")
        if self._registry is None or task is None:
            return
        self._registry.cancel(task.task_id)

    def refresh_running_progress(self) -> None:
        """Render the latest active train task progress from TaskRegistry."""
        if self._registry is None:
            return
        task = self._active_train_task()
        if task is None:
            if self._train_running:
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

    def _handle_train_outcome(self, outcome: TrainWorkerOutcome) -> None:
        self._train_running = False
        self._cancel_pending = False
        self._progress_timer.stop()
        self.run_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        if not outcome.success or outcome.result is None:
            error = outcome.error
            if error is not None and error.code == ErrorCode.TRAIN_INTERRUPTED.value:
                self._show_cancelled(error.message)
                return
            message = "训练失败"
            details = "" if error is None else f"{error.code}: {error.message}"
            self._show_error(message, details)
            return

        self._show_success(outcome.result)

    def _build_config(self) -> TrainConfig:
        dataset_dir = _required_path(self.dataset_input, "请选择数据集目录")
        return TrainConfig(
            data_yaml=dataset_dir / "data.yaml",
            base_model=_required_path(self.model_input, "请选择初始模型"),
            output_dir=_required_path(self.output_input, "请选择输出目录"),
            epochs=int(self.epochs_input.text().strip()),
            batch_size=int(self.batch_input.text().strip()),
            image_size=int(self.image_size_input.text().strip()),
            device=_device_value_from_label(self.device_input.currentText()),
            patience=int(self.patience_input.text().strip()),
            workers=int(self.workers_input.text().strip()),
            optimizer=self.optimizer_input.currentText().strip(),
            lr0=float(self.lr0_input.text().strip()),
            box=float(self.box_input.text().strip()),
            cls=float(self.cls_input.text().strip()),
            dfl=float(self.dfl_input.text().strip()),
            scale=float(self.scale_input.text().strip()),
            cache=_cache_value(self.cache_input.currentText()),
            run_name=self.run_name_input.text().strip() or None,
            overwrite_output=self.overwrite_output_checkbox.isChecked(),
        )

    def _show_success(self, result: TrainResult) -> None:
        self.stop_button.setEnabled(False)
        warning_text = "" if not result.warnings else f"；提示 {len(result.warnings)} 条"
        self.result_summary.setText(f"训练完成：输出 {result.output_dir}{warning_text}")
        self.runtime_status_label.setText("训练完成")
        self.progress_bar.setRange(0, 1)
        self.progress_bar.setValue(1)
        self.progress_label.setText("进度：训练完成")
        self.runtime_detail_label.setText(
            f"设备：{result.effective_config.get('device', '未知')}；"
            f"输出目录：{result.output_dir}"
        )
        lines = [
            "[succeeded] 训练完成",
            f"best: {result.best_model}",
            f"last: {result.last_model}",
            f"output: {result.output_dir}",
        ]
        if result.preflight:
            lines.append(f"preflight: {result.preflight}")
        if result.warnings:
            lines.append(f"warnings: {'; '.join(result.warnings)}")
        self.log_box.setPlainText("\n".join(lines))

    def _show_error(self, message: str, details: str) -> None:
        self._train_running = False
        self._cancel_pending = False
        self._progress_timer.stop()
        self.run_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        text = message if not details else f"{message}：{details}"
        self.result_summary.setText(text)
        self.runtime_status_label.setText("训练失败")
        self.progress_label.setText(f"进度：{text}")
        self.log_box.setPlainText(f"[failed] {text}")

    def _show_cancelled(self, details: str) -> None:
        self._train_running = False
        self._cancel_pending = False
        self._progress_timer.stop()
        self.run_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        text = "训练已停止" if not details else f"训练已停止：{details}"
        self.result_summary.setText(text)
        self.runtime_status_label.setText("训练已停止")
        self.progress_label.setText(f"进度：{text}")
        self.log_box.setPlainText(f"[cancelled] {text}")

    def _active_train_task(self) -> TaskHandle | None:
        """Return the newest queued/running training task, if any."""
        if self._registry is None:
            return None
        tasks = [
            task
            for task in self._registry.list_tasks()
            if task.task_type == "train" and task.status in {"queued", "running"}
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
    label = _device_label_for_value(current)
    if label and label not in items:
        field.addItem(label)
    field.setCurrentText(label)
    field.setObjectName("formInput")
    return field


def _device_option_labels() -> tuple[str, ...]:
    return tuple(label for label, _value in _TRAIN_DEVICE_OPTIONS)


def _device_label_for_value(value: str) -> str:
    normalized = value.strip()
    for label, option_value in _TRAIN_DEVICE_OPTIONS:
        if normalized == option_value or normalized == label:
            return label
    return normalized or "auto"


def _device_value_from_label(label: str) -> str:
    normalized = label.strip()
    for option_label, value in _TRAIN_DEVICE_OPTIONS:
        if normalized == option_label or normalized == value:
            return value
    return normalized or "auto"


def _set_combo_value(field: QComboBox, label: str) -> None:
    if label and field.findText(label) < 0:
        field.addItem(label)
    field.setCurrentText(label)


def _cache_value(text: str) -> str | bool:
    normalized = text.strip().lower()
    if normalized == "false":
        return False
    if normalized == "true":
        return True
    return normalized or "ram"


def _required_path(field: QLineEdit, message: str) -> Path:
    text = field.text().strip()
    if not text:
        raise ValueError(message)
    return Path(text)
