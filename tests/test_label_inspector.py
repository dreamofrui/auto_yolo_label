"""Tests for the inference label inspection module."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.label_inspector import (
    GetProductLabelsConfig,
    GetRunTreeConfig,
    InspectorClassesNotFoundError,
    InspectorMappingNotFoundError,
    InspectorOriginalImageMissingError,
    InspectorProductNotFoundError,
    InspectorRunNotFoundError,
    LabelInspector,
    ListRunsConfig,
)
from utils.mapping_manager import ImageInfo, MappingManager
from utils.path_encoder import PathEncoder
from utils.exceptions import ErrorCode


def make_label(path: Path, text: str = "") -> None:
    """Create one label file with parent directories."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def make_image(path: Path) -> None:
    """Create a lightweight image placeholder."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"image")


def make_mapping(site: Path, images: list[tuple[str, str, str]]) -> MappingManager:
    """Create mapping.json records for inspector tests."""
    (site / ".autolabeler").mkdir(parents=True, exist_ok=True)
    (site / ".autolabeler" / "classes.txt").write_text("CodeA\n", encoding="utf-8")
    manager = MappingManager(site / ".autolabeler" / "mapping.json").create_new(site)
    for class_id, code in enumerate(sorted({code for code, _, _ in images})):
        manager.add_class(class_id, code)
    encoder = PathEncoder()
    for code, product, filename in images:
        manager.add_image(
            encoder.encode(code, product, filename),
            ImageInfo(
                original_relative=Path(code, product, filename).as_posix(),
                code=code,
                product=product,
                original_name=filename,
                format=Path(filename).suffix.lower(),
            ),
        )
    manager.save()
    return manager


def test_label_inspector_constructs_successfully() -> None:
    """LabelInspector can be constructed with default dependencies."""
    inspector = LabelInspector()

    assert isinstance(inspector, LabelInspector)


def test_list_runs_parses_valid_configs_without_loading_mapping(tmp_path: Path) -> None:
    """Run listing scans only inference result folders and parses valid config snapshots."""
    site = tmp_path / "site"
    run_a = site / ".autolabeler" / "inference_results" / "run_20260513_103000"
    run_b = site / ".autolabeler" / "inference_results" / "run_20260513_104000"
    run_a.mkdir(parents=True)
    run_b.mkdir(parents=True)
    (run_a / "inference_config.json").write_text(
        json.dumps({"run_id": "run_20260513_103000", "image_count": 2}),
        encoding="utf-8",
    )
    (run_b / "inference_config.json").write_text(
        json.dumps({"run_id": "run_20260513_104000", "image_count": 1}),
        encoding="utf-8",
    )
    (site / ".autolabeler" / "mapping.json").write_text("{not-json", encoding="utf-8")

    runs = LabelInspector().list_runs(ListRunsConfig(site_folder=site))

    assert [run.run_id for run in runs] == [
        "run_20260513_104000",
        "run_20260513_103000",
    ]
    assert runs[0].config_exists is True
    assert runs[0].config == {"run_id": "run_20260513_104000", "image_count": 1}
    assert runs[0].created_at == "2026-05-13 10:40:00"
    assert runs[0].path == run_b


def test_list_runs_handles_missing_and_invalid_configs_as_absent(
    tmp_path: Path,
) -> None:
    """Unreadable or invalid config snapshots do not make run listing fail."""
    site = tmp_path / "site"
    invalid_run = site / ".autolabeler" / "inference_results" / "run_20260513_103000"
    no_config_run = site / ".autolabeler" / "inference_results" / "run_20260513_104000"
    invalid_run.mkdir(parents=True)
    no_config_run.mkdir(parents=True)
    (invalid_run / "inference_config.json").write_text("{not-json", encoding="utf-8")

    runs = LabelInspector().list_runs(ListRunsConfig(site_folder=site))

    assert [(run.run_id, run.config_exists, run.config) for run in runs] == [
        ("run_20260513_104000", False, None),
        ("run_20260513_103000", False, None),
    ]


def test_list_runs_returns_empty_when_inference_root_is_missing(tmp_path: Path) -> None:
    """Missing inference_results root is a valid empty listing."""
    runs = LabelInspector().list_runs(ListRunsConfig(site_folder=tmp_path / "site"))

    assert runs == []


def test_get_run_tree_counts_labels_and_filters_control_files(tmp_path: Path) -> None:
    """Run tree includes Code/Product nodes with label and empty-label counts."""
    site = tmp_path / "site"
    run = site / ".autolabeler" / "inference_results" / "run_20260513_103000"
    product_a = run / "labels" / "CodeA" / "Product1"
    product_b = run / "labels" / "CodeA" / "Product2"
    make_label(product_a / "one.txt", "0 0.5 0.5 0.2 0.2\n")
    make_label(product_a / "two.txt", "  \n")
    make_label(product_a / "classes.txt", "CodeA\n")
    make_label(product_a / "data.yaml", "path: .\n")
    make_label(product_a / "README.txt", "manual note\n")
    make_label(product_b / "three.txt", "\n")

    tree = LabelInspector().get_run_tree(
        GetRunTreeConfig(site_folder=site, run_id="run_20260513_103000")
    )

    assert tree == [
        type(tree[0])(
            code="CodeA",
            product="Product1",
            label_count=2,
            empty_count=1,
            path=product_a,
        ),
        type(tree[0])(
            code="CodeA",
            product="Product2",
            label_count=1,
            empty_count=1,
            path=product_b,
        ),
    ]


def test_get_run_tree_missing_run_raises_run_not_found(tmp_path: Path) -> None:
    """Missing run directories raise an inspector-specific business exception."""
    with pytest.raises(InspectorRunNotFoundError) as exc_info:
        LabelInspector().get_run_tree(
            GetRunTreeConfig(site_folder=tmp_path / "site", run_id="run_missing")
        )

    assert exc_info.value.code == ErrorCode.INSPECTOR_RUN_NOT_FOUND


def test_get_product_labels_counts_objects_and_resolves_original_images(
    tmp_path: Path,
) -> None:
    """Product label listing returns mapped images and missing-label warnings."""
    site = tmp_path / "site"
    make_mapping(
        site,
        [
            ("CodeA", "Product1", "one.jpg"),
            ("CodeA", "Product1", "two.PNG"),
            ("CodeA", "Product1", "needs_label.bmp"),
        ],
    )
    product = (
        site
        / ".autolabeler"
        / "inference_results"
        / "run_20260513_103000"
        / "labels"
        / "CodeA"
        / "Product1"
    )
    make_label(product / "one.txt", "0 0.5 0.5 0.2 0.2\n1 0.4 0.4 0.2 0.2\n\n")
    make_label(product / "two.txt", " \n")
    make_label(product / "classes.txt", "CodeA\n")
    make_label(product / "data.yaml", "path: .\n")
    make_label(product / "README.txt", "manual note\n")
    image_one = site / "CodeA" / "Product1" / "one.jpg"
    image_two = site / "CodeA" / "Product1" / "two.PNG"
    make_image(image_one)
    make_image(image_two)
    make_image(site / "CodeA" / "Product1" / "needs_label.bmp")

    labels = LabelInspector().get_product_labels(
        GetProductLabelsConfig(
            site_folder=site,
            run_id="run_20260513_103000",
            code="CodeA",
            product="Product1",
        )
    )

    assert [
        (
            label.image_name,
            label.image_path,
            label.label_path,
            label.object_count,
            label.missing_label,
        )
        for label in labels
    ] == [
        (
            "needs_label.bmp",
            site / "CodeA" / "Product1" / "needs_label.bmp",
            product / "needs_label.txt",
            0,
            True,
        ),
        ("one.jpg", image_one, product / "one.txt", 2, False),
        ("two.PNG", image_two, product / "two.txt", 0, False),
    ]


def test_get_product_labels_uses_mapping_not_directory_guess(tmp_path: Path) -> None:
    """Flow review resolves original images from mapping paths."""
    site = tmp_path / "site"
    manager = MappingManager(site / ".autolabeler" / "mapping.json").create_new(site)
    manager.add_class(0, "CodeA")
    (site / ".autolabeler").mkdir(parents=True, exist_ok=True)
    (site / ".autolabeler" / "classes.txt").write_text("CodeA\n", encoding="utf-8")
    image_path = site / "raw" / "actual.jpg"
    make_image(image_path)
    manager.add_image(
        "CodeA__Product1__one.jpg",
        ImageInfo(
            original_relative="raw/actual.jpg",
            code="CodeA",
            product="Product1",
            original_name="one.jpg",
            format=".jpg",
        ),
    )
    manager.save()
    product = (
        site
        / ".autolabeler"
        / "inference_results"
        / "run_20260513_103000"
        / "labels"
        / "CodeA"
        / "Product1"
    )
    make_label(product / "one.txt", "0 0.5 0.5 0.2 0.2\n")

    labels = LabelInspector().get_product_labels(
        GetProductLabelsConfig(
            site_folder=site,
            run_id="run_20260513_103000",
            code="CodeA",
            product="Product1",
        )
    )

    assert labels[0].image_path == image_path


def test_get_product_labels_missing_original_image_blocks_open(
    tmp_path: Path,
) -> None:
    """Missing mapped original images block opening a review node."""
    site = tmp_path / "site"
    make_mapping(site, [("CodeA", "Product1", "one.jpg")])
    product = (
        site
        / ".autolabeler"
        / "inference_results"
        / "run_20260513_103000"
        / "labels"
        / "CodeA"
        / "Product1"
    )
    make_label(product / "one.txt", "0 0.5 0.5 0.2 0.2\n")

    with pytest.raises(InspectorOriginalImageMissingError) as exc_info:
        LabelInspector().get_product_labels(
            GetProductLabelsConfig(
                site_folder=site,
                run_id="run_20260513_103000",
                code="CodeA",
                product="Product1",
            )
        )

    assert exc_info.value.code == ErrorCode.INSPECTOR_ORIGINAL_IMAGE_MISSING
    assert "one.jpg" in str(exc_info.value.details)


def test_get_product_labels_missing_mapping_blocks_flow_review(
    tmp_path: Path,
) -> None:
    """Flow review requires mapping.json before opening a product node."""
    site = tmp_path / "site"
    product = (
        site
        / ".autolabeler"
        / "inference_results"
        / "run_20260513_103000"
        / "labels"
        / "CodeA"
        / "Product1"
    )
    make_label(product / "one.txt", "0 0.5 0.5 0.2 0.2\n")
    (site / ".autolabeler" / "classes.txt").write_text("CodeA\n", encoding="utf-8")

    with pytest.raises(InspectorMappingNotFoundError) as exc_info:
        LabelInspector().get_product_labels(
            GetProductLabelsConfig(
                site_folder=site,
                run_id="run_20260513_103000",
                code="CodeA",
                product="Product1",
            )
        )

    assert exc_info.value.code == ErrorCode.INSPECTOR_MAPPING_NOT_FOUND


def test_get_product_labels_empty_classes_blocks_flow_review(
    tmp_path: Path,
) -> None:
    """Flow review requires a non-empty classes.txt before opening a product node."""
    site = tmp_path / "site"
    make_mapping(site, [("CodeA", "Product1", "one.jpg")])
    (site / ".autolabeler" / "classes.txt").write_text(" \n", encoding="utf-8")
    make_image(site / "CodeA" / "Product1" / "one.jpg")
    product = (
        site
        / ".autolabeler"
        / "inference_results"
        / "run_20260513_103000"
        / "labels"
        / "CodeA"
        / "Product1"
    )
    make_label(product / "one.txt", "0 0.5 0.5 0.2 0.2\n")

    with pytest.raises(InspectorClassesNotFoundError) as exc_info:
        LabelInspector().get_product_labels(
            GetProductLabelsConfig(
                site_folder=site,
                run_id="run_20260513_103000",
                code="CodeA",
                product="Product1",
            )
        )

    assert exc_info.value.code == ErrorCode.INSPECTOR_CLASSES_NOT_FOUND


def test_get_product_labels_missing_product_raises_product_not_found(
    tmp_path: Path,
) -> None:
    """Missing product label directories raise an inspector-specific exception."""
    site = tmp_path / "site"
    make_mapping(site, [("CodeA", "Product1", "one.jpg")])
    run = (
        site
        / ".autolabeler"
        / "inference_results"
        / "run_20260513_103000"
        / "labels"
    )
    run.mkdir(parents=True)

    with pytest.raises(InspectorProductNotFoundError) as exc_info:
        LabelInspector().get_product_labels(
            GetProductLabelsConfig(
                site_folder=site,
                run_id="run_20260513_103000",
                code="CodeA",
                product="Product1",
            )
        )

    assert exc_info.value.code == ErrorCode.INSPECTOR_PRODUCT_NOT_FOUND
