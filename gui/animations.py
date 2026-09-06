"""
Performance-Optimized Animation System for AutoLabeler GUI

This module provides GPU-accelerated animations using QPropertyAnimation.
Only animates transform and opacity properties to avoid layout recalculation.

Design Reference: docs/dev/UI_STANDARD.md (motion and accessibility rules)

Performance Principles:
- Use QPropertyAnimation (GPU accelerated) instead of QSS transitions
- Animate transform and opacity only (not width/height/padding)
- Support animation disabling for accessibility/performance
- Track active animations to prevent memory leaks

Usage Examples:
    # Card hover animation
    hover_anim = create_card_hover_animation(card_widget, reverse=False)
    hover_anim.start()

    # Progress bar update
    progress_anim = create_progress_animation(progress_bar, 0, 75)
    progress_anim.start()

    # Button press
    press_anim = create_button_press_animation(button, pressed=True)
    press_anim.start()

    # Page fade-in
    fade_anim = create_fade_in_animation(page_widget)
    fade_anim.start()

    # Disable all animations globally
    set_animations_enabled(False)
"""

from typing import Optional
from PySide6.QtCore import (
    QPropertyAnimation,
    QEasingCurve,
    QPoint,
    QObject,
    Property,
)
from PySide6.QtWidgets import QWidget, QProgressBar, QPushButton, QGraphicsOpacityEffect


# Global animation control flag
DISABLE_ANIMATIONS = False


def set_animations_enabled(enabled: bool) -> None:
    """
    Enable or disable animations globally.

    Args:
        enabled: True to enable animations, False to disable

    When disabled, animations complete instantly without visual transition.
    Useful for accessibility, low-performance devices, or testing.
    """
    global DISABLE_ANIMATIONS
    DISABLE_ANIMATIONS = not enabled


def get_animations_enabled() -> bool:
    """Check if animations are currently enabled."""
    return not DISABLE_ANIMATIONS


class AnimationManager:
    """
    Tracks active animations to prevent memory leaks and allow bulk cancellation.

    Usage:
        manager = AnimationManager()
        anim = create_card_hover_animation(widget)
        manager.track(anim)

        # Later, cancel all tracked animations
        manager.cancel_all()
    """

    def __init__(self):
        self._animations: list[QPropertyAnimation] = []

    def track(self, animation: QPropertyAnimation) -> QPropertyAnimation:
        """
        Track an animation for later management.

        Args:
            animation: Animation to track

        Returns:
            The same animation (for chaining)
        """
        self._animations.append(animation)

        # Auto-cleanup when animation finishes
        animation.finished.connect(lambda: self._remove(animation))

        return animation

    def _remove(self, animation: QPropertyAnimation) -> None:
        """Remove an animation from tracking (internal)."""
        if animation in self._animations:
            self._animations.remove(animation)

    def cancel_all(self) -> None:
        """Stop and remove all tracked animations."""
        for anim in self._animations[:]:  # Copy list to avoid modification during iteration
            anim.stop()
        self._animations.clear()

    def get_active_count(self) -> int:
        """Get the number of currently active animations."""
        return len(self._animations)


# Global animation manager instance
_global_manager = AnimationManager()


def get_animation_manager() -> AnimationManager:
    """Get the global animation manager instance."""
    return _global_manager


def create_card_hover_animation(
    widget: QWidget,
    reverse: bool = False,
    duration: int = 200,
    translate_y: int = -4
) -> QPropertyAnimation:
    """
    Create card hover animation with vertical translation.

    Animates the widget's position upward on hover (or downward when reversing).
    Uses OutCubic easing for smooth deceleration.

    Args:
        widget: Widget to animate
        reverse: True to reverse animation (move down), False to move up
        duration: Animation duration in milliseconds (default: 200)
        translate_y: Vertical translation in pixels (default: -4, negative = up)

    Returns:
        QPropertyAnimation instance (call .start() to begin)

    Design Spec:
        - Duration: 200ms
        - Easing: OutCubic
        - translateY: -4px (hover in), +4px (hover out)
    """
    animation = QPropertyAnimation(widget, b"pos")
    animation.setDuration(0 if DISABLE_ANIMATIONS else duration)
    animation.setEasingCurve(QEasingCurve.Type.OutCubic)

    original_pos = widget.pos()

    if reverse:
        # Reverse: move back down to original position
        start_pos = QPoint(original_pos.x(), original_pos.y() + translate_y)
        end_pos = original_pos
    else:
        # Forward: move up
        start_pos = original_pos
        end_pos = QPoint(original_pos.x(), original_pos.y() + translate_y)

    animation.setStartValue(start_pos)
    animation.setEndValue(end_pos)

    return animation


