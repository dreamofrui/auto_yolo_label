"""Tests for the sampling core module."""

from __future__ import annotations

from pathlib import Path

import pytest

from core.sampler import (
    IndependentSampleConfig,
    SampleConfig,
    SampleInvalidConfigError,
    SampleMappingNotFoundError,
    SamplePreflightIssue,
    SampleXmlConvertError,
    Sampler,
)
from utils.exceptions import TaskCancelledError
from utils.mapping_manager import ImageInfo, MappingManager
from utils.path_encoder import PathEncoder
from utils.task_registry import TaskHandle


def make_task_handle(is_cancel_requested: bool = False) -> TaskHandle:
    """Create an in-memory task handle for sampler tests."""
    return TaskHandle(
        task_id="task_sample_test",
        task_type="sample",
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
        is_cancel_requested=is_cancel_requested,
    )


def make_site_with_mapping(
    site: Path, layout: dict[str, dict[str, list[str]]]
) -> MappingManager:
    """Create placeholder images and a mapping.json for sampler tests."""
    encoder = PathEncoder()
    manager = MappingManager(site / ".autolabeler" / "mapping.json").create_new(site)
    for class_id, code in enumerate(sorted(layout)):
        manager.add_class(class_id, code)
        for product, names in layout[code].items():
            for name in names:
                image_path = site / code / product / name
                image_path.parent.mkdir(parents=True, exist_ok=True)
                image_path.write_bytes(b"image")
                encoded_name = encoder.encode(code, product, name)
                manager.add_image(
                    encoded_name,
                    ImageInfo(
                        original_relative=image_path.relative_to(site).as_posix(),
                        code=code,
                        product=product,
                        original_name=name,
                        format=image_path.suffix.lower(),
                    ),
                )
    manager.save()
    return manager


def write_xml(path: Path, class_name: str) -> None:
    """Write a minimal VOC XML label."""
    path.write_text(
        (
            "<annotation>"
            "<size><width>100</width><height>50</height></size>"
            f"<object><name>{class_name}</name>"
            "<bndbox><xmin>10</xmin><ymin>5</ymin><xmax>30</xmax><ymax>25</ymax></bndbox>"
            "</object>"
            "</annotation>"
        ),
        encoding="utf-8",
    )


def test_sampler_constructs_successfully() -> None:
    """Sampler can be constructed with default dependencies."""
    sampler = Sampler()

    assert isinstance(sampler, Sampler)


def test_sample_count_mode_creates_dataset_and_updates_mapping(tmp_path: Path) -> None:
    """Count mode samples images into YOLO folders and marks mapping state."""
    site = tmp_path / "site"
    output_dir = tmp_path / "database"
    make_site_with_mapping(
        site,
        {
            "CodeA": {"Product1": ["a1.jpg", "a2.jpg"], "Product2": ["a3.jpg"]},
            "CodeB": {"Product1": ["b1.jpg", "b2.jpg"]},
        },
    )
    (site / "CodeA" / "Product1" / "a1.txt").write_text(
        "0 0.5 0.5 0.2 0.2\n", encoding="utf-8"
    )
    write_xml(site / "CodeB" / "Product1" / "b1.xml", "CodeB")

    result = Sampler().sample(
        SampleConfig(site_folder=site, output_dir=output_dir, count=1, full_threshold=1)
    )

    assert result.dataset_dir == output_dir
    assert result.data_yaml == output_dir / "data.yaml"
    assert result.paths.images_train.exists()
    assert result.paths.images_val.exists()
    assert result.paths.labels_train.exists()
    assert result.paths.labels_val.exists()
    assert result.statistics.total_products == 3
    assert result.statistics.sampled_count == 3
    assert result.statistics.train_count == 3
    assert result.statistics.val_count == 0
    assert result.statistics.pre_labeled_count == 2

    yaml_text = result.data_yaml.read_text(encoding="utf-8")
    assert "train: images/train" in yaml_text
    assert "val: images/val" in yaml_text
    assert "vals" not in yaml_text
    assert "names: ['CodeA', 'CodeB']" in yaml_text
    assert (output_dir / "classes.txt").read_text(encoding="utf-8") == "CodeA\nCodeB\n"

    copied_images = sorted(path.name for path in (output_dir / "images").rglob("*.jpg"))
    assert copied_images == [
        "CodeA__Product1__a1.jpg",
        "CodeA__Product2__a3.jpg",
        "CodeB__Product1__b1.jpg",
    ]
    copied_labels = sorted(path.name for path in (output_dir / "labels").rglob("*.txt"))
    assert copied_labels == ["CodeA__Product1__a1.txt", "CodeB__Product1__b1.txt"]

    mapping = MappingManager(result.mapping_path).load()
    sampled = mapping.get_sampled_images()
    assert len(sampled) == 3
    assert {image.info.split for image in sampled} == {"train"}
    assert mapping.get_image_info("CodeA__Product1__a1.jpg")
    assert mapping.data.config["sample_mode"] == "count"
    assert mapping.get_statistics()["sample_pre_labeled_count"] == 2


