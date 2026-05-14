"""Tests for the scan HTTP route."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient
from PIL import Image

from api.main import create_app
from utils.task_registry import TaskRegistry


def make_image(path: Path) -> None:
    """Create a tiny image fixture."""
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (32, 32), color=(255, 255, 255)).save(path)


def test_scan_route_accepts_camel_case_and_returns_task_result(tmp_path: Path) -> None:
    """HTTP scan route converts camelCase JSON to core ScanConfig and back."""
    site = tmp_path / "site"
    make_image(site / "CodeA" / "Product1" / "a1.jpg")
    registry = TaskRegistry(task_dir=tmp_path / "tasks")
    client = TestClient(create_app(task_registry=registry))

    response = client.post(
        "/api/scan",
        json={"siteFolder": str(site), "validateExistingXml": True},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["task"]["status"] == "succeeded"
    mapping_path = Path(payload["result"]["mappingPath"])
    assert mapping_path.name == "mapping.json"
    assert mapping_path.parent.name == ".autolabeler"
    assert payload["result"]["statistics"]["totalImages"] == 1
    assert registry.get(payload["task"]["taskId"]).status == "succeeded"


def test_scan_route_maps_business_errors_to_json(tmp_path: Path) -> None:
    """AutoLabelerError exceptions become stable JSON error responses."""
    registry = TaskRegistry(task_dir=tmp_path / "tasks")
    client = TestClient(create_app(task_registry=registry))

    response = client.post("/api/scan", json={"siteFolder": str(tmp_path / "missing")})

    assert response.status_code == 400
    payload = response.json()
    assert payload["success"] is False
    assert payload["error"]["code"] == "SCAN_PATH_NOT_FOUND"
