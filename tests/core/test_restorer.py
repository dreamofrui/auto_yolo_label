"""Tests for restoring labels back to source image folders."""

from __future__ import annotations

import xml.etree.ElementTree as ElementTree
from pathlib import Path

import pytest
from PIL import Image

from core.restorer import (
    IndependentRestoreConfig,
    RestoreConfig,
    RestoreInvalidSourceTypeError,
    RestoreMappingNotFoundError,
    RestoreSourceNotFoundError,
    Restorer,
)
from utils.exceptions import AutoLabelerError, ErrorCode, TaskCancelledError
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
        Image.new("RGB", (100, 100), color=(255, 0, 0)).save(image_path)
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


def write_classes(path: Path) -> None:
    """Write a minimal classes.txt file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("CodeA\n", encoding="utf-8")


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
    write_classes(database / "classes.txt")
    write_label(database / "labels" / "train" / "CodeA__Product1__a1.txt")
    write_label(database / "labels" / "val" / "CodeA__Product1__a2.txt")

    result = Restorer().restore(
        RestoreConfig(site_folder=site, source_type="database", database_dir=database)
    )

    assert result.total == 2
    assert result.success == 2
    assert result.skipped == 0
    assert result.failed == 0
    assert (site / "CodeA" / "Product1" / "a1.xml").read_text(
        encoding="utf-8"
    ).startswith("<annotation")
    assert (site / "CodeA" / "Product1" / "a2.xml").read_text(
        encoding="utf-8"
    ).startswith("<annotation")
    mapping = MappingManager(site / ".autolabeler" / "mapping.json").load()
    assert mapping.get_statistics()["restored_count"] == 2


def test_inference_restore_uses_run_labels_and_writes_xml(tmp_path: Path) -> None:
    """Flow inference restore reads run/labels and writes VOC XML beside images."""
    site = tmp_path / "site"
    make_site_with_mapping(site)
    run = site / ".autolabeler" / "inference_results" / "run_20260513_103000"
    write_classes(run / "classes.txt")
    write_label(run / "labels" / "CodeA" / "Product1" / "a1.txt")

    result = Restorer().restore(
        RestoreConfig(
            site_folder=site, source_type="inference", run_id="run_20260513_103000"
        )
    )

    assert result.success == 1
    assert (site / "CodeA" / "Product1" / "a1.xml").exists()
    assert not (site / "CodeA" / "Product1" / "a1.txt").exists()


def test_flow_restore_preflight_reports_impact_without_writing(tmp_path: Path) -> None:
    """Flow restore preflight reports write impact without creating XML files."""
    site = tmp_path / "site"
    make_site_with_mapping(site)
    mapping_path = site / ".autolabeler" / "mapping.json"
    mapping_before = mapping_path.read_text(encoding="utf-8")
    run = site / ".autolabeler" / "inference_results" / "run_20260513_103000"
    write_classes(run / "classes.txt")
    write_label(run / "labels" / "CodeA" / "Product1" / "a1.txt")

    result = Restorer().preflight(
        RestoreConfig(
            site_folder=site,
            source_type="inference",
            run_id="run_20260513_103000",
        )
    )

    assert result.can_execute is True
    assert result.mode == "flow-inference"
    assert result.total_labels == 1
    assert result.matched_images == 1
    assert result.xml_to_write == 1
    assert result.classes_path == run / "classes.txt"
    assert result.target_folders == [site / "CodeA" / "Product1"]
    assert not (site / "CodeA" / "Product1" / "a1.xml").exists()
    assert mapping_path.read_text(encoding="utf-8") == mapping_before


def test_flow_preflight_reports_invalid_yolo_box_diagnostics(tmp_path: Path) -> None:
    """Flow preflight exposes the same row-level diagnostics without writing."""
    site = tmp_path / "site"
    make_site_with_mapping(site)
    run = site / ".autolabeler" / "inference_results" / "run_20260513_103000"
    write_classes(run / "classes.txt")
    label_path = run / "labels" / "CodeA" / "Product1" / "a1.txt"
    write_label(label_path, "0 0.5 0.99 0.2 0.04\n")

    with pytest.raises(AutoLabelerError) as exc_info:
        Restorer().preflight(
            RestoreConfig(
                site_folder=site,
                source_type="inference",
                run_id="run_20260513_103000",
            )
        )

    error = exc_info.value
    assert error.details is not None
    assert f"label_file: {label_path}" in error.details
    assert "line: 1" in error.details
    assert "pixel_bounds: xmin=40 ymin=97 xmax=60 ymax=101" in error.details
    assert "violation: ymax=101 exceeds image_height=100" in error.details
    assert not (site / "CodeA" / "Product1" / "a1.xml").exists()


def test_independent_restore_preflight_reports_impact_without_writing(
    tmp_path: Path,
) -> None:
    """Independent restore preflight validates matching labels without writing XML."""
    image_root = tmp_path / "images"
    label_root = tmp_path / "labels"
    (image_root / "Product1").mkdir(parents=True)
    Image.new("RGB", (100, 100), color=(255, 0, 0)).save(
        image_root / "Product1" / "a.jpg"
    )
    write_classes(label_root / "classes.txt")
    write_label(label_root / "Product1" / "a.txt")

    result = Restorer().preflight_independent(
        IndependentRestoreConfig(image_root=image_root, label_root=label_root)
    )

    assert result.can_execute is True
    assert result.mode == "independent"
    assert result.total_labels == 1
    assert result.xml_to_write == 1
    assert result.classes_path == label_root / "classes.txt"
    assert result.target_folders == [image_root / "Product1"]
    assert not (image_root / "Product1" / "a.xml").exists()


def test_independent_preflight_reports_exact_invalid_yolo_box(
    tmp_path: Path,
) -> None:
    """Invalid pixel bounds identify the source row and violated image edge."""
    image_root = tmp_path / "images"
    label_root = tmp_path / "labels"
    image_path = image_root / "Product1" / "a.jpg"
    image_path.parent.mkdir(parents=True)
    Image.new("RGB", (100, 100), color=(255, 0, 0)).save(image_path)
    write_classes(label_root / "classes.txt")
    label_path = label_root / "Product1" / "a.txt"
    invalid_row = "0 0.5 0.99 0.2 0.04"
    write_label(label_path, f"0 0.5 0.5 0.2 0.2\n{invalid_row}\n")

    with pytest.raises(AutoLabelerError) as exc_info:
        Restorer().preflight_independent(
            IndependentRestoreConfig(image_root=image_root, label_root=label_root)
        )

    error = exc_info.value
    assert error.code == ErrorCode.VALIDATION_ERROR
    assert error.message == "Invalid YOLO box"
    assert error.details is not None
    assert f"label_file: {label_path}" in error.details
    assert "line: 2" in error.details
    assert f"raw_row: {invalid_row}" in error.details
    assert f"image_file: {image_path}" in error.details
    assert "image_size: 100x100" in error.details
    assert "class_id: 0" in error.details
    assert "class_name: CodeA" in error.details
    assert "normalized_box: x=0.5 y=0.99 w=0.2 h=0.04" in error.details
    assert "pixel_bounds: xmin=40 ymin=97 xmax=60 ymax=101" in error.details
    assert "violation: ymax=101 exceeds image_height=100" in error.details
    assert not (image_root / "Product1" / "a.xml").exists()


@pytest.mark.parametrize(
    ("invalid_row", "expected_violation"),
    (
        ("0 0.5 nan 0.2 0.2", "violation: y=nan is not finite"),
        ("0 0.5 1e308 0.2 0.2", "violation: y=1e+308 exceeds 1"),
        ("0 1.1 0.5 0.2 0.2", "violation: x=1.1 exceeds 1"),
        (
            "0 0.5 0.5 -0.2 0.2",
            "violation: w=-0.2 must be greater than 0",
        ),
    ),
)
def test_independent_preflight_reports_invalid_yolo_geometry(
    tmp_path: Path, invalid_row: str, expected_violation: str
) -> None:
    """Diagnostic formatting preserves invalid geometry validation errors."""
    image_root = tmp_path / "images"
    label_root = tmp_path / "labels"
    image_path = image_root / "Product1" / "a.jpg"
    image_path.parent.mkdir(parents=True)
    Image.new("RGB", (100, 100), color=(255, 0, 0)).save(image_path)
    write_classes(label_root / "classes.txt")
    label_path = label_root / "Product1" / "a.txt"
    write_label(label_path, f"{invalid_row}\n")

    with pytest.raises(AutoLabelerError) as exc_info:
        Restorer().preflight_independent(
            IndependentRestoreConfig(image_root=image_root, label_root=label_root)
        )

    error = exc_info.value
    assert error.message == "Invalid YOLO geometry"
    assert error.details is not None
    assert f"label_file: {label_path}" in error.details
    assert "line: 1" in error.details
    assert f"raw_row: {invalid_row}" in error.details
    assert expected_violation in error.details
    assert "validation_detail: line 1" in error.details


def test_independent_restore_uses_explicit_classes_file(
    tmp_path: Path,
) -> None:
    """Independent restore can use a selected classes.txt outside label_root."""
    image_root = tmp_path / "images"
    label_root = tmp_path / "labels"
    classes_file = tmp_path / "metadata" / "classes.txt"
    (image_root / "Product1").mkdir(parents=True)
    Image.new("RGB", (100, 100), color=(255, 0, 0)).save(
        image_root / "Product1" / "a.jpg"
    )
    write_classes(classes_file)
    write_label(label_root / "Product1" / "a.txt")

    config = IndependentRestoreConfig(
        image_root=image_root,
        label_root=label_root,
        classes_file=classes_file,
    )

    preflight = Restorer().preflight_independent(config)
    result = Restorer().restore_independent(config)

    assert preflight.classes_path == classes_file
    assert result.success == 1
    assert (image_root / "Product1" / "a.xml").exists()


def test_independent_restore_does_not_fallback_when_explicit_classes_is_empty(
    tmp_path: Path,
) -> None:
    """A selected empty classes.txt blocks instead of falling back silently."""
    image_root = tmp_path / "images"
    label_root = tmp_path / "labels"
    classes_file = tmp_path / "metadata" / "classes.txt"
    (image_root / "Product1").mkdir(parents=True)
    Image.new("RGB", (100, 100), color=(255, 0, 0)).save(
        image_root / "Product1" / "a.jpg"
    )
    write_classes(label_root / "classes.txt")
    classes_file.parent.mkdir(parents=True)
    classes_file.write_text("", encoding="utf-8")
    write_label(label_root / "Product1" / "a.txt")

    with pytest.raises(RestoreSourceNotFoundError) as exc_info:
        Restorer().preflight_independent(
            IndependentRestoreConfig(
                image_root=image_root,
                label_root=label_root,
                classes_file=classes_file,
            )
        )

    assert exc_info.value.details == str(classes_file)


def test_independent_restore_matches_label_and_image_relative_paths(
    tmp_path: Path,
) -> None:
    """Independent restore needs no mapping and writes XML beside matching images."""
    image_root = tmp_path / "images"
    label_root = tmp_path / "labels"
    (image_root / "Product1").mkdir(parents=True)
    Image.new("RGB", (100, 100), color=(255, 0, 0)).save(
        image_root / "Product1" / "a.jpg"
    )
    write_classes(label_root / "classes.txt")
    write_label(label_root / "Product1" / "a.txt")

    result = Restorer().restore_independent(
        IndependentRestoreConfig(
            image_root=image_root,
            label_root=label_root,
        )
    )

    assert result.success == 1
    assert (image_root / "Product1" / "a.xml").exists()


def test_independent_restore_writes_labelimg_style_pretty_voc_xml(
    tmp_path: Path,
) -> None:
    """Restored XML includes folder/path metadata and is readable in Notepad."""
    image_root = tmp_path / "images"
    label_root = tmp_path / "labels"
    (image_root / "Product1").mkdir(parents=True)
    Image.new("RGB", (100, 100), color=(255, 0, 0)).save(
        image_root / "Product1" / "a.jpg"
    )
    write_classes(label_root / "classes.txt")
    write_label(label_root / "Product1" / "a.txt")

    Restorer().restore_independent(
        IndependentRestoreConfig(image_root=image_root, label_root=label_root)
    )

    xml_path = image_root / "Product1" / "a.xml"
    xml_text = xml_path.read_text(encoding="utf-8")
    root = ElementTree.fromstring(xml_text)

    assert root.findtext("folder") == "Product1"
    assert root.findtext("filename") == "a.jpg"
    assert root.findtext("path") == str(image_root / "Product1" / "a.jpg")
    assert root.findtext("source/database") == "Unknown"
    assert "\n  <folder>" in xml_text
    assert "\n  <object>" in xml_text


def test_independent_restore_blocks_ambiguous_same_stem_images(
    tmp_path: Path,
) -> None:
    """Independent restore rejects multiple same-relative image candidates."""
    image_root = tmp_path / "images"
    label_root = tmp_path / "labels"
    (image_root / "Product1").mkdir(parents=True)
    Image.new("RGB", (100, 100), color=(255, 0, 0)).save(
        image_root / "Product1" / "a.jpg"
    )
    Image.new("RGB", (100, 100), color=(0, 255, 0)).save(
        image_root / "Product1" / "a.png"
    )
    write_classes(label_root / "classes.txt")
    write_label(label_root / "Product1" / "a.txt")

    with pytest.raises(RestoreSourceNotFoundError):
        Restorer().restore_independent(
            IndependentRestoreConfig(image_root=image_root, label_root=label_root)
        )

    assert not (image_root / "Product1" / "a.xml").exists()


def test_flow_restore_blocks_ambiguous_same_stem_images(tmp_path: Path) -> None:
    """Flow restore rejects multiple same-stem images beside the target XML."""
    site = tmp_path / "site"
    database = tmp_path / "database"
    make_site_with_mapping(site)
    Image.new("RGB", (100, 100), color=(0, 255, 0)).save(
        site / "CodeA" / "Product1" / "a1.png"
    )
    write_classes(database / "classes.txt")
    write_label(database / "labels" / "train" / "CodeA__Product1__a1.txt")

    with pytest.raises(RestoreSourceNotFoundError):
        Restorer().restore(
            RestoreConfig(site_folder=site, source_type="database", database_dir=database)
        )

    assert not (site / "CodeA" / "Product1" / "a1.xml").exists()


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
        / "labels"
        / "CodeA"
        / "Product1"
        / "a1.txt",
    )
    write_classes(
        site
        / ".autolabeler"
        / "inference_results"
        / "run_20260513_103000"
        / "classes.txt"
    )

    result = Restorer().restore(
        RestoreConfig(
            site_folder=site, source_type="inference", run_id="run_20260513_103000"
        )
    )

    assert result.success == 1
    assert (site / "CodeA" / "Product1" / "a1.xml").exists()


def test_inference_restore_by_explicit_run_dir(tmp_path: Path) -> None:
    """Inference restore can use an explicit run directory independent of run_id."""
    site = tmp_path / "site"
    run_dir = tmp_path / "runs" / "run_custom"
    make_site_with_mapping(site)
    write_classes(run_dir / "classes.txt")
    write_label(run_dir / "labels" / "CodeA" / "Product1" / "a2.txt")

    result = Restorer().restore(
        RestoreConfig(
            site_folder=site, source_type="inference", inference_run_dir=run_dir
        )
    )

    assert result.total == 1
    assert result.success == 1
    assert (site / "CodeA" / "Product1" / "a2.xml").exists()


def test_restore_blocks_existing_target_when_overwrite_false(tmp_path: Path) -> None:
    """Existing XML blocks restore unless overwrite is enabled."""
    site = tmp_path / "site"
    database = tmp_path / "database"
    make_site_with_mapping(site)
    write_classes(database / "classes.txt")
    write_label(database / "labels" / "train" / "CodeA__Product1__a1.txt")
    (site / "CodeA" / "Product1" / "a1.xml").write_text("old\n", encoding="utf-8")

    with pytest.raises(RestoreSourceNotFoundError):
        Restorer().restore(
            RestoreConfig(site_folder=site, source_type="database", database_dir=database)
        )

    assert (site / "CodeA" / "Product1" / "a1.xml").read_text(
        encoding="utf-8"
    ) == "old\n"


def test_restore_overwrites_existing_target_when_overwrite_true(tmp_path: Path) -> None:
    """overwrite=True replaces existing target label files."""
    site = tmp_path / "site"
    database = tmp_path / "database"
    make_site_with_mapping(site)
    write_classes(database / "classes.txt")
    write_label(database / "labels" / "train" / "CodeA__Product1__a1.txt")
    (site / "CodeA" / "Product1" / "a1.xml").write_text("old\n", encoding="utf-8")

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
    assert (site / "CodeA" / "Product1" / "a1.xml").read_text(
        encoding="utf-8"
    ).startswith("<annotation")


def test_restore_rolls_back_xml_written_before_later_write_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Restore removes XML written by the same run if a later write fails."""
    site = tmp_path / "site"
    database = tmp_path / "database"
    make_site_with_mapping(site)
    write_classes(database / "classes.txt")
    write_label(database / "labels" / "train" / "CodeA__Product1__a1.txt")
    write_label(database / "labels" / "train" / "CodeA__Product1__a2.txt")
    from core import restorer as restorer_module

    original_write = restorer_module._write_xml_text
    calls = 0

    def flaky_write(target_path: Path, xml_text: str) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise restorer_module.RestoreSourceNotFoundError(
                "Restored XML cannot be written", details=str(target_path)
            )
        original_write(target_path, xml_text)

    monkeypatch.setattr(restorer_module, "_write_xml_text", flaky_write)

    with pytest.raises(RestoreSourceNotFoundError):
        Restorer().restore(
            RestoreConfig(site_folder=site, source_type="database", database_dir=database)
        )

    assert not (site / "CodeA" / "Product1" / "a1.xml").exists()
    assert not (site / "CodeA" / "Product1" / "a2.xml").exists()
    mapping = MappingManager(site / ".autolabeler" / "mapping.json").load()
    assert mapping.get_statistics()["restored_count"] == 0


