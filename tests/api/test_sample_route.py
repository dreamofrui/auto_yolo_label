"""Tests for the sample HTTP route."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient
from PIL import Image

from api.main import create_app
from core.scanner import ScanConfig, Scanner
from utils.task_registry import TaskRegistry


def make_image(path: Path) -> None:
    """Create a tiny image fixture."""
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (32, 32), color=(255, 255, 255)).save(path)


def make_scanned_site(site: Path) -> None:
    """Create a site and mapping.json for sample route tests."""
    make_image(site / "CodeA" / "Product1" / "a1.jpg")
    Scanner().scan(ScanConfig(site_folder=site))


def test_sample_route_accepts_camel_case_and_returns_task_result(
    tmp_path: Path,
) -> None:
    """HTTP sample route converts camelCase JSON to core SampleConfig and back."""
    site = tmp_path / "site"
    output_dir = tmp_path / "database"
    make_scanned_site(site)
    registry = TaskRegistry(task_dir=tmp_path / "tasks")
    client = TestClient(create_app(task_registry=registry))

    response = client.post(
        "/api/sample",
        json={
            "siteFolder": str(site),
            "outputDir": str(output_dir),
            "count": 1,
            "fullThreshold": 1,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["task"]["status"] == "succeeded"
    assert payload["result"]["datasetDir"] == str(output_dir)
    assert payload["result"]["statistics"]["sampledCount"] == 1
    assert registry.get(payload["task"]["taskId"]).status == "succeeded"


def test_sample_route_maps_business_errors_to_json(tmp_path: Path) -> None:
    """Sampler business errors become stable JSON error responses."""
    registry = TaskRegistry(task_dir=tmp_path / "tasks")
    client = TestClient(create_app(task_registry=registry))
    site = tmp_path / "site"
    site.mkdir()

    response = client.post(
        "/api/sample",
        json={"siteFolder": str(site), "outputDir": str(tmp_path / "database")},
    )

    assert response.status_code == 400
    payload = response.json()
    assert payload["success"] is False
    assert payload["error"]["code"] == "SAMPLE_MAPPING_NOT_FOUND"