def create_progress_animation(
    progress_bar: QProgressBar,
    start_value: int,
    end_value: int,
    duration: int = 300
) -> QPropertyAnimation:
    """
    Create smooth progress bar value update animation.

    Animates progress bar value changes with linear interpolation.
    Avoids jarring jumps when progress updates.

    Args:
        progress_bar: QProgressBar to animate
        start_value: Starting progress value (0-100)
        end_value: Target progress value (0-100)
        duration: Animation duration in milliseconds (default: 300)

    Returns:
        QPropertyAnimation instance (call .start() to begin)

    Design Spec:
        - Duration: 300ms
        - Easing: Linear
        - Update interval: 500ms (handled by caller)

    Usage:
        # Update progress from 30% to 75%
        anim = create_progress_animation(progress_bar, 30, 75)
        anim.start()
    """
    animation = QPropertyAnimation(progress_bar, b"value")
    animation.setDuration(0 if DISABLE_ANIMATIONS else duration)
    animation.setEasingCurve(QEasingCurve.Type.Linear)
    animation.setStartValue(start_value)
    animation.setEndValue(end_value)

    return animation


def create_button_press_animation(
    button: QPushButton,
    pressed: bool = True,
    duration: int = 100,
    translate_y: int = 1
) -> QPropertyAnimation:
    """
    Create button press animation with slight downward translation.

    Simulates physical button press by moving button down slightly.
    Coordinates with border-bottom height change in QSS.

    Args:
        button: QPushButton to animate
        pressed: True for press down, False for release up
        duration: Animation duration in milliseconds (default: 100)
        translate_y: Vertical translation in pixels (default: 1, positive = down)

    Returns:
        QPropertyAnimation instance (call .start() to begin)

    Design Spec:
        - Duration: 100ms
        - translateY: 1px (press down)
        - Coordinates with QSS border-bottom change

    Usage:
        # On mouse press
        press_anim = create_button_press_animation(button, pressed=True)
        press_anim.start()

        # On mouse release
        release_anim = create_button_press_animation(button, pressed=False)
        release_anim.start()
    """
    animation = QPropertyAnimation(button, b"pos")
    animation.setDuration(0 if DISABLE_ANIMATIONS else duration)
    animation.setEasingCurve(QEasingCurve.Type.Linear)

    original_pos = button.pos()

    if pressed:
        # Press: move down
        start_pos = original_pos
        end_pos = QPoint(original_pos.x(), original_pos.y() + translate_y)
    else:
        # Release: move back up
        start_pos = QPoint(original_pos.x(), original_pos.y() + translate_y)
        end_pos = original_pos

    animation.setStartValue(start_pos)
    animation.setEndValue(end_pos)

    return animation


def create_fade_in_animation(
    widget: QWidget,
    duration: int = 200,
    start_opacity: float = 0.0,
    end_opacity: float = 1.0
) -> QPropertyAnimation:
    """
    Create page/widget fade-in animation.

    Animates opacity from transparent to opaque for smooth page transitions.
    Requires QGraphicsOpacityEffect to be set on the widget.

    Args:
        widget: Widget to fade in
        duration: Animation duration in milliseconds (default: 200)
        start_opacity: Starting opacity (default: 0.0, fully transparent)
        end_opacity: Target opacity (default: 1.0, fully opaque)

    Returns:
        QPropertyAnimation instance (call .start() to begin)

    Design Spec:
        - Duration: 200ms (optional feature)
        - Opacity: 0.0 → 1.0

    Usage:
        # Set up opacity effect (do once)
        opacity_effect = QGraphicsOpacityEffect()
        widget.setGraphicsEffect(opacity_effect)

        # Fade in
        fade_anim = create_fade_in_animation(widget)
        fade_anim.start()

    Note:
        QGraphicsOpacityEffect has performance cost. Use sparingly for
        page-level transitions, not individual controls.
    """
    # Ensure opacity effect exists
    opacity_effect = widget.graphicsEffect()
    if not isinstance(opacity_effect, QGraphicsOpacityEffect):
        opacity_effect = QGraphicsOpacityEffect()
        widget.setGraphicsEffect(opacity_effect)

    animation = QPropertyAnimation(opacity_effect, b"opacity")
    animation.setDuration(0 if DISABLE_ANIMATIONS else duration)
    animation.setEasingCurve(QEasingCurve.Type.Linear)
    animation.setStartValue(start_opacity)
    animation.setEndValue(end_opacity)

    return animation