def test_restore_does_not_skip_restored_mapping_entry_without_xml(
    tmp_path: Path,
) -> None:
    """Mapping restored state does not replace XML target preflight."""
    site = tmp_path / "site"
    database = tmp_path / "database"
    manager = make_site_with_mapping(site)
    manager.mark_restored("CodeA__Product1__a1.jpg")
    manager.save()
    write_classes(database / "classes.txt")
    write_label(database / "labels" / "train" / "CodeA__Product1__a1.txt")

    result = Restorer().restore(
        RestoreConfig(site_folder=site, source_type="database", database_dir=database)
    )

    assert result.success == 1
    assert (site / "CodeA" / "Product1" / "a1.xml").exists()


def test_restore_filters_control_files(tmp_path: Path) -> None:
    """Control TXT files are not treated as labels."""
    site = tmp_path / "site"
    database = tmp_path / "database"
    make_site_with_mapping(site)
    write_classes(database / "classes.txt")
    write_label(database / "labels" / "train" / "CodeA__Product1__a1.txt")
    write_label(database / "labels" / "train" / "classes.txt", "CodeA\n")
    write_label(database / "labels" / "train" / "data.yaml", "path: .\n")
    write_label(database / "labels" / "train" / "README.txt", "notes\n")

    result = Restorer().restore(
        RestoreConfig(site_folder=site, source_type="database", database_dir=database)
    )

    assert result.total == 1
    assert result.success == 1
    assert not (site / "CodeA" / "Product1" / "classes.xml").exists()


