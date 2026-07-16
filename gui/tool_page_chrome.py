"""Shared chrome for desktop tool pages."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTextEdit,
    QVBoxLayout,
)


def configure_tool_root(layout: QHBoxLayout) -> None:
    """Apply shared outer spacing for tool pages."""
    layout.setContentsMargins(18, 16, 18, 14)
    layout.setSpacing(10)


def configure_left_panel(layout: QVBoxLayout) -> None:
    """Apply shared inner spacing for the main form/log panel."""
    layout.setContentsMargins(18, 16, 18, 16)
    layout.setSpacing(6)


def constrain_feedback_label(label: QLabel) -> QLabel:
    """Keep long status text from expanding a tool page horizontally."""
    label.setWordWrap(True)
    label.setMinimumWidth(0)
    label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
    return label


def wrap_scroll_panel(panel: QFrame) -> QScrollArea:
    """Keep dense tool forms usable when the desktop window is short."""
    area = QScrollArea()
    area.setObjectName("toolScrollArea")
    area.setWidgetResizable(True)
    area.setFrameShape(QFrame.Shape.NoFrame)
    area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    area.setWidget(panel)
    return area


def build_log_box(ready_text: str) -> QTextEdit:
    """Build the bottom log area used by every tool page."""
    log_box = QTextEdit()
    log_box.setObjectName("logBox")
    log_box.setProperty("surfaceRole", "log")
    log_box.setReadOnly(True)
    log_box.setMinimumHeight(160)
    log_box.setPlainText(ready_text)
    return log_box


def build_ai_assistant_panel(*, context: str) -> QFrame:
    """Build the persistent right support rail shown on tool pages."""
    panel = QFrame()
    panel.setObjectName("rightSupportPanel")
    panel.setProperty("surfaceRole", "support")
    panel.setMinimumWidth(260)
    panel.setMaximumWidth(292)

    layout = QVBoxLayout(panel)
    layout.setContentsMargins(16, 16, 16, 16)
    layout.setSpacing(8)

    task_header = QHBoxLayout()
    task_title = QLabel("任务状态")
    task_title.setObjectName("panelTitle")
    task_status = QLabel("待命")
    task_status.setObjectName("aiRailBadge")
    task_header.addWidget(task_title, 1)
    task_header.addWidget(task_status, 0)

    task_copy = QLabel("填写参数后先检查路径、输出和风险；运行中会在这里保留轻量状态。")
    task_copy.setObjectName("mutedText")
    task_copy.setWordWrap(True)

    divider = QFrame()
    divider.setFrameShape(QFrame.Shape.HLine)
    divider.setObjectName("railDivider")

    header = QHBoxLayout()
    title = QLabel("AI 助手预览")
    title.setObjectName("aiRailTitle")
    badge = QLabel("PREVIEW")
    badge.setObjectName("aiRailBadge")
    header.addWidget(title, 1)
    header.addWidget(badge, 0)

    copy = QLabel(f"{context}。此功能尚未接管执行，只展示未来的参数准备方式。")
    copy.setObjectName("mutedText")
    copy.setWordWrap(True)

    thread = QTextEdit()
    thread.setObjectName("aiRailThread")
    thread.setReadOnly(True)
    thread.setPlainText(
        "用户：抽样 D:/project/A9950，比例 20%。\n\n"
        "助手预览：可准备来源、比例和输出目录，执行仍需手动确认。\n\n"
        "用户：用 best.pt 推理这个文件夹。\n\n"
        "助手预览：可切到推理页并准备模型和图片路径。"
    )

    input_box = QTextEdit()
    input_box.setObjectName("aiRailInput")
    input_box.setPlaceholderText("预览功能暂不可输入")
    input_box.setMaximumHeight(82)
    input_box.setEnabled(False)

    disabled_action = QPushButton("预览中，暂不执行")
    disabled_action.setObjectName("secondaryButton")
    disabled_action.setEnabled(False)

    layout.addLayout(task_header)
    layout.addWidget(task_copy, 0)
    layout.addWidget(divider, 0)
    layout.addLayout(header)
    layout.addWidget(copy, 0)
    layout.addWidget(thread, 1)
    layout.addWidget(input_box, 0)
    layout.addWidget(disabled_action, 0)
    return panel
