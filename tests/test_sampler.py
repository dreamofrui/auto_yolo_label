"""Tests for the sampling core module."""

from __future__ import annotations

from pathlib import Path

import pytest

from core.sampler import (
    SampleConfig,
    SampleInvalidConfigError,
    SampleMappingNotFoundError,
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


def make_site_with_mapping(site: Path, layout: dict[str, dict[str, list[str]]]) -> MappingManager:
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
    (site / "CodeA" / "Product1" / "a1.txt").write_text("0 0.5 0.5 0.2 0.2\n", encoding="utf-8")
    write_xml(site / "CodeB" / "Product1" / "b1.xml", "CodeB")

    result = Sampler().sample(SampleConfig(site_folder=site, output_dir=output_dir, count=1, full_threshold=1))

    assert result.dataset_dir == output_dir
    assert result.data_yaml == output_dir / "data.yaml"
    assert result.paths.images_train.exists()
    assert result.paths.images_val.exists()
    assert result.paths.labels_train.exists()
    assert result.paths.labels_val.exists()
    assert result.statistics.total_products == 3
    assert result.statistics.sampled_count == 3
    assert result.statistics.train_count == 2
    assert result.statistics.val_count == 1
    assert result.statistics.pre_labeled_count == 2

    yaml_text = result.data_yaml.read_text(encoding="utf-8")
    assert "train: images/train" in yaml_text
    assert "val: images/val" in yaml_text
    assert "vals" not in yaml_text
    assert "names: [CodeA, CodeB]" in yaml_text

    copied_images = sorted(path.name for path in (output_dir / "images").rglob("*.jpg"))
    assert copied_images == ["CodeA__Product1__a1.jpg", "CodeA__Product2__a3.jpg", "CodeB__Product1__b1.jpg"]
    copied_labels = sorted(path.name for path in (output_dir / "labels").rglob("*.txt"))
    assert copied_labels == ["CodeA__Product1__a1.txt", "CodeB__Product1__b1.txt"]

    mapping = MappingManager(result.mapping_path).load()
    sampled = mapping.get_sampled_images()
    assert len(sampled) == 3
    assert {image.info.split for image in sampled} == {"train", "val"}
    assert mapping.get_image_info("CodeA__Product1__a1.jpg")
    assert mapping.data.config["sample_mode"] == "count"
    assert mapping.get_statistics()["sample_pre_labeled_count"] == 2


def test_ratio_and_mixed_modes_calculate_sample_counts(tmp_path: Path) -> None:
    """Ratio and mixed modes follow the documented count rules."""
    site = tmp_path / "site"
    make_site_with_mapping(site, {"CodeA": {"Product1": [f"a{i}.jpg" for i in range(10)]}})

    ratio_result = Sampler().sample(
        SampleConfig(site_folder=site, output_dir=tmp_path / "ratio", mode="ratio", ratio=0.3, full_threshold=2)
    )
    assert ratio_result.statistics.sampled_count == 3

    # Reset mapping to unsampled images for the mixed assertion.
    make_site_with_mapping(site, {"CodeA": {"Product1": [f"a{i}.jpg" for i in range(10)]}})
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
        Sampler().sample(SampleConfig(site_folder=site, output_dir=tmp_path / "database"))


def test_invalid_config_raises_sample_invalid_config(tmp_path: Path) -> None:
    """Invalid sampling configuration values are rejected."""
    site = tmp_path / "site"
    make_site_with_mapping(site, {"CodeA": {"Product1": ["a1.jpg"]}})

    with pytest.raises(SampleInvalidConfigError):
        Sampler().sample(SampleConfig(site_folder=site, output_dir=tmp_path / "database", ratio=1.5))


def test_xml_unknown_class_raises_sample_xml_convert(tmp_path: Path) -> None:
    """XML labels with classes outside mapping classes fail with sampler XML errors."""
    site = tmp_path / "site"
    make_site_with_mapping(site, {"CodeA": {"Product1": ["a1.jpg"]}})
    write_xml(site / "CodeA" / "Product1" / "a1.xml", "OtherCode")

    with pytest.raises(SampleXmlConvertError):
        Sampler().sample(SampleConfig(site_folder=site, output_dir=tmp_path / "database"))


def test_cancelled_task_raises_task_cancelled(tmp_path: Path) -> None:
    """Sampler honors injected task cancellation before copying files."""
    site = tmp_path / "site"
    make_site_with_mapping(site, {"CodeA": {"Product1": ["a1.jpg"]}})
    handle = make_task_handle(is_cancel_requested=True)

    with pytest.raises(TaskCancelledError):
        Sampler(task_handle=handle).sample(SampleConfig(site_folder=site, output_dir=tmp_path / "database"))
