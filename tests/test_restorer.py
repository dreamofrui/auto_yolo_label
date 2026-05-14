"""Tests for restoring labels back to source image folders."""

from __future__ import annotations

from pathlib import Path

import pytest

from core.restorer import (
    RestoreConfig,
    RestoreInvalidSourceTypeError,
    RestoreMappingNotFoundError,
    RestoreSourceNotFoundError,
    Restorer,
)
from utils.exceptions import ErrorCode, TaskCancelledError
from utils.mapping_manager import ImageInfo, MappingManager
from utils.path_encoder import PathEncoder
from utils.task_registry import TaskHandle


def make_task_handle(cancelled: bool = False) -> TaskHandle:
    """Create an in-memory restore task handle."""
    return TaskHandle(
        task_id="task_restore_test",
        task_type="restore",
        status="running",
        progress_current=0,
        progress_total=0,
        progress_message="",
        logs=[],
        result=None,
        error=None,
        created_at="2026-05-13 00:00:00",
        started_at="2026-05-13 00:00:00",
        finished_at=None,
        is_cancel_requested=cancelled,
    )


def make_site_with_mapping(site: Path) -> MappingManager:
    """Create a small site and mapping for restore tests."""
    encoder = PathEncoder()
    manager = MappingManager(site / ".autolabeler" / "mapping.json").create_new(site)
    manager.add_class(0, "CodeA")
    for name in ("a1.jpg", "a2.jpg", "a3.png"):
        image_path = site / "CodeA" / "Product1" / name
        image_path.parent.mkdir(parents=True, exist_ok=True)
        image_path.write_bytes(b"image")
        manager.add_image(
            encoder.encode("CodeA", "Product1", name),
            ImageInfo(
                original_relative=image_path.relative_to(site).as_posix(),
                code="CodeA",
                product="Product1",
                original_name=name,
                format=image_path.suffix.lower(),
            ),
        )
    manager.save()
    return manager


