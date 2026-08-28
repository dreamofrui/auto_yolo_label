"""
AutoLabeler Reusable Component Library
======================================

PySide6 widgets implementing the AutoLabeler design system.
All components follow design tokens from design_system.py and integrate with styles.qss.

Version: 1.0
Last Updated: 2026-08-24
"""

from typing import Optional, List
from enum import Enum

from PySide6.QtCore import (
    Qt, QSize, QRect, QPoint, QPropertyAnimation, QEasingCurve,
    QTimer, Property, Signal
)
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QLinearGradient, QPaintEvent, QPalette
from PySide6.QtWidgets import (
    QPushButton, QProgressBar, QWidget, QLabel, QVBoxLayout, QHBoxLayout,
    QFrame, QGraphicsOpacityEffect
)

from gui.design_system import SPACING, RADIUS, FONT_SIZE, PADDING


# =============================================================================
# BUTTON COMPONENTS
# =============================================================================

class PrimaryButton(QPushButton):
    """
    Primary action button with brand color styling.

    Object name: "primaryButton" for QSS styling.
    """

    def __init__(self, text: str = "", parent: Optional[QWidget] = None):
        super().__init__(text, parent)
        self.setObjectName("primaryButton")
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(40)


class SecondaryButton(QPushButton):
    """
    Secondary action button with subtle styling.

    Object name: "secondaryButton" for QSS styling.
    """

    def __init__(self, text: str = "", parent: Optional[QWidget] = None):
        super().__init__(text, parent)
        self.setObjectName("secondaryButton")
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(40)


class DangerButton(QPushButton):
    """
    Destructive action button with error color styling.

    Object name: "dangerButton" for QSS styling.
    """

    def __init__(self, text: str = "", parent: Optional[QWidget] = None):
        super().__init__(text, parent)
        self.setObjectName("dangerButton")
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(40)


# =============================================================================
# PROGRESS BAR COMPONENTS
# =============================================================================

class SmallProgressBar(QProgressBar):
    """
    Small progress bar with 8px height.

    Features:
    - Animated value changes (300ms)
    - Progress gradient: #0EA5E9 to #0284C7

    Object name: "smallProgressBar" for QSS styling.
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("smallProgressBar")
        self.setTextVisible(False)
        self.setFixedHeight(8)
        self.setRange(0, 100)
        self._animation: Optional[QPropertyAnimation] = None

    def setValueAnimated(self, value: int) -> None:
        """Set progress value with smooth animation."""
        if self._animation is not None:
            self._animation.stop()

        self._animation = QPropertyAnimation(self, b"value")
        self._animation.setDuration(300)
        self._animation.setStartValue(self.value())
        self._animation.setEndValue(value)
        self._animation.setEasingCurve(QEasingCurve.OutCubic)
        self._animation.start()


class LargeProgressBar(QProgressBar):
    """
    Large progress bar with 24px height and visible percentage text.

    Features:
    - Animated value changes (300ms)
    - Progress gradient: #0EA5E9 to #0284C7
    - Centered percentage text

    Object name: "largeProgressBar" for QSS styling.
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("largeProgressBar")
        self.setTextVisible(True)
        self.setAlignment(Qt.AlignCenter)
        self.setFixedHeight(24)
        self.setRange(0, 100)
        self._animation: Optional[QPropertyAnimation] = None

    def setValueAnimated(self, value: int) -> None:
        """Set progress value with smooth animation."""
        if self._animation is not None:
            self._animation.stop()

        self._animation = QPropertyAnimation(self, b"value")
        self._animation.setDuration(300)
        self._animation.setStartValue(self.value())
        self._animation.setEndValue(value)
        self._animation.setEasingCurve(QEasingCurve.OutCubic)
        self._animation.start()


# =============================================================================
# SPINNER COMPONENT
# =============================================================================

