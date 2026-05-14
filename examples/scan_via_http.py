"""Run a scan through the HTTP adapter."""

from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi.testclient import TestClient
from loguru import logger
from PIL import Image

from api.main import create_app
from utils.task_registry import TaskRegistry


def main() -> None:
    """Create a tiny site and scan it via FastAPI TestClient."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        site = root / "site"
        image = site / "CodeA" / "Product1" / "a1.jpg"
        image.parent.mkdir(parents=True)
        Image.new("RGB", (32, 32), color=(255, 255, 255)).save(image)
        client = TestClient(create_app(task_registry=TaskRegistry(root / "tasks")))
        response = client.post("/api/scan", json={"siteFolder": str(site)})
        response.raise_for_status()
        logger.info("mapping_path={}", response.json()["result"]["mappingPath"])


if __name__ == "__main__":
    main()
