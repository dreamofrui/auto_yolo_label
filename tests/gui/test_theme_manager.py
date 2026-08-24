"""Tests for theme manager functionality."""

import tempfile
from pathlib import Path

import pytest

from gui.theme_manager import ThemeManager, get_theme_manager


@pytest.fixture
def temp_config_path(tmp_path):
    """Provide a temporary config path for testing."""
    return tmp_path / "theme.json"


def test_theme_manager_initializes_with_dark_theme(temp_config_path):
    """Theme manager should default to dark theme."""
    manager = ThemeManager(temp_config_path)
    assert manager.get_current_theme() == "dark"


def test_theme_manager_generates_stylesheets(temp_config_path):
    """Theme manager should generate valid stylesheets for both themes."""
    manager = ThemeManager(temp_config_path)

    # Check dark theme stylesheet
    dark_stylesheet = manager.get_stylesheet()
    assert len(dark_stylesheet) > 1000
    assert "transition:" in dark_stylesheet
    assert "background-color:" in dark_stylesheet
    assert "#0A0E14" in dark_stylesheet  # Dark theme app background

    # Switch to light and check
    manager.set_theme("light")
    light_stylesheet = manager.get_stylesheet()
    assert len(light_stylesheet) > 1000
    assert "#F8FAFC" in light_stylesheet  # Light theme app background
    assert dark_stylesheet != light_stylesheet


def test_theme_manager_toggles_theme(temp_config_path):
    """Theme manager should toggle between dark and light."""
    manager = ThemeManager(temp_config_path)

    assert manager.get_current_theme() == "dark"

    result = manager.toggle_theme()
    assert result == "light"
    assert manager.get_current_theme() == "light"

    result = manager.toggle_theme()
    assert result == "dark"
    assert manager.get_current_theme() == "dark"


def test_theme_manager_persists_theme(temp_config_path):
    """Theme manager should persist theme preference to disk."""
    # Create manager and set theme
    manager1 = ThemeManager(temp_config_path)
    manager1.set_theme("light")

    # Create new manager instance - should load persisted theme
    manager2 = ThemeManager(temp_config_path)
    assert manager2.get_current_theme() == "light"


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

    # Should not raise, should default to dark
    manager = ThemeManager(temp_config_path)
    assert manager.get_current_theme() == "dark"


def test_theme_manager_handles_corrupt_config_gracefully(temp_config_path):
    """Theme manager should handle corrupt config file gracefully."""
    # Write invalid JSON
    temp_config_path.parent.mkdir(parents=True, exist_ok=True)
    temp_config_path.write_text("{ invalid json }", encoding="utf-8")

    # Should not raise, should default to dark
    manager = ThemeManager(temp_config_path)
    assert manager.get_current_theme() == "dark"


def test_theme_manager_stylesheet_excludes_progress_from_transition(temp_config_path):
    """Stylesheets should exclude progress bars from transitions per spec."""
    manager = ThemeManager(temp_config_path)
    stylesheet = manager.get_stylesheet()

    # Find QProgressBar section
    assert "QProgressBar" in stylesheet
    # Should have transition: none comment or explicit exclusion
    assert "transition: none" in stylesheet or "Exclude from theme transition" in stylesheet


def test_theme_manager_includes_300ms_transitions(temp_config_path):
    """Stylesheets should include 300ms transitions for color properties."""
    manager = ThemeManager(temp_config_path)
    stylesheet = manager.get_stylesheet()

    # Should have transition rules with 0.3s (300ms)
    assert "0.3s" in stylesheet
    assert "background-color" in stylesheet
    assert "border-color" in stylesheet


def test_theme_manager_no_theme_change_if_already_set(temp_config_path):
    """Setting the same theme should be a no-op."""
    manager = ThemeManager(temp_config_path)

    # Set to dark (already dark)
    manager.set_theme("dark")
    assert manager.get_current_theme() == "dark"

    # Should still be dark
    manager.set_theme("dark")
    assert manager.get_current_theme() == "dark"
