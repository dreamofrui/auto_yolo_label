"""Scan module page for the desktop workbench."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from core.scanner import ScanConfig, ScanResult
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
from gui.workers.scan_worker import ScanWorker, ScanWorkerOutcome
from utils.task_registry import TaskRegistry


class ScanWorkerProtocol(Protocol):
    """Worker shape used by ScanPage."""

    def run(self, config: ScanConfig) -> ScanWorkerOutcome:
        """Run scan and return worker outcome."""


class ScanPage(QWidget):
    """Interactive Flow scan page."""

    def __init__(
        self,
        worker: ScanWorkerProtocol | None = None,
        registry: TaskRegistry | None = None,
        task_runner: TaskRunner | None = None,
    ) -> None:
        super().__init__()
        self.setObjectName("scanPage")
        self._worker = worker or ScanWorker(registry=registry)
        self._task_runner = task_runner or ImmediateTaskRunner()

        root = QHBoxLayout(self)
        configure_tool_root(root)

        self.left_main_panel = QFrame()
        self.left_main_panel.setObjectName("leftMainPanel")
        left = QVBoxLayout(self.left_main_panel)
        configure_left_panel(left)

        eyebrow = QLabel("Flow only")
        eyebrow.setObjectName("eyebrow")
        title = QLabel("扫描")
        title.setObjectName("toolTitle")
        subtitle = QLabel("建立 Flow 模式 mapping.json 和 classes.txt")
        subtitle.setObjectName("smallTitle")
        constrain_feedback_label(subtitle)
        copy = QLabel(
            "扫描只接受严格的 site / Code / Product / image 结构。结构不匹配会列出问题路径，不会整理用户文件。"
        )
        copy.setObjectName("mutedText")
        constrain_feedback_label(copy)

        self.structure_toggle_button = QPushButton("目录结构示例")
        self.structure_toggle_button.setCheckable(True)
        self.structure_toggle_button.setChecked(True)
        self.structure_toggle_button.setObjectName("advancedToggleButton")
        self.structure_example_panel = QFrame()
        self.structure_example_panel.setObjectName("scanStructureExample")
        structure_layout = QVBoxLayout(self.structure_example_panel)
        structure_layout.setContentsMargins(10, 8, 10, 8)
        structure_layout.setSpacing(3)
        for line in (
            "site/",
            "  CodeA/",
            "    Product1/",
            "      image001.jpg",
            "      image002.png",
        ):
            label = QLabel(line)
            label.setObjectName("mutedText")
            structure_layout.addWidget(label)
        self.structure_toggle_button.clicked.connect(
            self.structure_example_panel.setVisible
        )

        form = QGridLayout()
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(10)
        self.site_input = PathPicker(
            placeholder="site 根目录",
            dialog_title="选择 site 根目录",
        )
        self.output_input = PathPicker(
            placeholder="可选输出目录，默认 site/.autolabeler",
            dialog_title="选择输出目录",
        )
        form.addWidget(QLabel("站点路径"), 0, 0)
        form.addWidget(self.site_input, 0, 1)
        form.addWidget(QLabel("输出目录"), 1, 0)
        form.addWidget(self.output_input, 1, 1)

        self.result_summary = QLabel("等待扫描。")
        self.result_summary.setObjectName("formPlaceholder")
        self.result_summary.setProperty("feedbackRole", "result")
        constrain_feedback_label(self.result_summary)

        actions = QHBoxLayout()
        self.run_button = QPushButton("开始扫描")
        self.run_button.setObjectName("primaryButton")
        self.run_button.clicked.connect(self.run_scan)
        actions.addStretch(1)
        actions.addWidget(self.run_button)

        left.addWidget(eyebrow)
        left.addWidget(title)
        left.addWidget(subtitle)
        left.addWidget(copy)
        left.addWidget(self.structure_toggle_button)
        left.addWidget(self.structure_example_panel)
        left.addLayout(form)
        left.addWidget(self.result_summary)
        self.log_box = build_log_box("[ready] 等待扫描站点")
        self.log_box.setMinimumHeight(88)
        self.log_box.setMaximumHeight(120)
        left.addWidget(self.log_box)
        left.addStretch(1)
        left.addLayout(actions)

        self.ai_assistant_panel = build_ai_assistant_panel(
            context="扫描页用于建立 Flow 模式 mapping.json 和 classes.txt"
        )
        self.right_support_panel = self.ai_assistant_panel

        root.addWidget(wrap_scroll_panel(self.left_main_panel), 1)
        root.addWidget(self.right_support_panel, 0)

    def run_scan(self) -> None:
        """Build ScanConfig and run scanner worker."""
        try:
            config = self._build_config()
        except (TypeError, ValueError) as exc:
            self._show_error("参数格式错误", str(exc))
            return
        self.result_summary.setText("扫描运行中...")
        self._task_runner.run(
            lambda: self._worker.run(config),
            self._handle_scan_outcome,
            lambda exc: self._show_error("扫描失败", str(exc)),
        )

    def _handle_scan_outcome(self, outcome: ScanWorkerOutcome) -> None:
        if not outcome.success or outcome.result is None:
            error = outcome.error
            details = "" if error is None else f"{error.code}: {error.message}"
            if error is not None and error.details:
                details = f"{details} ({error.details})"
            self._show_error("扫描失败", details)
            return
        self._show_success(outcome.result)

    def _build_config(self) -> ScanConfig:
        output_text = self.output_input.text().strip()
        return ScanConfig(
            site_folder=_required_path(self.site_input, "请选择站点路径"),
            output_dir=Path(output_text) if output_text else None,
        )

    def _show_success(self, result: ScanResult) -> None:
        stats = result.statistics
        self.result_summary.setText(
            f"扫描完成：图片 {stats.total_images}，类别 {stats.total_codes}，"
            f"产品组 {stats.total_products}；mapping.json: {result.mapping_path}；"
            f"classes.txt: {result.classes_path}"
        )
        products = [
            f"{code}/{product}: {count}"
            for code, items in result.products.items()
            for product, count in items.items()
        ]
        self.log_box.setPlainText(
            "\n".join(
                (
                    "[succeeded] 扫描完成",
                    f"mapping: {result.mapping_path}",
                    f"classes: {result.classes_path}",
                    f"class_names: {', '.join(result.classes)}",
                    f"products: {'; '.join(products)}",
                )
            )
        )

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
