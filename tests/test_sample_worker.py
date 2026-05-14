"""Tests for the desktop sample worker adapter."""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from core.sampler import SampleConfig
from core.scanner import ScanConfig, Scanner
from gui.workers.sample_worker import SampleWorker
from utils.task_registry import TaskRegistry


def make_image(path: Path) -> None:
    """Create a tiny image fixture."""
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (32, 32), color=(128, 128, 128)).save(path)


def make_scanned_site(site: Path) -> None:
    """Create a site and mapping.json for worker tests."""
    make_image(site / "CodeA" / "Product1" / "a1.jpg")
    Scanner().scan(ScanConfig(site_folder=site))


def test_sample_worker_runs_core_sample_and_updates_task(tmp_path: Path) -> None:
    """Desktop sample worker is a thin adapter over the shared sample service."""
    site = tmp_path / "site"
    make_scanned_site(site)
    registry = TaskRegistry(task_dir=tmp_path / "tasks")

    outcome = SampleWorker(registry=registry).run(
        SampleConfig(site_folder=site, output_dir=tmp_path / "database", count=1, full_threshold=1)
    )

    assert outcome.success is True
    assert outcome.result is not None
    assert outcome.result.statistics.sampled_count == 1
    assert registry.get(outcome.task.task_id).status == "succeeded"


def test_sample_worker_converts_errors_to_failed_task(tmp_path: Path) -> None:
    """Desktop sample worker records business failures on the shared registry."""
    site = tmp_path / "site"
    site.mkdir()
    registry = TaskRegistry(task_dir=tmp_path / "tasks")

    outcome = SampleWorker(registry=registry).run(
        SampleConfig(site_folder=site, output_dir=tmp_path / "database")
    )

    assert outcome.success is False
    assert outcome.error is not None
    assert outcome.error.code == "SAMPLE_MAPPING_NOT_FOUND"
    assert registry.get(outcome.task.task_id).status == "failed"
