"""Tests for the desktop restore worker adapter."""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from core.restorer import RestoreConfig
from core.scanner import ScanConfig, Scanner
from gui.workers.restore_worker import RestoreWorker
from utils.path_encoder import PathEncoder
from utils.task_registry import TaskRegistry


def make_image(path: Path) -> None:
    """Create a tiny image fixture."""
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (32, 32), color=(128, 128, 128)).save(path)


def make_scanned_site(site: Path) -> str:
    """Create a site with one scanned image and return its encoded stem."""
    image_path = site / "CodeA" / "Product1" / "a.jpg"
    make_image(image_path)
    Scanner().scan(ScanConfig(site_folder=site))
    encoded_name = PathEncoder().encode("CodeA", "Product1", "a.jpg")
    return Path(encoded_name).stem


def test_restore_worker_runs_core_restore_and_updates_task(tmp_path: Path) -> None:
    """Desktop restore worker is a thin adapter over the shared restore service."""
    site = tmp_path / "site"
    database_dir = tmp_path / "database"
    encoded_stem = make_scanned_site(site)
    label_path = database_dir / "labels" / "train" / f"{encoded_stem}.txt"
    label_path.parent.mkdir(parents=True, exist_ok=True)
    label_path.write_text("0 0.500000 0.500000 0.250000 0.250000\n", encoding="utf-8")
    registry = TaskRegistry(task_dir=tmp_path / "tasks")

    outcome = RestoreWorker(registry=registry).run(
        RestoreConfig(
            site_folder=site,
            source_type="database",
            database_dir=database_dir,
            overwrite=True,
        )
    )

    assert outcome.success is True
    assert outcome.result is not None
    assert outcome.result.success == 1
    assert (site / "CodeA" / "Product1" / "a.txt").exists()
    assert registry.get(outcome.task.task_id).status == "succeeded"


def test_restore_worker_converts_errors_to_failed_task(tmp_path: Path) -> None:
    """Desktop restore worker records business failures on the shared registry."""
    site = tmp_path / "site"
    site.mkdir()
    registry = TaskRegistry(task_dir=tmp_path / "tasks")

    outcome = RestoreWorker(registry=registry).run(
        RestoreConfig(
            site_folder=site,
            source_type="database",
            database_dir=tmp_path / "database",
        )
    )

    assert outcome.success is False
    assert outcome.error is not None
    assert outcome.error.code == "RESTORE_MAPPING_NOT_FOUND"
    assert registry.get(outcome.task.task_id).status == "failed"
