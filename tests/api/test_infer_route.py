"""Tests for the infer HTTP route."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from api.main import create_app
from core.scanner import ScanConfig, Scanner
from utils.task_registry import TaskRegistry


@dataclass
class FakeResult:
    """Minimal prediction result with no boxes."""

    boxes: list[object]


class FakeModel:
    """Fake YOLO model returning one empty result per source image."""

    def predict(self, **kwargs: Any) -> list[FakeResult]:
        """Return one fake result per requested source."""
        sources = kwargs["source"]
        return [FakeResult(boxes=[]) for _ in sources]


def make_image(path: Path) -> None:
    """Create a tiny RGB image fixture."""
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (32, 32), color=(255, 255, 255)).save(path)


def make_scanned_site(site: Path) -> None:
    """Create a one-image site and mapping.json."""
    make_image(site / "CodeA" / "Product1" / "a.jpg")
    Scanner().scan(ScanConfig(site_folder=site))


def make_client(registry: TaskRegistry) -> TestClient:
    """Create a test client from the main API app."""
    return TestClient(create_app(task_registry=registry))


def test_infer_route_accepts_camel_case_and_returns_task_result(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """HTTP infer route converts camelCase JSON to core InferConfig and back."""
    site = tmp_path / "site"
    make_scanned_site(site)
    model_path = tmp_path / "best.pt"
    model_path.write_bytes(b"model")
    output_base_dir = tmp_path / "runs"
    registry = TaskRegistry(task_dir=tmp_path / "tasks")
    client = make_client(registry)
    monkeypatch.setattr("core.inferencer._load_yolo_model", lambda path: FakeModel())

    response = client.post(
        "/api/infer",
        json={
            "modelPath": str(model_path),
            "siteFolder": str(site),
            "outputBaseDir": str(output_base_dir),
            "imageSource": "all",
            "device": "cpu",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["task"]["status"] == "succeeded"
    assert payload["result"]["runId"]
    assert Path(payload["result"]["inferenceOutputDir"]).parent == output_base_dir
    assert payload["result"]["statistics"]["processed"] == 1
    assert registry.get(payload["task"]["taskId"]).status == "succeeded"


def test_infer_route_maps_missing_model_to_error_json(tmp_path: Path) -> None:
    """Inferencer business errors become stable HTTP error responses."""
    registry = TaskRegistry(task_dir=tmp_path / "tasks")
    client = make_client(registry)

    response = client.post(
        "/api/infer",
        json={
            "modelPath": str(tmp_path / "missing.pt"),
            "siteFolder": str(tmp_path / "site"),
            "imageSource": "all",
        },
    )

    assert response.status_code == 400
    payload = response.json()
    assert payload["success"] is False
    assert payload["error"]["code"] == "INFER_MODEL_NOT_FOUND"