def test_flow_sampling_splits_each_code_product_group(tmp_path: Path) -> None:
    """Train/val split is calculated inside each Code/Product group."""
    site = tmp_path / "site"
    output_dir = tmp_path / "database"
    make_site_with_mapping(
        site,
        {
            "CodeA": {
                "Product1": ["a1.jpg", "a2.jpg"],
                "Product2": ["a3.jpg", "a4.jpg"],
            }
        },
    )

    result = Sampler().sample(
        SampleConfig(
            site_folder=site,
            output_dir=output_dir,
            count=2,
            full_threshold=1,
            train_ratio=0.5,
        )
    )

    train_images = sorted(path.name for path in result.paths.images_train.glob("*.jpg"))
    val_images = sorted(path.name for path in result.paths.images_val.glob("*.jpg"))
    assert train_images == ["CodeA__Product1__a1.jpg", "CodeA__Product2__a3.jpg"]
    assert val_images == ["CodeA__Product1__a2.jpg", "CodeA__Product2__a4.jpg"]


def test_flow_sampling_keeps_pre_labeled_images_over_target(tmp_path: Path) -> None:
    """Already labeled images are kept even when they exceed the target count."""
    site = tmp_path / "site"
    output_dir = tmp_path / "database"
    make_site_with_mapping(
        site,
        {
            "CodeA": {
                "Product1": ["a1.jpg", "a2.jpg", "a3.jpg"],
            }
        },
    )
    for name in ("a1.txt", "a2.txt"):
        (site / "CodeA" / "Product1" / name).write_text(
            "0 0.5 0.5 0.2 0.2\n", encoding="utf-8"
        )

    result = Sampler().sample(
        SampleConfig(site_folder=site, output_dir=output_dir, count=1, full_threshold=1)
    )

    copied_images = sorted(path.name for path in (output_dir / "images").rglob("*.jpg"))
    assert copied_images == ["CodeA__Product1__a1.jpg", "CodeA__Product1__a2.jpg"]
    assert result.statistics.pre_labeled_count == 2


def test_flow_sampling_txt_wins_when_txt_and_xml_exist(tmp_path: Path) -> None:
    """Non-empty TXT labels take precedence over same-stem XML labels."""
    site = tmp_path / "site"
    output_dir = tmp_path / "database"
    make_site_with_mapping(site, {"CodeA": {"Product1": ["a1.jpg"]}})
    (site / "CodeA" / "Product1" / "a1.txt").write_text(
        "0 0.1 0.2 0.3 0.4\n", encoding="utf-8"
    )
    write_xml(site / "CodeA" / "Product1" / "a1.xml", "CodeA")

    result = Sampler().sample(
        SampleConfig(site_folder=site, output_dir=output_dir, count=1, full_threshold=1)
    )

    label_text = (result.paths.labels_train / "CodeA__Product1__a1.txt").read_text(
        encoding="utf-8"
    )
    assert label_text == "0 0.1 0.2 0.3 0.4\n"


def test_sampling_refuses_non_empty_output_by_default(tmp_path: Path) -> None:
    """Sampling refuses to merge into non-empty output unless explicitly confirmed."""
    site = tmp_path / "site"
    output_dir = tmp_path / "database"
    make_site_with_mapping(site, {"CodeA": {"Product1": ["a1.jpg"]}})
    output_dir.mkdir()
    (output_dir / "old.txt").write_text("keep", encoding="utf-8")

    with pytest.raises(SampleInvalidConfigError):
        Sampler().sample(
            SampleConfig(site_folder=site, output_dir=output_dir, count=1)
        )
    assert (output_dir / "old.txt").read_text(encoding="utf-8") == "keep"


