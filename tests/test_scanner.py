"""Tests for the site scanner core module."""

from __future__ import annotations

from pathlib import Path

import pytest

from core.scanner import (
    ScanConfig,
    ScanEmptyError,
    ScanInvalidStructureError,
    ScanLabelMismatchError,
    ScanPathNotFoundError,
    Scanner,
)
from utils.exceptions import TaskCancelledError
from utils.mapping_manager import MappingManager
from utils.task_registry import TaskHandle


def make_image(path: Path) -> None:
    """Create a lightweight image placeholder for scanner tests."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"image")


def make_task_handle(is_cancel_requested: bool = False) -> TaskHandle:
    """Create an in-memory task handle without touching TaskRegistry files."""
    return TaskHandle(
        task_id="task_scan_test",
        task_type="scan",
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


def write_xml(path: Path, names: list[str]) -> None:
    """Write a minimal VOC-like XML file with object names."""
    objects = "".join(f"<object><name>{name}</name></object>" for name in names)
    path.write_text(f"<annotation>{objects}</annotation>", encoding="utf-8")


def test_scanner_constructs_successfully() -> None:
    """Scanner can be constructed with default dependencies."""
    scanner = Scanner()

    assert isinstance(scanner, Scanner)


def test_scan_builds_mapping_and_classes_for_site_structure(tmp_path: Path) -> None:
    """Typical scans index direct Product images and write mapping/classes outputs."""
    site = tmp_path / "site"
    make_image(site / "BetaCode" / "Product2" / "B_001.JPG")
    make_image(site / "AlphaCode" / "Product1" / "A_001.jpg")
    make_image(site / "AlphaCode" / "Product1" / "A_002.PNG")
    make_image(site / "AlphaCode" / "Product2" / "A_003.bmp")
    make_image(site / "AlphaCode" / "Product2" / "nested" / "ignored.jpg")

    result = Scanner().scan(ScanConfig(site_folder=site))

    assert result.mapping_path == site / ".autolabeler" / "mapping.json"
    assert result.classes_path == site / ".autolabeler" / "classes.txt"
    assert result.mapping_path.exists()
    assert result.classes_path.read_text(encoding="utf-8") == "AlphaCode\nBetaCode\n"
    assert result.classes == ["AlphaCode", "BetaCode"]
    assert result.statistics.total_images == 4
    assert result.statistics.total_codes == 2
    assert result.statistics.total_products == 3
    assert result.products == {
        "AlphaCode": {"Product1": 2, "Product2": 1},
        "BetaCode": {"Product2": 1},
    }

    mapping = MappingManager(result.mapping_path).load()
    assert mapping.get_classes() == {"0": "AlphaCode", "1": "BetaCode"}
    assert mapping.get_statistics()["total_images"] == 4
    assert mapping.get_image_info("AlphaCode__Product1__A_002.PNG") is not None
    alpha_image = mapping.get_image_info("AlphaCode__Product1__A_002.PNG")
    assert alpha_image is not None
    assert alpha_image.original_relative == (Path("AlphaCode") / "Product1" / "A_002.PNG").as_posix()
    assert alpha_image.code == "AlphaCode"
    assert alpha_image.product == "Product1"
    assert alpha_image.original_name == "A_002.PNG"
    assert alpha_image.format == ".png"
    assert alpha_image.label_source == "none"
    assert mapping.get_image_info("AlphaCode__Product2__ignored.jpg") is None


def test_scan_writes_to_custom_output_dir(tmp_path: Path) -> None:
    """Custom output_dir receives scanner artifacts instead of the default directory."""
    site = tmp_path / "site"
    output_dir = tmp_path / "scan_output"
    make_image(site / "CodeA" / "ProductA" / "IMG_001.jpeg")

    result = Scanner().scan(ScanConfig(site_folder=site, output_dir=output_dir))

    assert result.mapping_path == output_dir / "mapping.json"
    assert result.classes_path == output_dir / "classes.txt"
    assert result.mapping_path.exists()
    assert result.classes_path.exists()
    assert not (site / ".autolabeler" / "mapping.json").exists()


def test_scan_missing_site_folder_raises_path_not_found(tmp_path: Path) -> None:
    """Missing site roots raise a scanner-specific path error."""
    with pytest.raises(ScanPathNotFoundError):
        Scanner().scan(ScanConfig(site_folder=tmp_path / "missing"))


def test_scan_missing_code_product_structure_raises_invalid_structure(tmp_path: Path) -> None:
    """Scanner requires Code/Product directory levels before scanning images."""
    site = tmp_path / "site"
    (site / "CodeOnly").mkdir(parents=True)

    with pytest.raises(ScanInvalidStructureError):
        Scanner().scan(ScanConfig(site_folder=site))


def test_scan_valid_structure_without_images_raises_empty(tmp_path: Path) -> None:
    """A valid site tree with no supported images raises ScanEmptyError."""
    site = tmp_path / "site"
    (site / "CodeA" / "ProductA").mkdir(parents=True)
    (site / "CodeA" / "ProductA" / "notes.txt").write_text("not image", encoding="utf-8")

    with pytest.raises(ScanEmptyError):
        Scanner().scan(ScanConfig(site_folder=site))


def test_scan_rejects_reserved_separator_in_filename(tmp_path: Path) -> None:
    """Filenames containing the path encoder separator are rejected."""
    site = tmp_path / "site"
    make_image(site / "CodeA" / "ProductA" / "IMG__001.jpg")

    with pytest.raises(ScanInvalidStructureError):
        Scanner().scan(ScanConfig(site_folder=site))


def test_scan_rejects_xml_label_mismatch(tmp_path: Path) -> None:
    """Existing XML labels must match the containing Code name."""
    site = tmp_path / "site"
    image_path = site / "CodeA" / "ProductA" / "IMG_001.jpg"
    make_image(image_path)
    write_xml(image_path.with_suffix(".xml"), ["OtherCode"])

    with pytest.raises(ScanLabelMismatchError):
        Scanner().scan(ScanConfig(site_folder=site))


def test_scan_can_skip_existing_xml_validation(tmp_path: Path) -> None:
    """XML label mismatches are ignored when validation is disabled."""
    site = tmp_path / "site"
    image_path = site / "CodeA" / "ProductA" / "IMG_001.jpg"
    make_image(image_path)
    write_xml(image_path.with_suffix(".xml"), ["OtherCode"])

    result = Scanner().scan(ScanConfig(site_folder=site, validate_existing_xml=False))

    assert result.statistics.total_images == 1


def test_scan_cancelled_task_raises_task_cancelled(tmp_path: Path) -> None:
    """Scanner checks the injected task handle during scan loops."""
    site = tmp_path / "site"
    make_image(site / "CodeA" / "ProductA" / "IMG_001.jpg")
    task_handle = make_task_handle(is_cancel_requested=True)

    with pytest.raises(TaskCancelledError):
        Scanner(task_handle=task_handle).scan(ScanConfig(site_folder=site))