def create_fade_out_animation(
    widget: QWidget,
    duration: int = 200,
    start_opacity: float = 1.0,
    end_opacity: float = 0.0
) -> QPropertyAnimation:
    """
    Create page/widget fade-out animation.

    Animates opacity from opaque to transparent for smooth dismissal.
    Requires QGraphicsOpacityEffect to be set on the widget.

    Args:
        widget: Widget to fade out
        duration: Animation duration in milliseconds (default: 200)
        start_opacity: Starting opacity (default: 1.0, fully opaque)
        end_opacity: Target opacity (default: 0.0, fully transparent)

    Returns:
        QPropertyAnimation instance (call .start() to begin)

    Usage:
        fade_anim = create_fade_out_animation(widget)
        fade_anim.finished.connect(widget.hide)  # Hide after fade
        fade_anim.start()
    """
    return create_fade_in_animation(widget, duration, start_opacity, end_opacity)


# Animation presets for common use cases

class CardHoverController:
    """
    Helper class to manage card hover animations bidirectionally.

    Automatically creates and manages both hover-in and hover-out animations
    for a card widget, preventing animation conflicts.

    Usage:
        controller = CardHoverController(card_widget)

        # On hover enter
        controller.on_hover_enter()

        # On hover leave
        controller.on_hover_leave()
    """

    def __init__(self, widget: QWidget):
        self.widget = widget
        self._current_animation: Optional[QPropertyAnimation] = None
        self._original_pos = widget.pos()

    def on_hover_enter(self) -> None:
        """Start hover-in animation (move up)."""
        if self._current_animation and self._current_animation.state() == QPropertyAnimation.State.Running:
            self._current_animation.stop()

        self._current_animation = create_card_hover_animation(self.widget, reverse=False)
        self._current_animation.start()

    def on_hover_leave(self) -> None:
        """Start hover-out animation (move down to original position)."""
        if self._current_animation and self._current_animation.state() == QPropertyAnimation.State.Running:
            self._current_animation.stop()

        # Restore original position for reverse animation
        self.widget.move(self._original_pos)
        self._current_animation = create_card_hover_animation(self.widget, reverse=True)
        self._current_animation.start()

    def reset(self) -> None:
        """Stop animation and restore original position."""
        if self._current_animation:
            self._current_animation.stop()
        self.widget.move(self._original_pos)


class ProgressAnimationController:
    """
    Helper class to manage smooth progress bar updates.

    Automatically animates progress value changes and prevents animation stacking.

    Usage:
        controller = ProgressAnimationController(progress_bar)

        # Update progress with animation
        controller.set_progress(50)
        controller.set_progress(75)  # Automatically stops previous animation
    """

    def __init__(self, progress_bar: QProgressBar):
        self.progress_bar = progress_bar
        self._current_animation: Optional[QPropertyAnimation] = None

    def set_progress(self, value: int, duration: int = 300) -> None:
        """
        Set progress bar value with smooth animation.

        Args:
            value: Target progress value (0-100)
            duration: Animation duration in milliseconds (default: 300)
        """
        # Stop any ongoing animation
        if self._current_animation and self._current_animation.state() == QPropertyAnimation.State.Running:
            self._current_animation.stop()

        current_value = self.progress_bar.value()
        self._current_animation = create_progress_animation(
            self.progress_bar,
            current_value,
            value,
            duration
        )
        self._current_animation.start()

    def set_progress_instant(self, value: int) -> None:
        """Set progress bar value instantly without animation."""
        if self._current_animation:
            self._current_animation.stop()
        self.progress_bar.setValue(value)


# Performance monitoring (optional, for development)

class AnimationPerformanceMonitor:
    """
    Monitor animation performance and auto-disable on low frame rates.

    Usage:
        monitor = AnimationPerformanceMonitor()

        # In main event loop or timer
        monitor.record_frame()

        # Check if animations should be disabled
        if monitor.should_disable_animations():
            set_animations_enabled(False)
    """

    def __init__(self, fps_threshold: float = 30.0):
        import time
        self.time = time
        self.fps_threshold = fps_threshold
        self.frame_times: list[float] = []

    def record_frame(self) -> None:
        """Record a frame timestamp for FPS calculation."""
        self.frame_times.append(self.time.time())

        # Keep only last 60 frames
        if len(self.frame_times) > 60:
            self.frame_times.pop(0)

    def get_fps(self) -> float:
        """
        Calculate current frames per second.

        Returns:
            Current FPS, or 60.0 if insufficient data
        """
        if len(self.frame_times) < 2:
            return 60.0

        elapsed = self.frame_times[-1] - self.frame_times[0]
        if elapsed <= 0:
            return 60.0

        return len(self.frame_times) / elapsed

    def should_disable_animations(self) -> bool:
        """
        Check if animations should be disabled due to poor performance.

        Returns:
            True if FPS is below threshold, False otherwise
        """
        return self.get_fps() < self.fps_threshold

    def reset(self) -> None:
        """Clear frame time history."""
        self.frame_times.clear()