def test_flow_preflight_reports_estimate_without_writing_output(
    tmp_path: Path,
) -> None:
    """Flow preflight returns estimated counts and does not create the dataset."""
    site = tmp_path / "site"
    output_dir = tmp_path / "database"
    make_site_with_mapping(site, {"CodeA": {"Product1": ["a1.jpg", "a2.jpg"]}})

    result = Sampler().preflight(
        SampleConfig(
            site_folder=site,
            output_dir=output_dir,
            count=2,
            full_threshold=1,
            train_ratio=0.5,
        )
    )

    assert result.can_execute is True
    assert result.mode == "flow"
    assert result.statistics.sampled_count == 2
    assert result.statistics.train_count == 1
    assert result.statistics.val_count == 1
    assert result.total_groups == 1
    assert result.copy_count == 2
    assert result.move_count == 0
    assert result.issues == []
    assert not output_dir.exists()


def test_flow_preflight_reports_non_empty_output_blocker(tmp_path: Path) -> None:
    """Flow preflight reports non-empty output without deleting existing files."""
    site = tmp_path / "site"
    output_dir = tmp_path / "database"
    make_site_with_mapping(site, {"CodeA": {"Product1": ["a1.jpg"]}})
    output_dir.mkdir()
    (output_dir / "old.txt").write_text("keep", encoding="utf-8")

    result = Sampler().preflight(
        SampleConfig(site_folder=site, output_dir=output_dir, count=1)
    )

    assert result.can_execute is False
    assert SamplePreflightIssue(
        severity="blocker",
        code="OUTPUT_NOT_EMPTY",
        message="output directory is not empty",
        detail=str(output_dir),
    ) in result.issues
    assert (output_dir / "old.txt").read_text(encoding="utf-8") == "keep"


def test_independent_sampling_moves_selected_files_without_mapping(
    tmp_path: Path,
) -> None:
    """Independent YOLO sampling keeps the existing move-to-dataset behavior."""
    source = tmp_path / "source"
    output_dir = tmp_path / "database"
    for name in ("a1.jpg", "a2.jpg", "a3.jpg"):
        (source / "Product1").mkdir(parents=True, exist_ok=True)
        (source / "Product1" / name).write_bytes(b"image")
    (source / "Product1" / "a1.txt").write_text(
        "0 0.5 0.5 0.2 0.2\n", encoding="utf-8"
    )

    result = Sampler().sample_independent(
        IndependentSampleConfig(
            source_dir=source,
            output_dir=output_dir,
            output_format="yolo",
            count=2,
            full_threshold=1,
            train_ratio=0.5,
        )
    )

    assert result.mapping_path is None
    assert result.statistics.sampled_count == 2
    assert sorted(path.name for path in result.paths.images_train.glob("*.jpg")) == [
        "a1.jpg"
    ]
    assert sorted(path.name for path in result.paths.images_val.glob("*.jpg")) == [
        "a2.jpg"
    ]
    assert (result.paths.labels_train / "a1.txt").exists()
    assert not (source / "Product1" / "a1.jpg").exists()
    assert not (source / "Product1" / "a1.txt").exists()
    assert (source / "Product1" / "a3.jpg").exists()
    assert not (source / ".autolabeler" / "mapping.json").exists()
    assert (output_dir / "classes.txt").read_text(encoding="utf-8") == ""


def test_independent_sampling_defaults_to_flat_xml_labeling_output(
    tmp_path: Path,
) -> None:
    """Independent XML sampling preserves source folder structure for labeling."""
    source = tmp_path / "source"
    output_dir = tmp_path / "labeling_sample"
    for folder, name in (
        ("CodeA/Product1", "a1.jpg"),
        ("CodeA/Product1", "a2.jpg"),
        ("CodeB/Product2", "b1.jpg"),
    ):
        image = source / folder / name
        image.parent.mkdir(parents=True, exist_ok=True)
        image.write_bytes(b"image")
    write_xml(source / "CodeA" / "Product1" / "a1.xml", "CodeA")

    result = Sampler().sample_independent(
        IndependentSampleConfig(
            source_dir=source,
            output_dir=output_dir,
            count=1,
            full_threshold=1,
            train_ratio=0.5,
        )
    )

    assert result.mapping_path is None
    assert result.output_format == "xml"
    assert result.statistics.sampled_count == 2
    assert sorted(path.relative_to(output_dir).as_posix() for path in output_dir.rglob("*") if path.is_file()) == [
        "CodeA/Product1/a1.jpg",
        "CodeA/Product1/a1.xml",
        "CodeB/Product2/b1.jpg",
    ]
    assert not (output_dir / "images").exists()
    assert not (output_dir / "labels").exists()
    assert not (output_dir / "classes.txt").exists()
    assert not (output_dir / "data.yaml").exists()
    assert not (source / "CodeA" / "Product1" / "a1.jpg").exists()
    assert not (source / "CodeA" / "Product1" / "a1.xml").exists()
    assert (source / "CodeA" / "Product1" / "a2.jpg").exists()
    assert not (source / ".autolabeler" / "mapping.json").exists()