class Spinner(QWidget):
    """
    Animated spinner widget with infinite rotation.

    Features:
    - Three sizes: 16px, 32px, 48px
    - Infinite rotation animation (800ms per revolution)
    - Circular arc drawing

    Object name: "spinner" for QSS styling.
    """

    class Size(Enum):
        SMALL = 16
        MEDIUM = 32
        LARGE = 48

    def __init__(self, size: Size = Size.MEDIUM, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("spinner")
        self._size = size.value
        self._angle = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._rotate)
        self.setFixedSize(self._size, self._size)

    def start(self) -> None:
        """Start the spinner animation."""
        self._timer.start(20)  # ~50 FPS

    def stop(self) -> None:
        """Stop the spinner animation."""
        self._timer.stop()

    def _rotate(self) -> None:
        """Update rotation angle."""
        self._angle = (self._angle + 10) % 360
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        """Paint the spinner arc."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Set pen
        # The active theme stylesheet updates WindowText when the application
        # theme changes, so the painted arc follows the current palette.
        pen = QPen(self.palette().color(QPalette.WindowText))
        pen.setWidth(max(2, self._size // 8))
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)

        # Draw arc
        rect = QRect(
            pen.width() // 2,
            pen.width() // 2,
            self._size - pen.width(),
            self._size - pen.width()
        )
        painter.drawArc(rect, self._angle * 16, 270 * 16)


# =============================================================================
# STATUS BADGE COMPONENT
# =============================================================================

class StatusBadge(QLabel):
    """
    Status indicator badge with semantic colors.

    Statuses:
    - running: Info color (blue)
    - completed: Success color (green)
    - failed: Error color (red)
    - warning: Warning color (orange)
    - idle: Tertiary text color (gray)

    Object name: "statusBadge" with dynamic property "status" for QSS styling.
    """

    class Status(Enum):
        RUNNING = "running"
        COMPLETED = "completed"
        FAILED = "failed"
        WARNING = "warning"
        IDLE = "idle"

    def __init__(self, status: Status = Status.IDLE, text: str = "", parent: Optional[QWidget] = None):
        super().__init__(text or status.value.capitalize(), parent)
        self.setObjectName("statusBadge")
        self.setAlignment(Qt.AlignCenter)
        self.setFixedHeight(24)
        self.setMinimumWidth(80)
        self.setStatus(status)

    def setStatus(self, status: Status) -> None:
        """Update badge status and styling."""
        self.setProperty("status", status.value)
        self.setText(status.value.capitalize())
        self.style().unpolish(self)
        self.style().polish(self)


# =============================================================================
# CARD COMPONENT
# =============================================================================

class Card(QFrame):
    """
    Card widget with border-shadow and hover animation.

    Features:
    - Border-simulated shadow (performance optimized)
    - Hover animation: translateY -4px (200ms)
    - Rounded corners (8px)

    Object name: "card" for QSS styling.
    """

    clicked = Signal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("card")
        self._base_y = 0
        self._hover_animation: Optional[QPropertyAnimation] = None
        self._is_clickable = False

    def setClickable(self, clickable: bool) -> None:
        """Enable/disable click behavior and cursor."""
        self._is_clickable = clickable
        if clickable:
            self.setCursor(Qt.PointingHandCursor)
        else:
            self.setCursor(Qt.ArrowCursor)

    def enterEvent(self, event) -> None:
        """Animate card upward on hover."""
        if self._is_clickable:
            self._animatePosition(-4)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        """Animate card back to base position."""
        if self._is_clickable:
            self._animatePosition(0)
        super().leaveEvent(event)

    def mousePressEvent(self, event) -> None:
        """Emit clicked signal if clickable."""
        if self._is_clickable and event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

    def _animatePosition(self, offset_y: int) -> None:
        """Animate vertical position."""
        if self._hover_animation is not None:
            self._hover_animation.stop()

        current_pos = self.pos()
        if self._base_y == 0:
            self._base_y = current_pos.y()

        self._hover_animation = QPropertyAnimation(self, b"pos")
        self._hover_animation.setDuration(200)
        self._hover_animation.setStartValue(current_pos)
        self._hover_animation.setEndValue(QPoint(current_pos.x(), self._base_y + offset_y))
        self._hover_animation.setEasingCurve(QEasingCurve.OutCubic)
        self._hover_animation.start()


# =============================================================================
# EMPTY STATE COMPONENT
# =============================================================================

class EmptyState(QWidget):
    """
    Empty state display with icon, title, description, and optional actions.

    Features:
    - Icon/emoji display (64px, opacity 0.6)
    - Title (18px, 600 weight; color supplied by the active theme QSS)
    - Description (14px, line-height 1.6, max-width 480px; color supplied by the active theme QSS)
    - Primary action button (optional)
    - Secondary action link (optional)
    - Container: padding 60px 40px, min-height 320px

    Supports all scenarios from UI_DESIGN_SPEC_v2.md section 2.12:
    - Task center: 📋 "暂无任务记录"
    - Inference run list: 📂 "还没有推理运行记录"
    - Code/Product tree: 🌳 "未找到产品分组"
    - Search no results: 🔍 "未找到匹配结果"
    - Dataset empty: 📸 "数据集目录为空"
    - Independent mode: 🗺️ "独立推理不支持复核模式"

    Object name: "emptyStateContainer" for QSS styling.
    """

    def __init__(
        self,
        icon: str = "📭",
        title: str = "No Data",
        description: str = "There is nothing to display yet.",
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self.setObjectName("emptyStateContainer")

        # Container styling per spec: padding 60px 40px, min-height 320px
        self.setMinimumHeight(320)

        # Main layout
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setContentsMargins(40, 60, 40, 60)  # padding: 60px 40px
        layout.setSpacing(0)  # Manual spacing per spec

        # Icon
        self._icon_label = QLabel(icon)
        self._icon_label.setObjectName("emptyStateIcon")
        self._icon_label.setAlignment(Qt.AlignCenter)
        # Spec: 64px for emoji fallback, opacity 0.6
        self._icon_label.setStyleSheet(f"font-size: {64}px; opacity: 0.6;")
        layout.addWidget(self._icon_label)
        layout.addSpacing(24)  # margin-bottom per spec

        # Title
        self._title_label = QLabel(title)
        self._title_label.setObjectName("emptyStateTitle")
        self._title_label.setAlignment(Qt.AlignCenter)
        # Spec: 18px, 600 weight; color is supplied by the active theme QSS.
        self._title_label.setStyleSheet(
            f"font-size: {FONT_SIZE.H3}px; font-weight: 600;"
        )
        layout.addWidget(self._title_label)
        layout.addSpacing(12)  # margin-bottom per spec

        # Description
        self._desc_label = QLabel(description)
        self._desc_label.setObjectName("emptyStateDescription")
        self._desc_label.setAlignment(Qt.AlignCenter)
        self._desc_label.setWordWrap(True)
        # Spec: 14px (BODY), line-height 1.6, max-width 480px; color comes from QSS.
        self._desc_label.setStyleSheet(
            f"font-size: {FONT_SIZE.BODY}px; line-height: 1.6;"
        )
        self._desc_label.setMaximumWidth(480)
        layout.addWidget(self._desc_label)
        layout.addSpacing(28)  # margin-bottom per spec

        # Action container (buttons and links)
        self._action_layout = QVBoxLayout()
        self._action_layout.setAlignment(Qt.AlignCenter)
        self._action_layout.setSpacing(12)  # Space between primary and secondary actions
        layout.addLayout(self._action_layout)

    def addPrimaryButton(self, button: QPushButton) -> None:
        """Add a primary action button to the empty state."""
        self._action_layout.addWidget(button, alignment=Qt.AlignCenter)

    def addButton(self, button: QPushButton) -> None:
        """Add an action button to the empty state (alias for addPrimaryButton)."""
        self.addPrimaryButton(button)

    def addSecondaryLink(self, label: QLabel) -> None:
        """
        Add a secondary action link to the empty state.

        The label should be configured as a clickable link:
        - font-size: 13px
        - color supplied by the active theme QSS
        - cursor: pointer
        - text-decoration: none (or underline on hover)
        """
        label.setObjectName("emptyStateSecondaryLink")
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet(
            "font-size: 13px; text-decoration: none;"
        )
        label.setCursor(Qt.PointingHandCursor)
        self._action_layout.addWidget(label, alignment=Qt.AlignCenter)

    def setIcon(self, icon: str) -> None:
        """Update the icon."""
        self._icon_label.setText(icon)

    def setTitle(self, title: str) -> None:
        """Update the title."""
        self._title_label.setText(title)

    def setDescription(self, description: str) -> None:
        """Update the description."""
        self._desc_label.setText(description)


# =============================================================================
# LOADING PANEL COMPONENT
# =============================================================================

class LoadingPanel(QWidget):
    """
    Loading indicator with spinner and text message.

    Used to show loading state with context message.

    Object name: "loadingPanel" for QSS styling.
    """

    def __init__(
        self,
        message: str = "Loading...",
        spinner_size: Spinner.Size = Spinner.Size.MEDIUM,
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self.setObjectName("loadingPanel")

        # Main layout
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(SPACING.SPACE_4)

        # Spinner
        self._spinner = Spinner(spinner_size)
        spinner_container = QHBoxLayout()
        spinner_container.addStretch()
        spinner_container.addWidget(self._spinner)
        spinner_container.addStretch()
        layout.addLayout(spinner_container)

        # Message
        self._message_label = QLabel(message)
        self._message_label.setObjectName("loadingPanelMessage")
        self._message_label.setAlignment(Qt.AlignCenter)
        self._message_label.setStyleSheet(
            f"font-size: {FONT_SIZE.BODY}px;"
        )
        layout.addWidget(self._message_label)

        # Start spinner
        self._spinner.start()

    def setMessage(self, message: str) -> None:
        """Update the loading message."""
        self._message_label.setText(message)

    def stop(self) -> None:
        """Stop the spinner animation."""
        self._spinner.stop()


# =============================================================================
# SKELETON LOADER COMPONENT
# =============================================================================

class SkeletonLoader(QWidget):
    """
    Skeleton loading placeholder with pulsing animation.

    Used to show content structure while data is loading.

    Object name: "skeletonLoader" for QSS styling.
    """

    def __init__(
        self,
        width: int = 200,
        height: int = 20,
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self.setObjectName("skeletonLoader")
        self.setFixedSize(width, height)

        # Opacity effect for pulsing
        self._opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._opacity_effect)

        # Pulse animation
        self._pulse_animation = QPropertyAnimation(self._opacity_effect, b"opacity")
        self._pulse_animation.setDuration(1000)
        self._pulse_animation.setStartValue(0.3)
        self._pulse_animation.setEndValue(0.7)
        self._pulse_animation.setEasingCurve(QEasingCurve.InOutSine)
        self._pulse_animation.setLoopCount(-1)  # Infinite loop

    def start(self) -> None:
        """Start the pulsing animation."""
        self._pulse_animation.start()

    def stop(self) -> None:
        """Stop the pulsing animation."""
        self._pulse_animation.stop()


# =============================================================================
# SKELETON LOADER GROUP
# =============================================================================

class SkeletonLoaderGroup(QWidget):
    """
    Group of skeleton loaders for complex content structures.

    Provides preset layouts for common loading scenarios.

    Object name: "skeletonLoaderGroup" for QSS styling.
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("skeletonLoaderGroup")
        self._loaders: List[SkeletonLoader] = []
        self._layout = QVBoxLayout(self)
        self._layout.setSpacing(SPACING.SPACE_3)

    def addCardLayout(self) -> None:
        """Add skeleton loaders for a card-like layout."""
        # Title
        title_loader = SkeletonLoader(width=200, height=24)
        self._loaders.append(title_loader)
        self._layout.addWidget(title_loader)

        # Description lines
        for _ in range(2):
            desc_loader = SkeletonLoader(width=320, height=16)
            self._loaders.append(desc_loader)
            self._layout.addWidget(desc_loader)

    def addListItemLayout(self, count: int = 3) -> None:
        """Add skeleton loaders for list items."""
        for _ in range(count):
            item_loader = SkeletonLoader(width=400, height=48)
            self._loaders.append(item_loader)
            self._layout.addWidget(item_loader)

    def start(self) -> None:
        """Start all skeleton animations."""
        for loader in self._loaders:
            loader.start()

    def stop(self) -> None:
        """Stop all skeleton animations."""
        for loader in self._loaders:
            loader.stop()