def write_label(path: Path, text: str = "0 0.5 0.5 0.2 0.2\n") -> None:
    """Write one label file with parent directories."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_restorer_constructs_successfully() -> None:
    """Restorer can be constructed with default dependencies."""
    restorer = Restorer()

    assert isinstance(restorer, Restorer)


def test_database_restore_copies_train_and_val_labels_and_marks_mapping(
    tmp_path: Path,
) -> None:
    """Database restore copies train/val labels to original folders and marks mapping."""
    site = tmp_path / "site"
    database = tmp_path / "database"
    make_site_with_mapping(site)
    write_label(database / "labels" / "train" / "CodeA__Product1__a1.txt", "train\n")
    write_label(database / "labels" / "val" / "CodeA__Product1__a2.txt", "val\n")

    result = Restorer().restore(
        RestoreConfig(site_folder=site, source_type="database", database_dir=database)
    )

    assert result.total == 2
    assert result.success == 2
    assert result.skipped == 0
    assert result.failed == 0
    assert (site / "CodeA" / "Product1" / "a1.txt").read_text(
        encoding="utf-8"
    ) == "train\n"
    assert (site / "CodeA" / "Product1" / "a2.txt").read_text(
        encoding="utf-8"
    ) == "val\n"
    mapping = MappingManager(site / ".autolabeler" / "mapping.json").load()
    assert mapping.get_statistics()["restored_count"] == 2


def test_inference_restore_by_run_id_copies_labels_to_original_products(
    tmp_path: Path,
) -> None:
    """Inference restore can resolve the run directory from a run id."""
    site = tmp_path / "site"
    make_site_with_mapping(site)
    write_label(
        site
        / ".autolabeler"
        / "inference_results"
        / "run_20260513_103000"
        / "CodeA"
        / "Product1"
        / "a1.txt",
        "inferred\n",
    )

    result = Restorer().restore(
        RestoreConfig(
            site_folder=site, source_type="inference", run_id="run_20260513_103000"
        )
    )

    assert result.success == 1
    assert (site / "CodeA" / "Product1" / "a1.txt").read_text(
        encoding="utf-8"
    ) == "inferred\n"


def test_inference_restore_by_explicit_run_dir(tmp_path: Path) -> None:
    """Inference restore can use an explicit run directory independent of run_id."""
    site = tmp_path / "site"
    run_dir = tmp_path / "runs" / "run_custom"
    make_site_with_mapping(site)
    write_label(run_dir / "CodeA" / "Product1" / "a2.txt", "custom\n")

    result = Restorer().restore(
        RestoreConfig(
            site_folder=site, source_type="inference", inference_run_dir=run_dir
        )
    )

    assert result.total == 1
    assert result.success == 1
    assert (site / "CodeA" / "Product1" / "a2.txt").read_text(
        encoding="utf-8"
    ) == "custom\n"


def test_restore_skips_existing_target_when_overwrite_false(tmp_path: Path) -> None:
    """Existing restored TXT files are skipped unless overwrite is enabled."""
    site = tmp_path / "site"
    database = tmp_path / "database"
    make_site_with_mapping(site)
    write_label(database / "labels" / "train" / "CodeA__Product1__a1.txt", "new\n")
    write_label(site / "CodeA" / "Product1" / "a1.txt", "old\n")

    result = Restorer().restore(
        RestoreConfig(site_folder=site, source_type="database", database_dir=database)
    )

    assert result.total == 1
    assert result.success == 0
    assert result.skipped == 1
    assert (site / "CodeA" / "Product1" / "a1.txt").read_text(
        encoding="utf-8"
    ) == "old\n"


def test_restore_overwrites_existing_target_when_overwrite_true(tmp_path: Path) -> None:
    """overwrite=True replaces existing target label files."""
    site = tmp_path / "site"
    database = tmp_path / "database"
    make_site_with_mapping(site)
    write_label(database / "labels" / "train" / "CodeA__Product1__a1.txt", "new\n")
    write_label(site / "CodeA" / "Product1" / "a1.txt", "old\n")

    result = Restorer().restore(
        RestoreConfig(
            site_folder=site,
            source_type="database",
            database_dir=database,
            overwrite=True,
        )
    )

    assert result.success == 1
    assert result.skipped == 0
    assert (site / "CodeA" / "Product1" / "a1.txt").read_text(
        encoding="utf-8"
    ) == "new\n"


def test_restore_skips_already_restored_mapping_entry(tmp_path: Path) -> None:
    """Mapping entries already marked restored are skipped by default."""
    site = tmp_path / "site"
    database = tmp_path / "database"
    manager = make_site_with_mapping(site)
    manager.mark_restored("CodeA__Product1__a1.jpg")
    manager.save()
    write_label(database / "labels" / "train" / "CodeA__Product1__a1.txt", "new\n")

    result = Restorer().restore(
        RestoreConfig(site_folder=site, source_type="database", database_dir=database)
    )

    assert result.success == 0
    assert result.skipped == 1
    assert not (site / "CodeA" / "Product1" / "a1.txt").exists()


def test_restore_filters_control_files(tmp_path: Path) -> None:
    """Control TXT files are not treated as labels."""
    site = tmp_path / "site"
    database = tmp_path / "database"
    make_site_with_mapping(site)
    write_label(database / "labels" / "train" / "CodeA__Product1__a1.txt", "label\n")
    write_label(database / "labels" / "train" / "classes.txt", "CodeA\n")
    write_label(database / "labels" / "train" / "data.yaml", "path: .\n")
    write_label(database / "labels" / "train" / "README.txt", "notes\n")

    result = Restorer().restore(
        RestoreConfig(site_folder=site, source_type="database", database_dir=database)
    )

    assert result.total == 1
    assert result.success == 1
    assert not (site / "CodeA" / "Product1" / "classes.txt").exists()


def test_database_unknown_encoded_label_records_failure_and_continues(
    tmp_path: Path,
) -> None:
    """Unknown database labels are per-file failures and do not stop later files."""
    site = tmp_path / "site"
    database = tmp_path / "database"
    make_site_with_mapping(site)
    write_label(database / "labels" / "train" / "CodeA__Product1__missing.txt", "bad\n")
    write_label(database / "labels" / "train" / "CodeA__Product1__a1.txt", "good\n")

    result = Restorer().restore(
        RestoreConfig(site_folder=site, source_type="database", database_dir=database)
    )

    assert result.total == 2
    assert result.success == 1
    assert result.failed == 1
    assert result.errors[0].target_path is None
    assert (site / "CodeA" / "Product1" / "a1.txt").exists()


def test_inference_unknown_relative_label_records_failure_and_continues(
    tmp_path: Path,
) -> None:
    """Inference labels with no matching mapping image are per-file failures."""
    site = tmp_path / "site"
    make_site_with_mapping(site)
    run = site / ".autolabeler" / "inference_results" / "run_20260513_103000"
    write_label(run / "CodeA" / "Product1" / "missing.txt", "bad\n")
    write_label(run / "CodeA" / "Product1" / "a2.txt", "good\n")

    result = Restorer().restore(
        RestoreConfig(
            site_folder=site, source_type="inference", run_id="run_20260513_103000"
        )
    )

    assert result.success == 1
    assert result.failed == 1
    assert result.errors[0].target_path is None
    assert (site / "CodeA" / "Product1" / "a2.txt").exists()


def test_copy_failure_records_error_and_continues(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Copy errors are recorded per file and later labels continue."""
    site = tmp_path / "site"
    database = tmp_path / "database"
    make_site_with_mapping(site)
    failing_source = database / "labels" / "train" / "CodeA__Product1__a1.txt"
    write_label(failing_source, "bad\n")
    write_label(database / "labels" / "train" / "CodeA__Product1__a2.txt", "good\n")

    def fake_copy2(source: Path, target: Path) -> Path:
        if source == failing_source:
            raise OSError("disk full")
        target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
        return target

    monkeypatch.setattr("core.restorer.shutil.copy2", fake_copy2)

    result = Restorer().restore(
        RestoreConfig(site_folder=site, source_type="database", database_dir=database)
    )

    assert result.success == 1
    assert result.failed == 1
    assert "disk full" in result.errors[0].reason
    assert (site / "CodeA" / "Product1" / "a2.txt").exists()


