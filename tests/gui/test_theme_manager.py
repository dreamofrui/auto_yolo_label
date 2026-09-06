"""Tests for the single light-theme stylesheet manager."""

import pytest

import gui.theme_manager as theme_manager_module
from gui.design_system import LIGHT_THEME, get_current_theme
from gui.theme_manager import ThemeManager, get_theme_manager


@pytest.fixture(autouse=True)
def reset_theme_manager():
    """Keep singleton state isolated between tests."""
    ThemeManager._instance = None
    theme_manager_module._theme_manager_instance = None
    yield
    ThemeManager._instance = None
    theme_manager_module._theme_manager_instance = None


def test_design_system_defaults_to_light_palette():
    assert get_current_theme() is LIGHT_THEME


def test_theme_manager_generates_light_stylesheet():
    manager = ThemeManager()

    stylesheet = manager.get_stylesheet()
    assert len(stylesheet) > 1000
    assert "AutoLabeler Theme: Light" in stylesheet
    assert "background-color:" in stylesheet
    assert LIGHT_THEME.BG_APP in stylesheet
    assert LIGHT_THEME.TEXT_PRIMARY in stylesheet
    assert LIGHT_THEME.BG_SURFACE in stylesheet
    assert "#0A0E14" not in stylesheet


def test_theme_manager_stylesheet_excludes_progress_from_transition():
    stylesheet = ThemeManager().get_stylesheet()

    assert "QProgressBar" in stylesheet
    assert "Animations handled by QPropertyAnimation" in stylesheet


def test_theme_manager_uses_enterprise_visual_language():
    """The generated QSS exposes the navy rail/teal action system."""
    stylesheet = ThemeManager().get_stylesheet()

    assert LIGHT_THEME.NAV_BG in stylesheet
    assert LIGHT_THEME.BRAND_PRIMARY in stylesheet
    assert LIGHT_THEME.BRAND_ACCENT in stylesheet
    assert "qlineargradient" not in stylesheet


def test_theme_manager_documents_python_animations():
    stylesheet = ThemeManager().get_stylesheet()

    assert "QPropertyAnimation" in stylesheet
    assert "Transitions handled" in stylesheet


def test_theme_manager_singleton_pattern():
    assert get_theme_manager() is get_theme_manager()