# =============================================================================
# ERROR PANEL COMPONENT
# =============================================================================

class ErrorPanel(QFrame):
    """
    Error state panel with expandable technical details.

    Features:
    - Error title with icon (⚠️ or ❌)
    - Description text with line-height 1.6
    - User action suggestions (bulleted list)
    - Expandable technical details section with toggle button
    - Monospace font for technical content
    - Deep red color scheme per UI_DESIGN_SPEC_v2.md section 2.14

    Object names:
    - errorPanel: container frame
    - errorTitle: title label with icon
    - errorDescription: main description text
    - errorSuggestions: suggestions text area
    - errorTechnicalDetails: technical details content area

    Usage:
        panel = ErrorPanel(
            title="数据集验证失败",
            description="数据集目录结构不符合 YOLO 要求，无法开始训练。",
            suggestions=["确认 data.yaml 文件存在且格式正确", "检查 images/train 和 labels/train 目录是否存在"],
            technical_details="错误码: DATASET_INVALID_001\\n路径: D:\\datasets\\yolo_v3\\data.yaml"
        )
    """

    def __init__(
        self,
        title: str = "Error",
        description: str = "",
        suggestions: Optional[List[str]] = None,
        technical_details: str = "",
        icon: str = "❌",
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self.setObjectName("errorPanel")
        self.setFrameShape(QFrame.StyledPanel)

        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)  # padding: 16px 18px per spec
        layout.setSpacing(0)  # Manual spacing

        # Title with icon
        title_layout = QHBoxLayout()
        title_layout.setSpacing(8)  # gap: 8px per spec

        self._title_label = QLabel(f"{icon} {title}")
        self._title_label.setObjectName("errorTitle")
        self._title_label.setStyleSheet(
            f"font-size: {15}px; font-weight: 600; color: #EF4444;"
        )
        title_layout.addWidget(self._title_label)
        title_layout.addStretch()

        layout.addLayout(title_layout)
        layout.addSpacing(8)  # margin-bottom per spec

        # Description
        if description:
            self._desc_label = QLabel(description)
            self._desc_label.setObjectName("errorDescription")
            self._desc_label.setWordWrap(True)
            self._desc_label.setStyleSheet(
                f"font-size: {14}px; color: #FEE2E2; line-height: 1.6;"
            )
            layout.addWidget(self._desc_label)
            layout.addSpacing(12)  # margin-bottom per spec

        # User action suggestions
        if suggestions:
            suggestions_text = "\n".join(f"• {item}" for item in suggestions)
            self._suggestions_label = QLabel(suggestions_text)
            self._suggestions_label.setObjectName("errorSuggestions")
            self._suggestions_label.setWordWrap(True)
            self._suggestions_label.setStyleSheet(
                f"font-size: {14}px; color: #FEE2E2; line-height: 1.6;"
            )
            layout.addWidget(self._suggestions_label)
            layout.addSpacing(12)  # margin-bottom per spec

        # Technical details (expandable)
        if technical_details:
            self._technical_details = technical_details
            self._is_expanded = False

            # Toggle button
            self._toggle_button = QPushButton("▼ 查看技术详情")
            self._toggle_button.setObjectName("errorTechnicalToggle")
            self._toggle_button.setFlat(True)
            self._toggle_button.setCursor(Qt.PointingHandCursor)
            self._toggle_button.setStyleSheet(
                "background: transparent; border: none; color: #EF4444; "
                "font-size: 13px; font-weight: 500; text-align: left; padding: 6px 0;"
            )
            self._toggle_button.clicked.connect(self._toggle_technical_details)
            layout.addWidget(self._toggle_button)

            # Technical details content (initially hidden)
            self._details_label = QLabel(technical_details)
            self._details_label.setObjectName("errorTechnicalDetails")
            self._details_label.setWordWrap(True)
            self._details_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
            self._details_label.setStyleSheet(
                "background: #5C1B1B; border-radius: 4px; padding: 12px 14px; "
                "font-size: 13px; font-family: 'Consolas', 'Monaco', monospace; "
                "color: #FCA5A5; line-height: 1.5;"
            )
            self._details_label.setMaximumHeight(240)  # max-height per spec
            self._details_label.hide()
            layout.addSpacing(8)
            layout.addWidget(self._details_label)

        # Container styling per spec
        self.setStyleSheet(
            "QFrame#errorPanel { "
            "background-color: #7F1D1D; "
            "border: 1px solid #991B1B; "
            "border-left: 4px solid #EF4444; "
            "border-radius: 6px; "
            "}"
        )

    def _toggle_technical_details(self) -> None:
        """Toggle technical details visibility."""
        self._is_expanded = not self._is_expanded
        if self._is_expanded:
            self._details_label.show()
            self._toggle_button.setText("▲ 隐藏技术详情")
        else:
            self._details_label.hide()
            self._toggle_button.setText("▼ 查看技术详情")

    def setTitle(self, title: str, icon: str = "❌") -> None:
        """Update the error title and icon."""
        self._title_label.setText(f"{icon} {title}")

    def setDescription(self, description: str) -> None:
        """Update the error description."""
        if hasattr(self, '_desc_label'):
            self._desc_label.setText(description)

    def setSuggestions(self, suggestions: List[str]) -> None:
        """Update the user action suggestions."""
        if hasattr(self, '_suggestions_label'):
            suggestions_text = "\n".join(f"• {item}" for item in suggestions)
            self._suggestions_label.setText(suggestions_text)

    def setTechnicalDetails(self, details: str) -> None:
        """Update the technical details content."""
        if hasattr(self, '_details_label'):
            self._details_label.setText(details)