def test_missing_mapping_raises_restore_mapping_not_found(tmp_path: Path) -> None:
    """Restore requires mapping.json and does not invoke Scanner."""
    database = tmp_path / "database"
    database.mkdir()

    with pytest.raises(RestoreMappingNotFoundError) as exc_info:
        Restorer().restore(
            RestoreConfig(
                site_folder=tmp_path / "site",
                source_type="database",
                database_dir=database,
            )
        )

    assert exc_info.value.code == ErrorCode.RESTORE_MAPPING_NOT_FOUND


def test_invalid_source_type_raises_restore_invalid_source_type(tmp_path: Path) -> None:
    """Unknown source_type values are rejected."""
    site = tmp_path / "site"
    make_site_with_mapping(site)

    with pytest.raises(RestoreInvalidSourceTypeError) as exc_info:
        Restorer().restore(RestoreConfig(site_folder=site, source_type="other"))

    assert exc_info.value.code == ErrorCode.RESTORE_INVALID_SOURCE_TYPE


def test_missing_database_source_raises_restore_source_not_found(
    tmp_path: Path,
) -> None:
    """Database restore requires an existing database directory."""
    site = tmp_path / "site"
    make_site_with_mapping(site)

    with pytest.raises(RestoreSourceNotFoundError) as exc_info:
        Restorer().restore(RestoreConfig(site_folder=site, source_type="database"))

    assert exc_info.value.code == ErrorCode.RESTORE_SOURCE_NOT_FOUND


def test_missing_inference_source_raises_restore_source_not_found(
    tmp_path: Path,
) -> None:
    """Inference restore requires run_id or an existing explicit run directory."""
    site = tmp_path / "site"
    make_site_with_mapping(site)

    with pytest.raises(RestoreSourceNotFoundError):
        Restorer().restore(RestoreConfig(site_folder=site, source_type="inference"))

    with pytest.raises(RestoreSourceNotFoundError):
        Restorer().restore(
            RestoreConfig(
                site_folder=site, source_type="inference", run_id="run_missing"
            )
        )


def test_task_handle_progress_updates(tmp_path: Path) -> None:
    """Restore updates the injected task progress handle."""
    site = tmp_path / "site"
    database = tmp_path / "database"
    make_site_with_mapping(site)
    write_label(database / "labels" / "train" / "CodeA__Product1__a1.txt", "label\n")
    handle = make_task_handle()

    Restorer(task_handle=handle).restore(
        RestoreConfig(site_folder=site, source_type="database", database_dir=database)
    )

    assert handle.progress_current == 1
    assert handle.progress_total == 1
    assert handle.progress_message


def test_cancelled_task_raises_task_cancelled(tmp_path: Path) -> None:
    """Restore honors injected cancellation before copying labels."""
    site = tmp_path / "site"
    database = tmp_path / "database"
    make_site_with_mapping(site)
    write_label(database / "labels" / "train" / "CodeA__Product1__a1.txt", "label\n")
    handle = make_task_handle(cancelled=True)

    with pytest.raises(TaskCancelledError):
        Restorer(task_handle=handle).restore(
            RestoreConfig(
                site_folder=site, source_type="database", database_dir=database
            )
        )
