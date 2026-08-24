"""
Theme Manager for AutoLabeler
==============================

Handles theme switching between dark and light themes with optimized performance.
Implements preloading, batched stylesheet updates, and theme persistence.

Version: 1.0
Last Updated: 2026-08-24
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from PySide6.QtWidgets import QApplication

from gui.design_system import (
    DARK_THEME,
    LIGHT_THEME,
    FONT_FAMILY,
    FONT_SIZE,
    FONT_WEIGHT,
    LINE_HEIGHT,
    SPACING,
    PADDING,
    RADIUS,
    BORDER_SHADOW,
    DarkThemeColors,
    LightThemeColors,
)

ThemeMode = Literal["dark", "light"]

# Default theme persistence location
_DEFAULT_THEME_CONFIG_PATH = Path.home() / ".autolabeler" / "theme.json"


class ThemeManager:
    """
    Singleton theme manager for the AutoLabeler application.

    Responsibilities:
    - Generate complete QSS stylesheets for both themes
    - Switch themes with batched updates (300ms transitions)
    - Persist theme preference to disk
    - Provide current theme access
    """

    _instance: ThemeManager | None = None

    def __new__(cls, config_path: Path | None = None) -> ThemeManager:
        """Singleton pattern: ensure only one instance exists."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, config_path: Path | None = None) -> None:
        """Initialize theme manager (only once due to singleton pattern)."""
        if self._initialized:
            return

        self._config_path = config_path or _DEFAULT_THEME_CONFIG_PATH
        self._current_theme: ThemeMode = self._load_persisted_theme()
        self._dark_stylesheet = self._generate_stylesheet(DARK_THEME, "dark")
        self._light_stylesheet = self._generate_stylesheet(LIGHT_THEME, "light")
        self._initialized = True

    def get_current_theme(self) -> ThemeMode:
        """Return the currently active theme mode."""
        return self._current_theme

    def set_theme(self, theme: ThemeMode) -> None:
        """
        Switch to the specified theme.

        Args:
            theme: "dark" or "light"
        """
        if theme not in ("dark", "light"):
            raise ValueError(f"Invalid theme: {theme}. Must be 'dark' or 'light'.")

        if theme == self._current_theme:
            return  # Already on this theme

        self._current_theme = theme
        self._apply_current_stylesheet()
        self._persist_theme(theme)

    def toggle_theme(self) -> ThemeMode:
        """
        Toggle between dark and light themes.

        Returns:
            The new theme mode after toggling
        """
        new_theme: ThemeMode = "light" if self._current_theme == "dark" else "dark"
        self.set_theme(new_theme)
        return new_theme

    def get_stylesheet(self) -> str:
        """Return the complete QSS stylesheet for the current theme."""
        return self._dark_stylesheet if self._current_theme == "dark" else self._light_stylesheet

    def _apply_current_stylesheet(self) -> None:
        """Apply the current theme's stylesheet to the application."""
        app = QApplication.instance()
        if app is not None:
            app.setStyleSheet(self.get_stylesheet())

    def _load_persisted_theme(self) -> ThemeMode:
        """Load theme preference from disk, defaulting to dark theme."""
        try:
            if self._config_path.exists():
                data = json.loads(self._config_path.read_text(encoding="utf-8"))
                theme = data.get("theme", "dark")
                if theme in ("dark", "light"):
                    return theme
        except (OSError, json.JSONDecodeError):
            pass  # Fall through to default

        return "dark"  # Default theme

    def _persist_theme(self, theme: ThemeMode) -> None:
        """Save theme preference to disk."""
        try:
            self._config_path.parent.mkdir(parents=True, exist_ok=True)
            data = {"theme": theme}
            self._config_path.write_text(
                json.dumps(data, indent=2, ensure_ascii=False),
                encoding="utf-8"
            )
        except OSError:
            pass  # Silent fail on persistence errors

    def _generate_stylesheet(
        self, colors: DarkThemeColors | LightThemeColors, mode: str
    ) -> str:
        """
        Generate complete QSS stylesheet for a theme.

        Args:
            colors: Theme color palette
            mode: "dark" or "light" for mode-specific adjustments

        Returns:
            Complete QSS stylesheet string
        """
        # Font family setup
        font_family = FONT_FAMILY.get_sans_serif_family()
        mono_family = FONT_FAMILY.get_monospace_family()

        # Border shadow helpers
        is_dark = mode == "dark"
        shadow_light = BORDER_SHADOW.DARK_LIGHT if is_dark else BORDER_SHADOW.LIGHT_LIGHT
        shadow_medium = BORDER_SHADOW.DARK_MEDIUM if is_dark else BORDER_SHADOW.LIGHT_MEDIUM

        # Global transition setup (300ms for color properties only)
        # Excludes progress bars, spinners, and pulse animations
        transition_rule = """
            transition: background-color 0.3s ease,
                        border-color 0.3s ease,
                        color 0.3s ease;
        """

        stylesheet = f"""
/* ============================================================================
   AutoLabeler Theme: {mode.capitalize()}
   Generated by ThemeManager
   ============================================================================ */

/* Global Base Styles */
* {{
    font-family: {font_family};
    {transition_rule}
}}

QWidget {{
    background-color: {colors.BG_APP};
    color: {colors.TEXT_PRIMARY};
    font-size: {FONT_SIZE.BODY}px;
    font-weight: {FONT_WEIGHT.REGULAR};
}}

/* ============================================================================
   Application Shell
   ============================================================================ */

#workbenchView {{
    background-color: {colors.BG_APP};
}}

#loginView {{
    background-color: {colors.BG_APP};
}}

/* ============================================================================
   Side Navigation
   ============================================================================ */

#sideNav {{
    background-color: {colors.BG_APP};
    border-right: 1px solid {colors.BORDER_SUBTLE};
    min-width: 240px;
    max-width: 240px;
}}

#navMark {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                stop:0 {colors.BRAND_PRIMARY},
                                stop:1 {colors.BRAND_HOVER});
    color: #FFFFFF;
    font-size: 18px;
    font-weight: {FONT_WEIGHT.BOLD};
    border-radius: {RADIUS.LG}px;
    min-width: 40px;
    max-width: 40px;
    min-height: 40px;
    max-height: 40px;
}}

#navBrand {{
    color: {colors.TEXT_PRIMARY};
    font-size: 16px;
    font-weight: {FONT_WEIGHT.SEMIBOLD};
    line-height: {LINE_HEIGHT.TIGHT};
}}

#navSection {{
    color: {colors.TEXT_TERTIARY};
    font-size: 11px;
    font-weight: {FONT_WEIGHT.SEMIBOLD};
    text-transform: uppercase;
    letter-spacing: 0.5px;
    padding: 20px 20px 8px;
}}

QPushButton[objectName="navButton"] {{
    background-color: transparent;
    color: {colors.TEXT_SECONDARY};
    border: none;
    border-left: 3px solid transparent;
    border-radius: {RADIUS.MD}px;
    padding: 10px 20px 10px 17px;
    margin: 2px 12px;
    font-size: {FONT_SIZE.BODY}px;
    font-weight: {FONT_WEIGHT.MEDIUM};
    text-align: left;
}}

QPushButton[objectName="navButton"]:hover {{
    background-color: {colors.BG_SURFACE};
    color: {colors.TEXT_PRIMARY};
}}

QPushButton[objectName="navButton"][selected="true"] {{
    background-color: {colors.BRAND_SUBTLE};
    color: {colors.BRAND_PRIMARY};
    border-left: 3px solid {colors.BRAND_PRIMARY};
    font-weight: {FONT_WEIGHT.SEMIBOLD};
}}

/* ============================================================================
   Buttons
   ============================================================================ */

#primaryButton {{
    background-color: {colors.BRAND_PRIMARY};
    color: #FFFFFF;
    border: none;
    border-radius: {RADIUS.MD}px;
    padding: {PADDING.BUTTON_MD[0]}px {PADDING.BUTTON_MD[1]}px;
    font-size: {FONT_SIZE.BODY}px;
    font-weight: {FONT_WEIGHT.MEDIUM};
}}

#primaryButton:hover {{
    background-color: {colors.BRAND_HOVER};
    border-bottom: 2px solid {colors.BRAND_ACTIVE};
}}

#primaryButton:pressed {{
    background-color: {colors.BRAND_ACTIVE};
}}

#primaryButton:disabled {{
    background-color: {colors.BORDER_DEFAULT};
    color: {colors.TEXT_TERTIARY};
}}

#secondaryButton {{
    background-color: transparent;
    color: {colors.TEXT_SECONDARY};
    border: 1px solid {colors.BORDER_DEFAULT};
    border-radius: {RADIUS.MD}px;
    padding: {PADDING.BUTTON_MD[0]}px {PADDING.BUTTON_MD[1]}px;
    font-size: {FONT_SIZE.BODY}px;
    font-weight: {FONT_WEIGHT.MEDIUM};
}}

#secondaryButton:hover {{
    background-color: {colors.BG_HOVER};
    border-color: {colors.BORDER_EMPHASIS};
    color: {colors.TEXT_PRIMARY};
}}

#secondaryButton:pressed {{
    background-color: {colors.BG_ACTIVE};
}}

#secondaryButton:disabled {{
    background-color: transparent;
    color: {colors.TEXT_DISABLED};
    border-color: {colors.BORDER_SUBTLE};
}}

/* ============================================================================
   Input Fields
   ============================================================================ */

#formInput, QLineEdit {{
    background-color: {colors.BG_INPUT};
    color: {colors.TEXT_PRIMARY};
    border: 1px solid {colors.BORDER_DEFAULT};
    border-radius: {RADIUS.MD}px;
    padding: 10px 12px;
    font-size: {FONT_SIZE.BODY}px;
}}

#formInput:focus, QLineEdit:focus {{
    border-color: {colors.BRAND_PRIMARY};
    outline: 2px solid rgba(14, 165, 233, 0.2);
}}

#formInput:disabled, QLineEdit:disabled {{
    background-color: {colors.BG_APP};
    color: {colors.TEXT_TERTIARY};
}}

QComboBox {{
    background-color: {colors.BG_INPUT};
    color: {colors.TEXT_PRIMARY};
    border: 1px solid {colors.BORDER_DEFAULT};
    border-radius: {RADIUS.MD}px;
    padding: 10px 12px;
    font-size: {FONT_SIZE.BODY}px;
}}

QComboBox:hover {{
    border-color: {colors.BRAND_PRIMARY};
}}

QComboBox::drop-down {{
    border: none;
}}

QComboBox QAbstractItemView {{
    background-color: {colors.BG_ELEVATED};
    border: 1px solid {colors.BORDER_DEFAULT};
    selection-background-color: {colors.BRAND_SUBTLE};
    selection-color: {colors.BRAND_PRIMARY};
}}

/* ============================================================================
   Cards and Panels
   ============================================================================ */

QFrame[objectName*="Card"], QFrame[objectName*="Panel"] {{
    background-color: {colors.BG_SURFACE};
    border: 1px solid {colors.BORDER_SUBTLE};
    border-bottom: 2px solid {shadow_light[1]};
    border-radius: {RADIUS.LG}px;
    padding: {PADDING.CARD_PADDING}px;
}}

#homeHero, #homeModulePanel, #homeSupportPanel {{
    background-color: {colors.BG_SURFACE};
    border: 1px solid {colors.BORDER_SUBTLE};
    border-bottom: 2px solid {shadow_light[1]};
    border-radius: {RADIUS.LG}px;
}}

#aiPreview {{
    background-color: {colors.BG_SURFACE};
    border: 1px solid {colors.BORDER_SUBTLE};
    border-radius: {RADIUS.LG}px;
}}

/* ============================================================================
   Module Cards (Homepage)
   ============================================================================ */

QPushButton[objectName="moduleCardButton"] {{
    background-color: {colors.BG_SURFACE};
    border: 1px solid {colors.BORDER_SUBTLE};
    border-bottom: 2px solid {shadow_light[1]};
    border-radius: {RADIUS.LG}px;
    padding: 10px 12px;
    text-align: center;
}}

QPushButton[objectName="moduleCardButton"]:hover {{
    border-color: {colors.BORDER_DEFAULT};
    border-bottom: 3px solid {shadow_medium[1]};
    transform: translateY(-2px);
}}

/* ============================================================================
   Typography
   ============================================================================ */

#toolTitle {{
    font-size: {FONT_SIZE.H1}px;
    font-weight: {FONT_WEIGHT.BOLD};
    color: {colors.TEXT_PRIMARY};
    line-height: {LINE_HEIGHT.TIGHT};
}}

#homeTitle {{
    font-size: {FONT_SIZE.H1}px;
    font-weight: {FONT_WEIGHT.BOLD};
    color: {colors.TEXT_PRIMARY};
}}

#homeEyebrow, #eyebrow {{
    font-size: {FONT_SIZE.CAPTION}px;
    font-weight: {FONT_WEIGHT.SEMIBOLD};
    color: {colors.TEXT_TERTIARY};
    text-transform: uppercase;
    letter-spacing: 0.5px;
}}

#smallTitle {{
    font-size: {FONT_SIZE.BODY_L}px;
    font-weight: {FONT_WEIGHT.MEDIUM};
    color: {colors.TEXT_PRIMARY};
}}

#mutedText {{
    font-size: {FONT_SIZE.BODY_S}px;
    color: {colors.TEXT_SECONDARY};
    line-height: {LINE_HEIGHT.NORMAL};
}}

#moduleTitleText {{
    font-size: {FONT_SIZE.BODY_L}px;
    font-weight: {FONT_WEIGHT.SEMIBOLD};
    color: {colors.TEXT_PRIMARY};
}}

#moduleDescription {{
    font-size: {FONT_SIZE.CAPTION}px;
    color: {colors.TEXT_SECONDARY};
}}

/* ============================================================================
   Status Labels and Badges
   ============================================================================ */

QLabel[objectName="statusBadge"] {{
    font-size: {FONT_SIZE.CAPTION}px;
    font-weight: {FONT_WEIGHT.SEMIBOLD};
    padding: 5px 12px;
    border-radius: {RADIUS.SM}px;
}}

/* Running status */
QLabel[objectName="statusBadge"][status="running"] {{
    background-color: {colors.SUCCESS_BG};
    color: {colors.SUCCESS};
}}

/* Completed status */
QLabel[objectName="statusBadge"][status="completed"] {{
    background-color: {colors.INFO_BG};
    color: {colors.INFO};
}}

/* Failed status */
QLabel[objectName="statusBadge"][status="failed"] {{
    background-color: {colors.ERROR_BG};
    color: {colors.ERROR};
}}

/* Warning/stopped status */
QLabel[objectName="statusBadge"][status="warning"] {{
    background-color: {colors.WARNING_BG};
    color: {colors.WARNING};
}}

/* ============================================================================
   Progress Bars
   ============================================================================ */

QProgressBar {{
    background-color: {colors.BG_INPUT};
    border: none;
    border-radius: {RADIUS.SM}px;
    text-align: center;
    transition: none;  /* Exclude from theme transition */
}}

QProgressBar::chunk {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                stop:0 {colors.BRAND_PRIMARY},
                                stop:1 {colors.BRAND_HOVER});
    border-radius: {RADIUS.SM}px;
}}

/* ============================================================================
   Scrollbars
   ============================================================================ */

QScrollBar:vertical {{
    background-color: {colors.BG_SURFACE};
    width: 12px;
    border: none;
}}

QScrollBar::handle:vertical {{
    background-color: {colors.BORDER_DEFAULT};
    border-radius: 6px;
    min-height: 30px;
}}

QScrollBar::handle:vertical:hover {{
    background-color: {colors.BORDER_EMPHASIS};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}

QScrollBar:horizontal {{
    background-color: {colors.BG_SURFACE};
    height: 12px;
    border: none;
}}

QScrollBar::handle:horizontal {{
    background-color: {colors.BORDER_DEFAULT};
    border-radius: 6px;
    min-width: 30px;
}}

QScrollBar::handle:horizontal:hover {{
    background-color: {colors.BORDER_EMPHASIS};
}}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0px;
}}

/* ============================================================================
   Login Page Specific
   ============================================================================ */

#loginStory {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                stop:0 {colors.BG_APP},
                                stop:1 {colors.BG_SURFACE});
}}

#loginBrand {{
    font-size: 32px;
    font-weight: {FONT_WEIGHT.BOLD};
    color: {colors.TEXT_PRIMARY};
}}

#loginHeadline {{
    font-size: 36px;
    font-weight: {FONT_WEIGHT.BOLD};
    color: {colors.TEXT_PRIMARY};
    line-height: {LINE_HEIGHT.TIGHT};
}}

#loginSubheadline {{
    font-size: 16px;
    color: {colors.TEXT_SECONDARY};
    line-height: {LINE_HEIGHT.RELAXED};
}}

#loginCard {{
    background-color: {colors.BG_ELEVATED};
    border: 1px solid {colors.BORDER_DEFAULT};
    border-radius: {RADIUS.XL}px;
}}

#loginFormTitle {{
    font-size: 28px;
    font-weight: {FONT_WEIGHT.BOLD};
    color: {colors.TEXT_PRIMARY};
}}

#loginFormSubtitle {{
    font-size: {FONT_SIZE.BODY}px;
    color: {colors.TEXT_SECONDARY};
}}

#loginFieldLabel {{
    font-size: {FONT_SIZE.BODY}px;
    font-weight: {FONT_WEIGHT.MEDIUM};
    color: {colors.TEXT_PRIMARY};
}}

#loginStatValue {{
    font-size: 40px;
    font-weight: {FONT_WEIGHT.BOLD};
    color: {colors.BRAND_PRIMARY};
}}

#loginStatLabel {{
    font-size: {FONT_SIZE.BODY}px;
    color: {colors.TEXT_TERTIARY};
}}

/* ============================================================================
   AI Preview Panel
   ============================================================================ */

#aiTitle {{
    font-size: {FONT_SIZE.BODY_L}px;
    font-weight: {FONT_WEIGHT.SEMIBOLD};
    color: {colors.TEXT_PRIMARY};
}}

#aiStatus {{
    background-color: {colors.WARNING_BG};
    color: {colors.WARNING};
    font-size: 10px;
    font-weight: {FONT_WEIGHT.SEMIBOLD};
    padding: 3px 8px;
    border-radius: {RADIUS.SM}px;
}}

#aiChip {{
    background-color: {colors.BG_HOVER};
    color: {colors.TEXT_SECONDARY};
    font-size: {FONT_SIZE.CAPTION}px;
    padding: 4px 10px;
    border-radius: {RADIUS.SM}px;
}}

#aiThread {{
    background-color: {colors.BG_ELEVATED};
    border-radius: {RADIUS.MD}px;
}}

#aiBubbleUser {{
    background-color: {colors.BRAND_SUBTLE};
    color: {colors.TEXT_PRIMARY};
    font-size: {FONT_SIZE.CAPTION}px;
    padding: 8px 10px;
    border-radius: {RADIUS.MD}px;
}}

#aiBubbleBot {{
    background-color: {colors.BG_HOVER};
    color: {colors.TEXT_SECONDARY};
    font-size: {FONT_SIZE.CAPTION}px;
    padding: 8px 10px;
    border-radius: {RADIUS.MD}px;
}}

#aiInput {{
    background-color: {colors.BG_ELEVATED};
    border: 1px solid {colors.BORDER_DEFAULT};
    border-radius: {RADIUS.MD}px;
}}

/* ============================================================================
   Error and Warning Panels
   ============================================================================ */

QFrame[objectName*="error"], QFrame[objectName*="Error"] {{
    background-color: {colors.ERROR_BG};
    border: 1px solid {colors.ERROR_BORDER};
    border-left: 4px solid {colors.ERROR};
    border-radius: {RADIUS.MD}px;
}}

QFrame[objectName*="warning"], QFrame[objectName*="Warning"] {{
    background-color: {colors.WARNING_BG};
    border: 1px solid {colors.WARNING_BORDER};
    border-left: 4px solid {colors.WARNING};
    border-radius: {RADIUS.MD}px;
}}

QFrame[objectName*="success"], QFrame[objectName*="Success"] {{
    background-color: {colors.SUCCESS_BG};
    border: 1px solid {colors.SUCCESS_BORDER};
    border-left: 4px solid {colors.SUCCESS};
    border-radius: {RADIUS.MD}px;
}}

/* ============================================================================
   End of Stylesheet
   ============================================================================ */
        """

        return stylesheet.strip()


# Module-level singleton accessor
_theme_manager_instance: ThemeManager | None = None


def get_theme_manager(config_path: Path | None = None) -> ThemeManager:
    """
    Get the singleton ThemeManager instance.

    Args:
        config_path: Optional custom config path (only used on first call)

    Returns:
        ThemeManager singleton instance
    """
    global _theme_manager_instance
    if _theme_manager_instance is None:
        _theme_manager_instance = ThemeManager(config_path)
    return _theme_manager_instance


__all__ = [
    "ThemeManager",
    "ThemeMode",
    "get_theme_manager",
]
