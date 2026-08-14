"""Shared fixtures and helpers for GUI tests.

The GUI test seam centralizes deterministic Qt workbench setup so individual
surface tests only assert page behavior: one shared QApplication, synchronous
worker execution, closeup of top-level Qt widgets, and small file/mapping/task
helpers used by page-level tests.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PIL import Image
from PySide6.QtWidgets import QApplication

from core.scanner import ScanConfig, Scanner
from gui.task_runner import ImmediateTaskRunner
from gui.workbench import AutoLabelerWindow
from utils.task_registry import TaskRegistry

_IMMEDIATE_RUNNER = ImmediateTaskRunner()


def app() -> QApplication:
    """Return a QApplication for widget tests."""
    instance = QApplication.instance()
    if instance is None:
        instance = QApplication(sys.argv[:1])
    return instance


def make_window(**kwargs) -> AutoLabelerWindow:
    """Create a test window with synchronous GUI worker execution."""
    kwargs.setdefault("task_runner", _IMMEDIATE_RUNNER)
    return AutoLabelerWindow(**kwargs)


@pytest.fixture(autouse=True)
def close_qt_windows():
    """Close top-level Qt widgets after each test to avoid native handle buildup."""
    yield
    instance = QApplication.instance()
    if instance is None:
        return
    for widget in instance.topLevelWidgets():
        widget.close()
        widget.deleteLater()
    instance.processEvents()


def make_image(path: Path) -> None:
    """Create a tiny image fixture."""
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (16, 16), color=(128, 128, 128)).save(path)


def set_task_timestamp(
    registry: TaskRegistry,
    task_id: str,
    created_at: str,
    finished_at: str | None = None,
) -> None:
    """Force deterministic task timestamps in GUI tests."""
    task = registry.get(task_id)
    task.created_at = created_at
    if finished_at is not None:
        task.finished_at = finished_at
    registry._persist(task)


def make_scanned_site(site: Path) -> None:
    """Create a site folder and mapping for GUI sampling tests."""
    make_image(site / "CodeA" / "Product1" / "a1.jpg")
    Scanner().scan(ScanConfig(site_folder=site))
