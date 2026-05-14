"""Tests for the desktop scan worker adapter."""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from core.scanner import ScanConfig
from gui.workers.scan_worker import ScanWorker
from utils.task_registry import TaskRegistry


def make_image(path: Path) -> None:
    """Create a tiny image fixture."""
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (32, 32), color=(128, 128, 128)).save(path)


def test_scan_worker_runs_core_scan_and_updates_task(tmp_path: Path) -> None:
    """Desktop scan worker is a thin adapter over the shared scan service."""
    site = tmp_path / "site"
    make_image(site / "CodeA" / "Product1" / "a1.jpg")
    registry = TaskRegistry(task_dir=tmp_path / "tasks")

    outcome = ScanWorker(registry=registry).run(ScanConfig(site_folder=site))

    assert outcome.success is True
    assert outcome.result is not None
    assert outcome.result.statistics.total_images == 1
    assert registry.get(outcome.task.task_id).status == "succeeded"


def test_scan_worker_converts_errors_to_failed_task(tmp_path: Path) -> None:
    """Desktop scan worker records business failures on the shared task registry."""
    registry = TaskRegistry(task_dir=tmp_path / "tasks")

    outcome = ScanWorker(registry=registry).run(ScanConfig(site_folder=tmp_path / "missing"))

    assert outcome.success is False
    assert outcome.error is not None
    assert outcome.error.code == "SCAN_PATH_NOT_FOUND"
    assert registry.get(outcome.task.task_id).status == "failed"
