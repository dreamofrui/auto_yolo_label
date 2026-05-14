"""Tests for label inspector HTTP routes."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from api.main import create_app
from utils.task_registry import TaskRegistry


def make_label(path: Path, text: str = "") -> None:
    """Create one label file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def make_image(path: Path) -> None:
    """Create a lightweight source image fixture."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"image")


def make_client(registry: TaskRegistry) -> TestClient:
    """Create a test client from the main API app."""
    return TestClient(create_app(task_registry=registry))


def test_list_runs_route_returns_camel_case_run_metadata(tmp_path: Path) -> None:
    """List-runs route returns task metadata and run snapshots."""
    site = tmp_path / "site"
    run_dir = site / ".autolabeler" / "inference_results" / "run_20260513_104000"
    run_dir.mkdir(parents=True)
    (run_dir / "inference_config.json").write_text(
        json.dumps({"run_id": "run_20260513_104000", "image_count": 1}),
        encoding="utf-8",
    )
    registry = TaskRegistry(tmp_path / "tasks")
    client = make_client(registry)

    response = client.post("/api/label-inspector/runs", json={"siteFolder": str(site)})

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["task"]["status"] == "succeeded"
    assert payload["result"]["runs"][0]["runId"] == "run_20260513_104000"
    assert payload["result"]["runs"][0]["configExists"] is True
    assert registry.get(payload["task"]["taskId"]).status == "succeeded"


def test_run_tree_route_returns_product_counts(tmp_path: Path) -> None:
    """Run-tree route returns Code/Product label counts."""
    site = tmp_path / "site"
    product_dir = (
        site
        / ".autolabeler"
        / "inference_results"
        / "run_20260513_104000"
        / "CodeA"
        / "Product1"
    )
    make_label(product_dir / "a.txt", "0 0.5 0.5 0.2 0.2\n")
    make_label(product_dir / "b.txt", "\n")
    registry = TaskRegistry(tmp_path / "tasks")
    client = make_client(registry)

    response = client.post(
        "/api/label-inspector/run-tree",
        json={"siteFolder": str(site), "runId": "run_20260513_104000"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["result"]["nodes"][0]["code"] == "CodeA"
    assert payload["result"]["nodes"][0]["product"] == "Product1"
    assert payload["result"]["nodes"][0]["labelCount"] == 2
    assert payload["result"]["nodes"][0]["emptyCount"] == 1


def test_product_labels_route_returns_labels_and_source_images(tmp_path: Path) -> None:
    """Product-labels route returns label records with image paths."""
    site = tmp_path / "site"
    product_dir = (
        site
        / ".autolabeler"
        / "inference_results"
        / "run_20260513_104000"
        / "CodeA"
        / "Product1"
    )
    make_label(product_dir / "a.txt", "0 0.5 0.5 0.2 0.2\n")
    image_path = site / "CodeA" / "Product1" / "a.jpg"
    make_image(image_path)
    registry = TaskRegistry(tmp_path / "tasks")
    client = make_client(registry)

    response = client.post(
        "/api/label-inspector/product-labels",
        json={
            "siteFolder": str(site),
            "runId": "run_20260513_104000",
            "code": "CodeA",
            "product": "Product1",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["result"]["labels"][0]["imageName"] == "a.jpg"
    assert payload["result"]["labels"][0]["imagePath"] == str(image_path)
    assert payload["result"]["labels"][0]["objectCount"] == 1


def test_run_tree_route_maps_business_errors_to_json(tmp_path: Path) -> None:
    """Missing runs are returned as stable business errors."""
    registry = TaskRegistry(tmp_path / "tasks")
    client = make_client(registry)

    response = client.post(
        "/api/label-inspector/run-tree",
        json={"siteFolder": str(tmp_path / "site"), "runId": "missing"},
    )

    assert response.status_code == 400
    payload = response.json()
    assert payload["success"] is False
    assert payload["error"]["code"] == "INSPECTOR_RUN_NOT_FOUND"
