"""Restore module page for the desktop workbench."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from core.restorer import (
    IndependentRestoreConfig,
    RestoreConfig,
    RestorePreflightResult,
    RestoreResult,
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
from gui.workers.restore_worker import (
    RestorePreflightOutcome,
    RestoreWorker,
    RestoreWorkerOutcome,
)
from gui.tool_defaults import ToolDefaults
from utils.exceptions import ErrorInfo
from utils.task_registry import TaskRegistry


class RestoreWorkerProtocol(Protocol):
    """Worker shape used by RestorePage."""

    def preflight(self, config: RestoreConfig) -> RestorePreflightOutcome:
        """Run Flow restore preflight."""

    def preflight_independent(
        self, config: IndependentRestoreConfig
    ) -> RestorePreflightOutcome:
        """Run Independent restore preflight."""

    def run(self, config: RestoreConfig) -> RestoreWorkerOutcome:
        """Run Flow restore."""

    def run_independent(
        self, config: IndependentRestoreConfig
    ) -> RestoreWorkerOutcome:
        """Run Independent restore."""


class RestorePage(QWidget):
    """Interactive Restore page with mandatory preflight and confirmation."""

    def __init__(
        self,
        worker: RestoreWorkerProtocol | None = None,
        registry: TaskRegistry | None = None,
        task_runner: TaskRunner | None = None,
        defaults: ToolDefaults | None = None,
    ) -> None:
        super().__init__()
        self.setObjectName("restorePage")
        self._worker = worker or RestoreWorker(registry=registry)
        self._task_runner = task_runner or ImmediateTaskRunner()
        self._defaults = defaults or ToolDefaults()
        self._mode = "inference"
        self._preflight_ready = False

        root = QHBoxLayout(self)
        configure_tool_root(root)

        self.left_main_panel = QFrame()
        self.left_main_panel.setObjectName("leftMainPanel")
        left = QVBoxLayout(self.left_main_panel)
        configure_left_panel(left)

        eyebrow = QLabel("必须先预检")
        eyebrow.setObjectName("eyebrow")
        title = QLabel("还原")
        title.setObjectName("toolTitle")
        subtitle = QLabel("把 YOLO 标签写回为原图同级 VOC XML")
        subtitle.setObjectName("smallTitle")
        copy = QLabel(
            "还原会在匹配原图旁写入 XML。任何来源都必须先预检，再显式确认写回。"
        )
        copy.setObjectName("mutedText")
        copy.setWordWrap(True)

        mode_row = QHBoxLayout()
        self.inference_mode_button = _mode_button("Flow 推理结果", checked=True)
        self.dataset_mode_button = _mode_button("Flow 数据集标签")
        self.independent_mode_button = _mode_button("独立还原")
        mode_group = QButtonGroup(self)
        for button in (
            self.inference_mode_button,
            self.dataset_mode_button,
            self.independent_mode_button,
        ):
            mode_group.addButton(button)
            mode_row.addWidget(button)
        mode_row.addStretch(1)
        self.inference_mode_button.clicked.connect(lambda: self.set_mode("inference"))
        self.dataset_mode_button.clicked.connect(lambda: self.set_mode("database"))
        self.independent_mode_button.clicked.connect(
            lambda: self.set_mode("independent")
        )

        self.mode_note = QLabel("")
        self.mode_note.setObjectName("formPlaceholder")
        self.mode_note.setProperty("feedbackRole", "explanation")
        constrain_feedback_label(self.mode_note)

        form = QGridLayout()
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(10)
        self.site_input = PathPicker(
            placeholder="已扫描站点路径",
            dialog_title="选择站点路径",
        )
        self.run_input = PathPicker(
            placeholder="run_YYYYMMDD_HHMMSS 或推理 run 目录",
            dialog_title="选择推理结果目录",
        )
        self.dataset_dir_input = PathPicker(
            placeholder="YOLO 数据集目录",
            dialog_title="选择数据集目录",
        )
        self.image_root_input = PathPicker(
            placeholder="独立图片根目录",
            dialog_title="选择图片根目录",
        )
        self.label_root_input = PathPicker(
            placeholder="独立标签根目录",
            dialog_title="选择标签根目录",
        )
        self.classes_file_input = PathPicker(
            mode="file",
            placeholder="独立还原 classes.txt",
            dialog_title="选择 classes.txt",
            file_filter="Text files (*.txt);;All Files (*)",
        )
        self.overwrite_checkbox = QCheckBox("如预检发现已有 XML 冲突，允许覆盖")
        self.overwrite_checkbox.setObjectName("riskCheckbox")
        self.overwrite_checkbox.setProperty("feedbackRole", "riskConfirm")
        self.overwrite_checkbox.setChecked(False)
        self.overwrite_checkbox.setToolTip(
            "仅在预检提示已有 XML 冲突且你确实要替换时启用；启用后需要重新预检。"
        )

        self._site_label = QLabel("站点路径")
        self._run_label = QLabel("推理结果")
        self._dataset_label = QLabel("数据集目录")
        self._image_root_label = QLabel("图片根目录")
        self._label_root_label = QLabel("标签根目录")
        self._classes_file_label = QLabel("类别文件")
        for label in (
            self._site_label,
            self._run_label,
            self._dataset_label,
            self._image_root_label,
            self._label_root_label,
            self._classes_file_label,
        ):
            label.setObjectName("fieldLabel")

        form.addWidget(self._site_label, 0, 0)
        form.addWidget(self.site_input, 0, 1)
        form.addWidget(self._run_label, 1, 0)
        form.addWidget(self.run_input, 1, 1)
        form.addWidget(self._dataset_label, 2, 0)
        form.addWidget(self.dataset_dir_input, 2, 1)
        form.addWidget(self._image_root_label, 3, 0)
        form.addWidget(self.image_root_input, 3, 1)
        form.addWidget(self._label_root_label, 4, 0)
        form.addWidget(self.label_root_input, 4, 1)
        form.addWidget(self._classes_file_label, 5, 0)
        form.addWidget(self.classes_file_input, 5, 1)
        writeback_controls = QVBoxLayout()
        writeback_controls.setContentsMargins(0, 0, 0, 0)
        writeback_controls.setSpacing(6)
        writeback_label = QLabel("写回控制")
        writeback_label.setObjectName("fieldLabel")
        writeback_controls.addWidget(writeback_label)
        writeback_controls.addWidget(self.overwrite_checkbox)

        self.confirm_write_checkbox = QCheckBox("我确认写回 XML 到原图同级目录")
        self.confirm_write_checkbox.setObjectName("riskCheckbox")
        self.confirm_write_checkbox.setProperty("feedbackRole", "riskConfirm")
        self.confirm_write_checkbox.setToolTip(
            "还原会在匹配到的原图旁写入 VOC XML；预检通过后再确认执行。"
        )
        writeback_controls.addWidget(self.confirm_write_checkbox)
        self.result_summary = QLabel("等待预检。")
        self.result_summary.setObjectName("formPlaceholder")
        self.result_summary.setProperty("feedbackRole", "result")
        constrain_feedback_label(self.result_summary)
        self.preflight_panel = QFrame()
        self.preflight_panel.setObjectName("preflightPanel")
        preflight_layout = QGridLayout(self.preflight_panel)
        preflight_layout.setContentsMargins(10, 8, 10, 8)
        preflight_layout.setHorizontalSpacing(8)
        self.preflight_match_summary = QLabel("匹配质量：等待预检")
        self.preflight_match_summary.setObjectName("preflightSummary")
        self.preflight_match_summary.setProperty("feedbackRole", "output")
        constrain_feedback_label(self.preflight_match_summary)
        self.preflight_write_summary = QLabel("写入影响：等待预检")
        self.preflight_write_summary.setObjectName("preflightSummary")
        self.preflight_write_summary.setProperty("feedbackRole", "risk")
        constrain_feedback_label(self.preflight_write_summary)
        preflight_layout.addWidget(self.preflight_match_summary, 0, 0)
        preflight_layout.addWidget(self.preflight_write_summary, 0, 1)

        actions = QHBoxLayout()
        self.preflight_button = QPushButton("预检")
        self.preflight_button.setObjectName("secondaryButton")
        self.preflight_button.clicked.connect(self.run_preflight)
        self.run_button = QPushButton("开始还原")
        self.run_button.setObjectName("primaryButton")
        self.run_button.clicked.connect(self.run_restore)
        actions.addStretch(1)
        actions.addWidget(self.preflight_button)
        actions.addWidget(self.run_button)

        left.addWidget(eyebrow)
        left.addWidget(title)
        left.addWidget(subtitle)
        left.addWidget(copy)
        left.addLayout(mode_row)
        left.addWidget(self.mode_note)
        left.addLayout(form)
        left.addLayout(writeback_controls)
        left.addWidget(self.result_summary)
        left.addWidget(self.preflight_panel)
        self.log_box = build_log_box("[ready] 等待还原预检")
        self.log_box.setMinimumHeight(96)
        self.log_box.setMaximumHeight(140)
        left.addWidget(self.log_box, 0)
        left.addStretch(1)
        left.addLayout(actions)

        self.ai_assistant_panel = build_ai_assistant_panel(
            context="还原页用于把 YOLO 标签写回为原图同级 VOC XML"
        )
        self.right_support_panel = self.ai_assistant_panel

        self.left_scroll_area = wrap_scroll_panel(self.left_main_panel)
        root.addWidget(self.left_scroll_area, 1)
        root.addWidget(self.right_support_panel, 0)

        for field in (
            self.site_input,
            self.run_input,
            self.dataset_dir_input,
            self.image_root_input,
            self.label_root_input,
            self.classes_file_input,
        ):
            field.textChanged.connect(self._invalidate_preflight)
        self.overwrite_checkbox.stateChanged.connect(self._invalidate_preflight)
        self.confirm_write_checkbox.stateChanged.connect(self._sync_action_state)
        self.set_mode("inference")

    def apply_defaults(self, defaults: ToolDefaults) -> None:
        """Apply non-path default parameters to the page."""
        self._defaults = defaults
        self.overwrite_checkbox.setChecked(False)
        self.confirm_write_checkbox.setChecked(False)
        self._invalidate_preflight()

    def set_mode(self, mode: str) -> None:
        """Switch restore source mode."""
        self._mode = mode
        self._invalidate_preflight()
        is_inference = mode == "inference"
        is_database = mode == "database"
        is_independent = mode == "independent"
        self.site_input.setVisible(not is_independent)
        self._site_label.setVisible(not is_independent)
        self.run_input.setVisible(is_inference)
        self._run_label.setVisible(is_inference)
        self.dataset_dir_input.setVisible(is_database)
        self._dataset_label.setVisible(is_database)
        self.image_root_input.setVisible(is_independent)
        self._image_root_label.setVisible(is_independent)
        self.label_root_input.setVisible(is_independent)
        self._label_root_label.setVisible(is_independent)
        self.classes_file_input.setVisible(is_independent)
        self._classes_file_label.setVisible(is_independent)

        notes = {
            "inference": "Flow 推理结果使用 run/labels 和 mapping，把预测标签写回原图同级 XML。",
            "database": "Flow 数据集标签使用 dataset/labels/train|val 和 mapping，还原到原始站点。",
            "independent": "独立还原不读取 mapping，按标签和图片的相对路径匹配同名文件，并使用所选 classes.txt。",
        }
        self.mode_note.setText(notes[mode])
        active = {
            self.inference_mode_button: is_inference,
            self.dataset_mode_button: is_database,
            self.independent_mode_button: is_independent,
        }
        for button, checked in active.items():
            button.setObjectName("tabButtonActive" if checked else "tabButton")
            button.style().unpolish(button)
            button.style().polish(button)

    def run_preflight(self) -> None:
        """Run non-writing restore preflight."""
        try:
            config = self._build_config()
        except (TypeError, ValueError) as exc:
            self._show_error("参数格式错误", str(exc))
            return
        self.result_summary.setText("预检运行中...")
        self._task_runner.run(
            lambda: (
                self._worker.preflight_independent(config)  # type: ignore[arg-type]
                if self._mode == "independent"
                else self._worker.preflight(config)  # type: ignore[arg-type]
            ),
            self._handle_preflight_outcome,
            lambda exc: self._show_error("预检失败", str(exc)),
        )

    def _handle_preflight_outcome(self, outcome: RestorePreflightOutcome) -> None:
        if not outcome.success or outcome.result is None:
            self._show_error_info("预检失败", outcome.error)
            self._preflight_ready = False
            self._sync_action_state()
            return
        self._preflight_ready = outcome.result.can_execute
        self.confirm_write_checkbox.setChecked(False)
        self._show_preflight(outcome.result)
        self._sync_action_state()
        QTimer.singleShot(0, lambda: self._scroll_actions_into_view(retries=2))

    def run_restore(self) -> None:
        """Run restore only after preflight and explicit confirmation."""
        if not self._preflight_ready:
            self.result_summary.setText("请先完成预检，通过后才能开始写回 XML。")
            return
        if not self.confirm_write_checkbox.isChecked():
            self.result_summary.setText("确认写回 XML 到原图同级目录后，才能开始还原。")
            return
        try:
            config = self._build_config()
        except (TypeError, ValueError) as exc:
            self._show_error("参数格式错误", str(exc))
            return
        self.result_summary.setText("还原运行中...")
        self._task_runner.run(
            lambda: (
                self._worker.run_independent(config)  # type: ignore[arg-type]
                if self._mode == "independent"
                else self._worker.run(config)  # type: ignore[arg-type]
            ),
            self._handle_restore_outcome,
            lambda exc: self._show_error("还原失败", str(exc)),
        )

    def _handle_restore_outcome(self, outcome: RestoreWorkerOutcome) -> None:
        if not outcome.success or outcome.result is None:
            self._show_error_info("还原失败", outcome.error)
            return
        self._show_success(outcome.result)
        self._preflight_ready = False
        self.confirm_write_checkbox.setChecked(False)
        self._sync_action_state()

    def _build_config(self) -> RestoreConfig | IndependentRestoreConfig:
        overwrite = self.overwrite_checkbox.isChecked()
        if self._mode == "independent":
            return IndependentRestoreConfig(
                image_root=_required_path(self.image_root_input, "请选择图片根目录"),
                label_root=_required_path(self.label_root_input, "请选择标签根目录"),
                overwrite=overwrite,
                classes_file=_required_path(
                    self.classes_file_input, "请选择 classes.txt"
                ),
            )
        site_folder = _required_path(self.site_input, "请选择站点路径")
        if self._mode == "database":
            return RestoreConfig(
                site_folder=site_folder,
                source_type="database",
                database_dir=_required_path(
                    self.dataset_dir_input, "请选择数据集目录"
                ),
                overwrite=overwrite,
            )
        run_text = self.run_input.text().strip()
        if not run_text:
            raise ValueError("请选择推理结果")
        if "/" in run_text or "\\" in run_text or ":" in run_text:
            return RestoreConfig(
                site_folder=site_folder,
                source_type="inference",
                inference_run_dir=Path(run_text),
                overwrite=overwrite,
            )
        return RestoreConfig(
            site_folder=site_folder,
            source_type="inference",
            run_id=run_text,
            overwrite=overwrite,
        )

    def _invalidate_preflight(self, *_ignored: object) -> None:
        self._preflight_ready = False
        self.confirm_write_checkbox.setChecked(False)
        self._sync_action_state()

    def _sync_action_state(self, *_ignored: object) -> None:
        """Keep restore execution gated by a valid preflight and confirmation."""
        self.confirm_write_checkbox.setEnabled(self._preflight_ready)
        self.run_button.setEnabled(
            self._preflight_ready and self.confirm_write_checkbox.isChecked()
        )

    def _scroll_actions_into_view(self, *, retries: int = 0) -> None:
        """Keep write actions reachable after preflight summaries expand."""
        try:
            self.left_main_panel.adjustSize()
            self.left_scroll_area.ensureWidgetVisible(self.run_button, 0, 18)
        except RuntimeError:
            return
        if retries > 0:
            QTimer.singleShot(
                0, lambda: self._scroll_actions_into_view(retries=retries - 1)
            )

    def _show_preflight(self, result: RestorePreflightResult) -> None:
        status = "预检通过" if result.can_execute else "预检阻断"
        self.result_summary.setText(
            f"{status}：标签 {result.total_labels}，匹配 {result.matched_images}，"
            f"将写入 XML {result.xml_to_write}"
        )
        if result.can_execute:
            self.result_summary.setText(
                f"{self.result_summary.text()}；请确认写回后开始还原。"
            )
        blockers = sum(1 for issue in result.issues if issue.severity == "blocker")
        warnings = len(result.issues) - blockers
        overwrite_status = "已允许覆盖" if self.overwrite_checkbox.isChecked() else "不覆盖已有 XML"
        confirm_status = "等待写回确认" if result.can_execute else "需先处理阻断"
        classes_path = _compact_path(result.classes_path)
        self.preflight_match_summary.setText(
            f"匹配质量：标签 {result.total_labels}，匹配图片 {result.matched_images}，"
            f"classes {classes_path}"
        )
        self.preflight_write_summary.setText(
            f"写入影响：XML {result.xml_to_write}，目标目录 {len(result.target_folders)}，"
            f"{overwrite_status}，{confirm_status}，阻断 {blockers}，警告 {warnings}"
        )
        self.preflight_match_summary.setToolTip(f"classes.txt：{result.classes_path}")
        self.preflight_write_summary.setToolTip(
            "\n".join(str(folder) for folder in result.target_folders)
        )
        lines = [
            f"[preflight] {status}",
            f"mode: {result.mode}",
            f"classes: {result.classes_path}",
            f"labels: {result.total_labels}",
            f"matched: {result.matched_images}",
            f"xml_to_write: {result.xml_to_write}",
        ]
        for folder in result.target_folders:
            lines.append(f"target: {folder}")
        for issue in result.issues:
            lines.append(
                f"{issue.severity}: {issue.code} - {issue.message} ({issue.detail})"
            )
        self.log_box.setPlainText("\n".join(lines))

    def _show_success(self, result: RestoreResult) -> None:
        self.result_summary.setText(
            f"还原完成：总数 {result.total}，成功 {result.success}，失败 {result.failed}"
        )
        self.log_box.setPlainText(
            "\n".join(
                (
                    "[succeeded] 还原完成",
                    f"total: {result.total}",
                    f"success: {result.success}",
                    f"skipped: {result.skipped}",
                    f"failed: {result.failed}",
                )
            )
        )

    def _show_error_info(self, message: str, error: ErrorInfo | None) -> None:
        """Show a compact failure summary and full actionable diagnostics."""
        if error is None:
            self._show_error(message, "")
            return
        self.result_summary.setText(f"{message}：{error.code}: {error.message}")
        lines = [
            f"[failed] {message}",
            f"code: {error.code}",
            f"message: {error.message}",
        ]
        if error.details:
            lines.extend(error.details.splitlines())
        self.log_box.setPlainText("\n".join(lines))

    def _show_error(self, message: str, details: str) -> None:
        text = message if not details else f"{message}：{details}"
        self.result_summary.setText(text)
        self.log_box.setPlainText(f"[failed] {text}")


def _mode_button(text: str, checked: bool = False) -> QPushButton:
    button = QPushButton(text)
    button.setCheckable(True)
    button.setChecked(checked)
    button.setObjectName("tabButtonActive" if checked else "tabButton")
    return button


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


def _compact_path(path: Path, *, max_chars: int = 34) -> str:
    """Return a bounded path string for visible preflight summaries."""
    text = str(path)
    if len(text) <= max_chars:
        return text
    head = max(10, max_chars // 3)
    tail = max_chars - head - 3
    return f"{text[:head]}...{text[-tail:]}"
