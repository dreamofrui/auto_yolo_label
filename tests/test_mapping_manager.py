"""Tests for mapping.json management."""

from __future__ import annotations

from pathlib import Path

import pytest

from utils.exceptions import PathNotFoundError
from utils.mapping_manager import ImageInfo, MappingData, MappingManager


def make_image(name: str = "IMG_001.jpg") -> ImageInfo:
    """Create a representative image record."""
    return ImageInfo(
        original_relative=f"CodeA/ProductA/{name}",
        code="CodeA",
        product="ProductA",
        original_name=name,
        format=".jpg",
    )


def test_create_new_initializes_mapping_data(tmp_path: Path) -> None:
    """New mappings start with empty collections and default version."""
    mapping_path = tmp_path / "mapping.json"
    manager = MappingManager(mapping_path).create_new(tmp_path / "site", project_name="Demo")

    assert isinstance(manager.data, MappingData)
    assert manager.data.version == "1.0"
    assert manager.data.project_name == "Demo"
    assert manager.data.site_folder == tmp_path / "site"
    assert manager.data.classes == {}
    assert manager.data.images == {}
    assert manager.is_dirty is True


def test_add_class_and_image_updates_statistics(tmp_path: Path) -> None:
    """Adding images updates class data and aggregate statistics."""
    manager = MappingManager(tmp_path / "mapping.json").create_new(tmp_path / "site")

    manager.add_class(0, "CodeA")
    manager.add_image("CodeA__ProductA__IMG_001.jpg", make_image())

    assert manager.get_classes() == {"0": "CodeA"}
    assert manager.get_class_list() == ["CodeA"]
    assert manager.get_statistics()["total_images"] == 1
    assert manager.get_statistics()["sampled_count"] == 0


def test_save_and_load_round_trip_dataclasses(tmp_path: Path) -> None:
    """Saved JSON can be loaded back into MappingData and ImageInfo objects."""
    mapping_path = tmp_path / "mapping.json"
    manager = MappingManager(mapping_path).create_new(tmp_path / "site")
    manager.add_class(0, "CodeA")
    manager.add_image("CodeA__ProductA__IMG_001.jpg", make_image())
    manager.save()

    loaded = MappingManager(mapping_path).load()

    assert loaded.is_dirty is False
    assert loaded.data.site_folder == tmp_path / "site"
    assert loaded.get_image_info("CodeA__ProductA__IMG_001.jpg") == make_image()


def test_mark_methods_update_image_state_and_statistics(tmp_path: Path) -> None:
    """State mutation helpers keep the cache and statistics in sync."""
    manager = MappingManager(tmp_path / "mapping.json").create_new(tmp_path / "site")
    key = "CodeA__ProductA__IMG_001.jpg"
    manager.add_image(key, make_image())

    manager.mark_sampled(key, "train", label_source="pre_existing_xml")
    manager.mark_labeled(key)
    manager.mark_inferred([key])
    manager.mark_restored(key)

    image = manager.get_image_info(key)
    assert image is not None
    assert image.sampled is True
    assert image.split == "train"
    assert image.label_source == "manual"
    assert image.manual_labeled is True
    assert image.inferred is True
    assert image.restored is True
    assert manager.get_statistics()["sampled_count"] == 1
    assert manager.get_statistics()["labeled_count"] == 1
    assert manager.get_statistics()["inferred_count"] == 1
    assert manager.get_statistics()["restored_count"] == 1


def test_pending_inference_filters_sampled_but_not_inferred(tmp_path: Path) -> None:
    """Inferred is only a statistic and does not remove unsampled images from pending inference."""
    manager = MappingManager(tmp_path / "mapping.json").create_new(tmp_path / "site")
    unsampled_key = "CodeA__ProductA__IMG_001.jpg"
    sampled_key = "CodeA__ProductA__IMG_002.jpg"
    manager.add_image(unsampled_key, make_image("IMG_001.jpg"))
    manager.add_image(sampled_key, make_image("IMG_002.jpg"))
    manager.mark_inferred([unsampled_key])
    manager.mark_sampled(sampled_key, "val")

    pending = manager.get_pending_inference_images()

    assert [item.encoded_name for item in pending] == [unsampled_key]


def test_load_missing_mapping_raises_path_not_found(tmp_path: Path) -> None:
    """Loading a missing mapping path raises a business exception."""
    with pytest.raises(PathNotFoundError):
        MappingManager(tmp_path / "missing.json").load()