def test_independent_xml_sampling_allows_same_names_in_different_folders(
    tmp_path: Path,
) -> None:
    """Independent XML output detects conflicts by relative path, not basename."""
    source = tmp_path / "source"
    output_dir = tmp_path / "labeling_sample"
    for folder in ("left", "right"):
        image = source / folder / "same.jpg"
        image.parent.mkdir(parents=True, exist_ok=True)
        image.write_bytes(b"image")

    result = Sampler().sample_independent(
        IndependentSampleConfig(
            source_dir=source,
            output_dir=output_dir,
            count=1,
            full_threshold=1,
        )
    )

    assert result.output_format == "xml"
    assert sorted(path.relative_to(output_dir).as_posix() for path in output_dir.rglob("*.jpg")) == [
        "left/same.jpg",
        "right/same.jpg",
    ]


def test_independent_xml_sampling_does_not_keep_txt_labels_over_target(
    tmp_path: Path,
) -> None:
    """Independent XML output only treats XML labels as reusable labels."""
    source = tmp_path / "source"
    output_dir = tmp_path / "labeling_sample"
    for name in ("a1.jpg", "a2.jpg", "a3.jpg"):
        image = source / "Product1" / name
        image.parent.mkdir(parents=True, exist_ok=True)
        image.write_bytes(b"image")
    (source / "Product1" / "a1.txt").write_text(
        "0 0.5 0.5 0.2 0.2\n", encoding="utf-8"
    )

    result = Sampler().sample_independent(
        IndependentSampleConfig(
            source_dir=source,
            output_dir=output_dir,
            count=1,
            full_threshold=1,
        )
    )

    assert result.output_format == "xml"
    assert result.statistics.sampled_count == 1
    assert result.statistics.pre_labeled_count == 0
    assert sorted(path.relative_to(output_dir).as_posix() for path in output_dir.rglob("*") if path.is_file()) == [
        "Product1/a1.jpg"
    ]
    assert (source / "Product1" / "a1.txt").exists()


def test_independent_preflight_reports_move_count_without_moving_files(
    tmp_path: Path,
) -> None:
    """Independent XML preflight reports move count without touching sources."""
    source = tmp_path / "source"
    output_dir = tmp_path / "database"
    for name in ("a1.jpg", "a2.jpg", "a3.jpg"):
        image = source / "Product1" / name
        image.parent.mkdir(parents=True, exist_ok=True)
        image.write_bytes(b"image")

    result = Sampler().preflight_independent(
        IndependentSampleConfig(
            source_dir=source,
            output_dir=output_dir,
            count=2,
            full_threshold=1,
            train_ratio=0.5,
        )
    )

    assert result.can_execute is True
    assert result.mode == "independent"
    assert result.statistics.sampled_count == 2
    assert result.statistics.train_count == 1
    assert result.statistics.val_count == 1
    assert result.copy_count == 0
    assert result.move_count == 2
    assert result.output_format == "xml"
    assert result.issues == []
    assert (source / "Product1" / "a1.jpg").exists()
    assert not output_dir.exists()


def test_independent_yolo_preflight_reports_empty_classes_warning(
    tmp_path: Path,
) -> None:
    """Independent YOLO preflight reports the empty classes metadata warning."""
    source = tmp_path / "source"
    output_dir = tmp_path / "database"
    for name in ("a1.jpg", "a2.jpg"):
        image = source / "Product1" / name
        image.parent.mkdir(parents=True, exist_ok=True)
        image.write_bytes(b"image")

    result = Sampler().preflight_independent(
        IndependentSampleConfig(
            source_dir=source,
            output_dir=output_dir,
            output_format="yolo",
            count=2,
            full_threshold=1,
            train_ratio=0.5,
        )
    )

    assert result.output_format == "yolo"
    assert result.issues == [
        SamplePreflightIssue(
            severity="warning",
            code="EMPTY_CLASSES",
            message="classes.txt will be empty until the user fills classes",
            detail=str(output_dir / "classes.txt"),
        )
    ]
    assert (source / "Product1" / "a1.jpg").exists()
    assert not output_dir.exists()