# =============================================================================
# WARNING PANEL COMPONENT
# =============================================================================

class WarningPanel(QFrame):
    """
    Warning state panel for non-blocking issues.

    Features:
    - Warning title with icon (⚠️)
    - Description text with line-height 1.5
    - Orange color scheme per UI_DESIGN_SPEC_v2.md section 2.14

    Object names:
    - warningPanel: container frame
    - warningTitle: title label with icon
    - warningDescription: description text

    Usage:
        panel = WarningPanel(
            title="验证集为空",
            description="labels/val 目录为空，训练过程中不会计算验证指标。"
        )
    """

    def __init__(
        self,
        title: str = "Warning",
        description: str = "",
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self.setObjectName("warningPanel")
        self.setFrameShape(QFrame.StyledPanel)

        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)  # padding: 14px 16px per spec
        layout.setSpacing(0)  # Manual spacing

        # Title with icon
        title_layout = QHBoxLayout()
        title_layout.setSpacing(8)  # gap: 8px per spec

        self._title_label = QLabel(f"⚠️ {title}")
        self._title_label.setObjectName("warningTitle")
        self._title_label.setStyleSheet(
            f"font-size: {14}px; font-weight: 600; color: #F59E0B;"
        )
        title_layout.addWidget(self._title_label)
        title_layout.addStretch()

        layout.addLayout(title_layout)
        layout.addSpacing(6)  # margin-bottom per spec

        # Description
        if description:
            self._desc_label = QLabel(description)
            self._desc_label.setObjectName("warningDescription")
            self._desc_label.setWordWrap(True)
            self._desc_label.setStyleSheet(
                f"font-size: {13}px; color: #FEF3C7; line-height: 1.5;"
            )
            layout.addWidget(self._desc_label)

        # Container styling per spec
        self.setStyleSheet(
            "QFrame#warningPanel { "
            "background-color: #78350F; "
            "border: 1px solid #92400E; "
            "border-left: 4px solid #F59E0B; "
            "border-radius: 6px; "
            "}"
        )

    def setTitle(self, title: str) -> None:
        """Update the warning title."""
        self._title_label.setText(f"⚠️ {title}")

    def setDescription(self, description: str) -> None:
        """Update the warning description."""
        if hasattr(self, '_desc_label'):
            self._desc_label.setText(description)


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    # Buttons
    "PrimaryButton",
    "SecondaryButton",
    "DangerButton",

    # Progress
    "SmallProgressBar",
    "LargeProgressBar",

    # Loading
    "Spinner",
    "LoadingPanel",
    "SkeletonLoader",
    "SkeletonLoaderGroup",

    # Status
    "StatusBadge",

    # Containers
    "Card",
    "EmptyState",

    # Error States
    "ErrorPanel",
    "WarningPanel",
]
