"""Tests for theme manager functionality."""

from pathlib import Path

import pytest

import gui.theme_manager as theme_manager_module
from gui.design_system import LIGHT_THEME, get_current_theme
from gui.theme_manager import ThemeManager, get_theme_manager


@pytest.fixture
def temp_config_path(tmp_path):
    """Provide a temporary config path for testing."""
    return tmp_path / "theme.json"


@pytest.fixture(autouse=True)
def reset_theme_manager():
    """Keep singleton state isolated so each test exercises its own config."""
    ThemeManager._instance = None
    theme_manager_module._theme_manager_instance = None
    yield
    ThemeManager._instance = None
    theme_manager_module._theme_manager_instance = None


def test_theme_manager_initializes_with_light_theme(temp_config_path):
    """Theme manager should default to light theme."""
    manager = ThemeManager(temp_config_path)
    assert manager.get_current_theme() == "light"


def test_design_system_defaults_to_light_palette():
    """Palette-only callers should use the same light default as the manager."""
    assert get_current_theme() is LIGHT_THEME


def test_theme_manager_generates_stylesheets(temp_config_path):
    """Theme manager should default to a complete light stylesheet."""
    manager = ThemeManager(temp_config_path)

    light_stylesheet = manager.get_stylesheet()
    assert len(light_stylesheet) > 1000
    assert "background-color:" in light_stylesheet
    assert "#F8FAFC" in light_stylesheet
    assert "#0F172A" in light_stylesheet
    assert "#FFFFFF" in light_stylesheet

    manager.set_theme("dark")
    dark_stylesheet = manager.get_stylesheet()
    assert "#0A0E14" in dark_stylesheet
    assert dark_stylesheet != light_stylesheet


def test_theme_manager_toggles_theme(temp_config_path):
    """Theme manager should toggle between dark and light."""
    manager = ThemeManager(temp_config_path)

    assert manager.get_current_theme() == "light"

    result = manager.toggle_theme()
    assert result == "dark"
    assert manager.get_current_theme() == "dark"

    result = manager.toggle_theme()
    assert result == "light"
    assert manager.get_current_theme() == "light"


def test_theme_manager_persists_theme(temp_config_path):
    """Theme manager should persist theme preference to disk."""
    # Create manager and set theme
    manager1 = ThemeManager(temp_config_path)
    manager1.set_theme("dark")

    # Create new manager instance - should load persisted theme
    ThemeManager._instance = None
    manager2 = ThemeManager(temp_config_path)
    assert manager2.get_current_theme() == "dark"


def test_theme_manager_rejects_invalid_theme(temp_config_path):
    """Theme manager should reject invalid theme names."""
    manager = ThemeManager(temp_config_path)

    with pytest.raises(ValueError, match="Invalid theme"):
        manager.set_theme("invalid")


def test_theme_manager_singleton_pattern():
    """get_theme_manager should return the same instance."""
    manager1 = get_theme_manager()
    manager2 = get_theme_manager()

    assert manager1 is manager2


def test_theme_manager_handles_missing_config_gracefully(temp_config_path):
    """Theme manager should handle missing config file gracefully."""
    # Ensure config doesn't exist
    if temp_config_path.exists():
        temp_config_path.unlink()

    # Should not raise, should default to light
    manager = ThemeManager(temp_config_path)
    assert manager.get_current_theme() == "light"


def test_theme_manager_handles_corrupt_config_gracefully(temp_config_path):
    """Theme manager should handle corrupt config file gracefully."""
    # Write invalid JSON
    temp_config_path.parent.mkdir(parents=True, exist_ok=True)
    temp_config_path.write_text("{ invalid json }", encoding="utf-8")

    # Should not raise, should default to light
    manager = ThemeManager(temp_config_path)
    assert manager.get_current_theme() == "light"


def test_theme_manager_stylesheet_excludes_progress_from_transition(temp_config_path):
    """Stylesheets should exclude progress bars from transitions per spec."""
    manager = ThemeManager(temp_config_path)
    stylesheet = manager.get_stylesheet()

    # Find QProgressBar section
    assert "QProgressBar" in stylesheet
    assert "Animations handled by QPropertyAnimation" in stylesheet


def test_theme_manager_documents_python_theme_transitions(temp_config_path):
    """Stylesheets should document that transitions are handled in Python."""
    manager = ThemeManager(temp_config_path)
    stylesheet = manager.get_stylesheet()

    assert "QPropertyAnimation" in stylesheet
    assert "Transitions handled" in stylesheet


def test_theme_manager_no_theme_change_if_already_set(temp_config_path):
    """Setting the same theme should be a no-op."""
    manager = ThemeManager(temp_config_path)

    # Set to light (already light)
    manager.set_theme("light")
    assert manager.get_current_theme() == "light"

    # Should still be light
    manager.set_theme("light")
    assert manager.get_current_theme() == "light"
