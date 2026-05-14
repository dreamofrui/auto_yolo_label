"""Run a scan through the desktop worker adapter."""

from __future__ import annotations

import tempfile
from pathlib import Path

from loguru import logger
from PIL import Image

from core.scanner import ScanConfig
from gui.workers.scan_worker import ScanWorker
from utils.task_registry import TaskRegistry


def main() -> None:
    """Create a tiny site and scan it via the desktop worker."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        site = root / "site"
        image = site / "CodeA" / "Product1" / "a1.jpg"
        image.parent.mkdir(parents=True)
        Image.new("RGB", (32, 32), color=(255, 255, 255)).save(image)
        registry = TaskRegistry(root / "tasks")
        outcome = ScanWorker(registry=registry).run(ScanConfig(site_folder=site))
        if not outcome.success or outcome.result is None:
            raise SystemExit(outcome.error.message if outcome.error else "scan failed")
        logger.info("mapping_path={}", outcome.result.mapping_path)


if __name__ == "__main__":
    main()
