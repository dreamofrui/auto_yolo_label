"""Tests for the restore HTTP route."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient
from PIL import Image

from api.main import create_app
from core.scanner import ScanConfig, Scanner
from utils.path_encoder import PathEncoder
from utils.task_registry import TaskRegistry


def make_image(path: Path) -> None:
    """Create a tiny image fixture."""
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (32, 32), color=(255, 255, 255)).save(path)


def make_scanned_site(site: Path) -> str:
    """Create a site with one scanned image and return its encoded stem."""
    image_path = site / "CodeA" / "Product1" / "a.jpg"
    make_image(image_path)
    Scanner().scan(ScanConfig(site_folder=site))
    encoded_name = PathEncoder().encode("CodeA", "Product1", "a.jpg")
    return Path(encoded_name).stem


def make_restore_client(registry: TaskRegistry) -> TestClient:
    """Create a test app with only the restore router added locally."""
    from api.routes.restore import router as restore_router

    app = create_app(task_registry=registry)
    app.include_router(restore_router)
    return TestClient(app)


def test_restore_route_restores_database_labels_and_records_task(tmp_path: Path) -> None:
    """HTTP restore route copies database labels beside original images."""
    site = tmp_path / "site"
    database_dir = tmp_path / "database"
    encoded_stem = make_scanned_site(site)
    label_path = database_dir / "labels" / "train" / f"{encoded_stem}.txt"
    label_path.parent.mkdir(parents=True, exist_ok=True)
    label_path.write_text("0 0.500000 0.500000 0.250000 0.250000\n", encoding="utf-8")
    registry = TaskRegistry(task_dir=tmp_path / "tasks")
    client = make_restore_client(registry)

    response = client.post(
        "/api/restore",
        json={
            "siteFolder": str(site),
            "sourceType": "database",
            "databaseDir": str(database_dir),
            "overwrite": True,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["task"]["status"] == "succeeded"
    assert payload["result"]["success"] == 1
    assert (site / "CodeA" / "Product1" / "a.txt").exists()
    assert registry.get(payload["task"]["taskId"]).status == "succeeded"


def test_restore_route_maps_invalid_source_type_to_business_error(tmp_path: Path) -> None:
    """Restore route returns stable JSON errors for invalid source_type."""
    site = tmp_path / "site"
    make_scanned_site(site)
    registry = TaskRegistry(task_dir=tmp_path / "tasks")
    client = make_restore_client(registry)

    response = client.post(
        "/api/restore",
        json={"siteFolder": str(site), "sourceType": "bad-source"},
    )

    assert response.status_code == 400
    payload = response.json()
    assert payload["success"] is False
    assert payload["error"]["code"] == "RESTORE_INVALID_SOURCE_TYPE"
