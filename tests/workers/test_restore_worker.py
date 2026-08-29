"""Tests for the desktop restore worker adapter."""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from core.restorer import IndependentRestoreConfig, RestoreConfig
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
    (database_dir / "classes.txt").write_text("CodeA\n", encoding="utf-8")
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
    assert (site / "CodeA" / "Product1" / "a.xml").exists()
    assert not (site / "CodeA" / "Product1" / "a.txt").exists()
    assert registry.get(outcome.task.task_id).status == "succeeded"


def test_restore_worker_preflights_flow_restore_without_writing(
    tmp_path: Path,
) -> None:
    """Desktop restore worker exposes non-writing Flow restore preflight."""
    site = tmp_path / "site"
    run = site / ".autolabeler" / "inference_results" / "run_20260520_120000"
    encoded_stem = make_scanned_site(site)
    label_path = run / "labels" / "CodeA" / "Product1" / "a.txt"
    label_path.parent.mkdir(parents=True, exist_ok=True)
    label_path.write_text("0 0.500000 0.500000 0.250000 0.250000\n", encoding="utf-8")
    (run / "classes.txt").write_text("CodeA\n", encoding="utf-8")

    outcome = RestoreWorker(registry=TaskRegistry(task_dir=tmp_path / "tasks")).preflight(
        RestoreConfig(
            site_folder=site,
            source_type="inference",
            run_id="run_20260520_120000",
        )
    )

    assert outcome.success is True
    assert outcome.result is not None
    assert outcome.result.total_labels == 1
    assert outcome.result.xml_to_write == 1
    assert not (site / "CodeA" / "Product1" / "a.xml").exists()
    assert encoded_stem == "CodeA__Product1__a"


def test_restore_worker_runs_independent_restore(tmp_path: Path) -> None:
    """Desktop restore worker exposes independent restore without mapping."""
    image_root = tmp_path / "images"
    label_root = tmp_path / "labels"
    make_image(image_root / "Product1" / "a.jpg")
    label_path = label_root / "Product1" / "a.txt"
    label_path.parent.mkdir(parents=True, exist_ok=True)
    label_path.write_text("0 0.500000 0.500000 0.250000 0.250000\n", encoding="utf-8")
    (label_root / "classes.txt").write_text("CodeA\n", encoding="utf-8")
    registry = TaskRegistry(task_dir=tmp_path / "tasks")

    outcome = RestoreWorker(registry=registry).run_independent(
        IndependentRestoreConfig(image_root=image_root, label_root=label_root)
    )

    assert outcome.success is True
    assert outcome.result is not None
    assert outcome.result.success == 1
    assert (image_root / "Product1" / "a.xml").exists()
    assert registry.get(outcome.task.task_id).status == "succeeded"


def test_restore_worker_preflights_independent_restore_without_writing(
    tmp_path: Path,
) -> None:
    """Desktop restore worker exposes independent restore preflight."""
    image_root = tmp_path / "images"
    label_root = tmp_path / "labels"
    make_image(image_root / "Product1" / "a.jpg")
    label_path = label_root / "Product1" / "a.txt"
    label_path.parent.mkdir(parents=True, exist_ok=True)
    label_path.write_text("0 0.500000 0.500000 0.250000 0.250000\n", encoding="utf-8")
    (label_root / "classes.txt").write_text("CodeA\n", encoding="utf-8")

    outcome = RestoreWorker(
        registry=TaskRegistry(task_dir=tmp_path / "tasks")
    ).preflight_independent(
        IndependentRestoreConfig(image_root=image_root, label_root=label_root)
    )

    assert outcome.success is True
    assert outcome.result is not None
    assert outcome.result.mode == "independent"
    assert outcome.result.xml_to_write == 1
    assert not (image_root / "Product1" / "a.xml").exists()


def test_restore_worker_preserves_invalid_box_diagnostics(tmp_path: Path) -> None:
    """Desktop preflight returns actionable core validation details unchanged."""
    image_root = tmp_path / "images"
    label_root = tmp_path / "labels"
    image_path = image_root / "Product1" / "a.jpg"
    make_image(image_path)
    label_path = label_root / "Product1" / "a.txt"
    label_path.parent.mkdir(parents=True, exist_ok=True)
    label_path.write_text("0 0.5 1.0 0.2 0.2\n", encoding="utf-8")
    (label_root / "classes.txt").write_text("CodeA\n", encoding="utf-8")

    outcome = RestoreWorker(
        registry=TaskRegistry(task_dir=tmp_path / "tasks")
    ).preflight_independent(
        IndependentRestoreConfig(image_root=image_root, label_root=label_root)
    )

    assert outcome.success is False
    assert outcome.error is not None
    assert outcome.error.code == "VALIDATION_ERROR"
    assert outcome.error.details is not None
    assert f"label_file: {label_path}" in outcome.error.details
    assert "line: 1" in outcome.error.details
    assert "violation: ymax=35 exceeds image_height=32" in outcome.error.details


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
