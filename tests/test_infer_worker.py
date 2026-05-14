"""Tests for the desktop infer worker adapter."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
from PIL import Image

from core.inferencer import InferConfig
from core.scanner import ScanConfig, Scanner
from gui.workers.infer_worker import InferWorker
from utils.task_registry import TaskRegistry


@dataclass
class FakeResult:
    """Minimal prediction result with no boxes."""

    boxes: list[object]


class FakeModel:
    """Fake YOLO model returning one empty result per source image."""

    def predict(self, **kwargs: Any) -> list[FakeResult]:
        """Return one fake result per requested source."""
        return [FakeResult(boxes=[]) for _ in kwargs["source"]]


def make_image(path: Path) -> None:
    """Create a tiny RGB image fixture."""
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (32, 32), color=(128, 128, 128)).save(path)


def make_scanned_site(site: Path) -> None:
    """Create a one-image site and mapping.json."""
    make_image(site / "CodeA" / "Product1" / "a.jpg")
    Scanner().scan(ScanConfig(site_folder=site))


def test_infer_worker_runs_core_infer_and_updates_task(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Desktop infer worker is a thin adapter over the shared infer service."""
    site = tmp_path / "site"
    make_scanned_site(site)
    model_path = tmp_path / "best.pt"
    model_path.write_bytes(b"model")
    registry = TaskRegistry(task_dir=tmp_path / "tasks")
    monkeypatch.setattr("core.inferencer._load_yolo_model", lambda path: FakeModel())

    outcome = InferWorker(registry=registry).run(
        InferConfig(
            model_path=model_path,
            site_folder=site,
            output_base_dir=tmp_path / "runs",
            image_source="all",
            device="cpu",
        )
    )

    assert outcome.success is True
    assert outcome.result is not None
    assert outcome.result.statistics.processed == 1
    assert registry.get(outcome.task.task_id).status == "succeeded"


def test_infer_worker_converts_errors_to_failed_task(tmp_path: Path) -> None:
    """Desktop infer worker records business failures on the shared registry."""
    registry = TaskRegistry(task_dir=tmp_path / "tasks")

    outcome = InferWorker(registry=registry).run(
        InferConfig(
            model_path=tmp_path / "missing.pt",
            site_folder=tmp_path / "site",
            image_source="all",
        )
    )

    assert outcome.success is False
    assert outcome.error is not None
    assert outcome.error.code == "INFER_MODEL_NOT_FOUND"
    assert registry.get(outcome.task.task_id).status == "failed"
