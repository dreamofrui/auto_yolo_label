"""Scenario A: full clean-site workflow."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PIL import Image

from core.inferencer import InferConfig, Inferencer
from core.restorer import RestoreConfig, Restorer
from core.sampler import SampleConfig, Sampler
from core.scanner import ScanConfig, Scanner
from core.trainer import TrainConfig, Trainer


@dataclass
class FakeBox:
    """Minimal predicted box."""

    cls: int
    xywhn: tuple[float, float, float, float]


@dataclass
class FakeResult:
    """Minimal YOLO prediction result."""

    boxes: list[FakeBox]


class FakeTrainerModel:
    """Fake YOLO trainer that writes expected run artifacts."""

    def __init__(self, run_dir: Path) -> None:
        """Create a fake trainer."""
        self.run_dir = run_dir
        self.callbacks: dict[str, list[Any]] = {}

    def add_callback(self, event: str, callback: Any) -> None:
        """Store callbacks for compatibility with Trainer."""
        self.callbacks.setdefault(event, []).append(callback)

    def train(self, **kwargs: Any) -> object:
        """Write minimal training artifacts."""
        weights = self.run_dir / "weights"
        weights.mkdir(parents=True, exist_ok=True)
        (weights / "best.pt").write_bytes(b"best")
        (weights / "last.pt").write_bytes(b"last")
        (self.run_dir / "results.csv").write_text(
            "epoch,metrics/mAP50(B),metrics/mAP50-95(B)\n0,0.8,0.5\n",
            encoding="utf-8",
        )
        return object()


class FakeInferModel:
    """Fake YOLO predictor."""

    def predict(self, **kwargs: Any) -> list[FakeResult]:
        """Return empty predictions for all sources."""
        return [FakeResult([]) for _ in kwargs["source"]]


def make_image(path: Path) -> None:
    """Create a tiny image fixture."""
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (64, 64), color=(128, 128, 128)).save(path)


def test_scenario_a_scan_sample_label_train_infer_restore(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    """A clean site can run through the full core workflow."""
    site = tmp_path / "site"
    for name in ("a1.jpg", "a2.jpg"):
        make_image(site / "CodeA" / "Product1" / name)

    scan_result = Scanner().scan(ScanConfig(site_folder=site))
    database = tmp_path / "database"
    sample_result = Sampler().sample(
        SampleConfig(site_folder=site, output_dir=database, count=1, full_threshold=1)
    )
    manual_label = sample_result.paths.labels_train / "CodeA__Product1__a1.txt"
    manual_label.parent.mkdir(parents=True, exist_ok=True)
    manual_label.write_text("0 0.5 0.5 0.2 0.2\n", encoding="utf-8")

    model_path = tmp_path / "base.pt"
    model_path.write_bytes(b"model")
    train_output = tmp_path / "train_runs"
    monkeypatch.setattr(
        "core.trainer._load_yolo_model",
        lambda path: FakeTrainerModel(train_output / "train"),
    )
    train_result = Trainer().train(
        TrainConfig(
            data_yaml=sample_result.data_yaml,
            base_model=model_path,
            output_dir=train_output,
        )
    )

    monkeypatch.setattr(
        "core.inferencer._load_yolo_model", lambda path: FakeInferModel()
    )
    monkeypatch.setattr("core.inferencer._run_id", lambda: "run_20260514_103000")
    infer_result = Inferencer().infer(
        InferConfig(
            model_path=train_result.best_model,
            site_folder=site,
            image_source="all",
            device="cpu",
        )
    )
    restore_result = Restorer().restore(
        RestoreConfig(
            site_folder=site, source_type="inference", run_id=infer_result.run_id
        )
    )

    assert scan_result.statistics.total_images == 2
    assert sample_result.statistics.sampled_count == 1
    assert train_result.best_model.exists()
    assert infer_result.statistics.success == 2
    assert restore_result.success == 2
    assert (site / "CodeA" / "Product1" / "a1.txt").exists()
    assert (site / "CodeA" / "Product1" / "a2.txt").exists()