def test_database_unknown_encoded_label_blocks_before_writing(
    tmp_path: Path,
) -> None:
    """Unknown database labels fail preflight and do not write later XML."""
    site = tmp_path / "site"
    database = tmp_path / "database"
    make_site_with_mapping(site)
    write_classes(database / "classes.txt")
    write_label(database / "labels" / "train" / "CodeA__Product1__missing.txt")
    write_label(database / "labels" / "train" / "CodeA__Product1__a1.txt")

    with pytest.raises(RestoreSourceNotFoundError):
        Restorer().restore(
            RestoreConfig(site_folder=site, source_type="database", database_dir=database)
        )

    assert not (site / "CodeA" / "Product1" / "a1.xml").exists()


def test_inference_unknown_relative_label_blocks_before_writing(
    tmp_path: Path,
) -> None:
    """Inference labels with no matching mapping image fail preflight."""
    site = tmp_path / "site"
    make_site_with_mapping(site)
    run = site / ".autolabeler" / "inference_results" / "run_20260513_103000"
    write_classes(run / "classes.txt")
    write_label(run / "labels" / "CodeA" / "Product1" / "missing.txt")
    write_label(run / "labels" / "CodeA" / "Product1" / "a2.txt")

    with pytest.raises(RestoreSourceNotFoundError):
        Restorer().restore(
            RestoreConfig(
                site_folder=site, source_type="inference", run_id="run_20260513_103000"
            )
        )

    assert not (site / "CodeA" / "Product1" / "a2.xml").exists()


def test_invalid_label_blocks_before_writing(
    tmp_path: Path,
) -> None:
    """Invalid labels fail preflight and do not write later XML."""
    site = tmp_path / "site"
    database = tmp_path / "database"
    make_site_with_mapping(site)
    write_classes(database / "classes.txt")
    write_label(database / "labels" / "train" / "CodeA__Product1__a1.txt", "bad\n")
    write_label(database / "labels" / "train" / "CodeA__Product1__a2.txt")

    with pytest.raises(AutoLabelerError):
        Restorer().restore(
            RestoreConfig(site_folder=site, source_type="database", database_dir=database)
        )

    assert not (site / "CodeA" / "Product1" / "a2.xml").exists()


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
    write_classes(database / "classes.txt")
    write_label(database / "labels" / "train" / "CodeA__Product1__a1.txt")
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
    write_classes(database / "classes.txt")
    write_label(database / "labels" / "train" / "CodeA__Product1__a1.txt", "label\n")
    handle = make_task_handle(cancelled=True)

    with pytest.raises(TaskCancelledError):
        Restorer(task_handle=handle).restore(
            RestoreConfig(
                site_folder=site, source_type="database", database_dir=database
            )
        )