def test_independent_sampling_blocks_ambiguous_nested_image_folders(
    tmp_path: Path,
) -> None:
    """Parent and child folders containing images are ambiguous and block sampling."""
    source = tmp_path / "source"
    (source / "root.jpg").parent.mkdir(parents=True, exist_ok=True)
    (source / "root.jpg").write_bytes(b"image")
    (source / "nested" / "child.jpg").parent.mkdir(parents=True, exist_ok=True)
    (source / "nested" / "child.jpg").write_bytes(b"image")

    with pytest.raises(SampleInvalidConfigError):
        Sampler().sample_independent(
            IndependentSampleConfig(source_dir=source, output_dir=tmp_path / "database")
        )
    assert not (tmp_path / "database").exists()
    assert (source / "root.jpg").exists()
    assert (source / "nested" / "child.jpg").exists()


def test_independent_sampling_blocks_filename_conflicts_before_move(
    tmp_path: Path,
) -> None:
    """Independent YOLO output conflicts block before any source file moves."""
    source = tmp_path / "source"
    for folder in ("left", "right"):
        image = source / folder / "same.jpg"
        image.parent.mkdir(parents=True, exist_ok=True)
        image.write_bytes(b"image")

    with pytest.raises(SampleInvalidConfigError):
        Sampler().sample_independent(
            IndependentSampleConfig(
                source_dir=source,
                output_dir=tmp_path / "database",
                output_format="yolo",
                count=1,
                full_threshold=1,
            )
        )
    assert not (tmp_path / "database").exists()
    assert (source / "left" / "same.jpg").exists()
    assert (source / "right" / "same.jpg").exists()


def test_ratio_and_mixed_modes_calculate_sample_counts(tmp_path: Path) -> None:
    """Ratio and mixed modes follow the documented count rules."""
    site = tmp_path / "site"
    make_site_with_mapping(
        site, {"CodeA": {"Product1": [f"a{i}.jpg" for i in range(10)]}}
    )

    ratio_result = Sampler().sample(
        SampleConfig(
            site_folder=site,
            output_dir=tmp_path / "ratio",
            mode="ratio",
            ratio=0.3,
            full_threshold=2,
        )
    )
    assert ratio_result.statistics.sampled_count == 3

    # Reset mapping to unsampled images for the mixed assertion.
    make_site_with_mapping(
        site, {"CodeA": {"Product1": [f"a{i}.jpg" for i in range(10)]}}
    )
    mixed_result = Sampler().sample(
        SampleConfig(
            site_folder=site,
            output_dir=tmp_path / "mixed",
            mode="mixed",
            ratio=0.8,
            min_count=2,
            max_count=5,
            full_threshold=2,
        )
    )
    assert mixed_result.statistics.sampled_count == 5


def test_missing_mapping_raises_sample_mapping_not_found(tmp_path: Path) -> None:
    """Sampler does not call Scanner when mapping.json is missing."""
    site = tmp_path / "site"
    site.mkdir()

    with pytest.raises(SampleMappingNotFoundError):
        Sampler().sample(
            SampleConfig(site_folder=site, output_dir=tmp_path / "database")
        )


def test_invalid_config_raises_sample_invalid_config(tmp_path: Path) -> None:
    """Invalid sampling configuration values are rejected."""
    site = tmp_path / "site"
    make_site_with_mapping(site, {"CodeA": {"Product1": ["a1.jpg"]}})

    with pytest.raises(SampleInvalidConfigError):
        Sampler().sample(
            SampleConfig(site_folder=site, output_dir=tmp_path / "database", ratio=1.5)
        )


def test_xml_unknown_class_raises_sample_xml_convert(tmp_path: Path) -> None:
    """XML labels with classes outside mapping classes fail with sampler XML errors."""
    site = tmp_path / "site"
    make_site_with_mapping(site, {"CodeA": {"Product1": ["a1.jpg"]}})
    write_xml(site / "CodeA" / "Product1" / "a1.xml", "OtherCode")

    with pytest.raises(SampleXmlConvertError):
        Sampler().sample(
            SampleConfig(site_folder=site, output_dir=tmp_path / "database")
        )


def test_cancelled_task_raises_task_cancelled(tmp_path: Path) -> None:
    """Sampler honors injected task cancellation before copying files."""
    site = tmp_path / "site"
    make_site_with_mapping(site, {"CodeA": {"Product1": ["a1.jpg"]}})
    handle = make_task_handle(is_cancel_requested=True)

    with pytest.raises(TaskCancelledError):
        Sampler(task_handle=handle).sample(
            SampleConfig(site_folder=site, output_dir=tmp_path / "database")
        )
