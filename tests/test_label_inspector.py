"""Tests for the inference label inspection module."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.label_inspector import (
    GetProductLabelsConfig,
    GetRunTreeConfig,
    InspectorProductNotFoundError,
    InspectorRunNotFoundError,
    LabelInspector,
    ListRunsConfig,
)
from utils.exceptions import ErrorCode


def make_label(path: Path, text: str = "") -> None:
    """Create one label file with parent directories."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def make_image(path: Path) -> None:
    """Create a lightweight image placeholder."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"image")


def test_label_inspector_constructs_successfully() -> None:
    """LabelInspector can be constructed with default dependencies."""
    inspector = LabelInspector()

    assert isinstance(inspector, LabelInspector)


def test_list_runs_parses_valid_configs_without_mapping_json(tmp_path: Path) -> None:
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

    assert [run.run_id for run in runs] == ["run_20260513_104000", "run_20260513_103000"]
    assert runs[0].config_exists is True
    assert runs[0].config == {"run_id": "run_20260513_104000", "image_count": 1}
    assert runs[0].created_at == "2026-05-13 10:40:00"
    assert runs[0].path == run_b


def test_list_runs_handles_missing_and_invalid_configs_as_absent(tmp_path: Path) -> None:
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
    product_a = run / "CodeA" / "Product1"
    product_b = run / "CodeA" / "Product2"
    make_label(product_a / "one.txt", "0 0.5 0.5 0.2 0.2\n")
    make_label(product_a / "two.txt", "  \n")
    make_label(product_a / "classes.txt", "CodeA\n")
    make_label(product_a / "data.yaml", "path: .\n")
    make_label(product_a / "README.txt", "manual note\n")
    make_label(product_b / "three.txt", "\n")

    tree = LabelInspector().get_run_tree(GetRunTreeConfig(site_folder=site, run_id="run_20260513_103000"))

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


def test_get_product_labels_counts_objects_and_resolves_original_images(tmp_path: Path) -> None:
    """Product label listing returns object counts and best-effort original image paths."""
    site = tmp_path / "site"
    product = site / ".autolabeler" / "inference_results" / "run_20260513_103000" / "CodeA" / "Product1"
    make_label(product / "one.txt", "0 0.5 0.5 0.2 0.2\n1 0.4 0.4 0.2 0.2\n\n")
    make_label(product / "two.txt", " \n")
    make_label(product / "missing.txt", "2 0.1 0.1 0.2 0.2\n")
    make_label(product / "classes.txt", "CodeA\n")
    make_label(product / "data.yaml", "path: .\n")
    make_label(product / "README.txt", "manual note\n")
    image_one = site / "CodeA" / "Product1" / "one.jpg"
    image_two = site / "CodeA" / "Product1" / "two.PNG"
    make_image(image_one)
    make_image(image_two)

    labels = LabelInspector().get_product_labels(
        GetProductLabelsConfig(
            site_folder=site,
            run_id="run_20260513_103000",
            code="CodeA",
            product="Product1",
        )
    )

    assert [(label.image_name, label.image_path, label.object_count) for label in labels] == [
        ("missing", None, 1),
        ("one.jpg", image_one, 2),
        ("two.PNG", image_two, 0),
    ]
    assert [label.label_path for label in labels] == [
        product / "missing.txt",
        product / "one.txt",
        product / "two.txt",
    ]


def test_get_product_labels_missing_product_raises_product_not_found(tmp_path: Path) -> None:
    """Missing product directories raise an inspector-specific business exception."""
    run = tmp_path / "site" / ".autolabeler" / "inference_results" / "run_20260513_103000"
    run.mkdir(parents=True)

    with pytest.raises(InspectorProductNotFoundError) as exc_info:
        LabelInspector().get_product_labels(
            GetProductLabelsConfig(
                site_folder=tmp_path / "site",
                run_id="run_20260513_103000",
                code="CodeA",
                product="Product1",
            )
        )

    assert exc_info.value.code == ErrorCode.INSPECTOR_PRODUCT_NOT_FOUND
