"""Scenario B: skip scanning with existing mapping and database."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PIL import Image

from core.inferencer import InferConfig, Inferencer
from core.restorer import RestoreConfig, Restorer
from core.trainer import TrainConfig, Trainer
from utils.mapping_manager import ImageInfo, MappingManager
from utils.path_encoder import PathEncoder


@dataclass
class FakeResult:
    """Minimal empty YOLO prediction result."""

    boxes: list[object]


class FakeTrainerModel:
    """Fake YOLO trainer."""

    def __init__(self, run_dir: Path) -> None:
        """Create a fake trainer."""
        self.run_dir = run_dir

    def add_callback(self, event: str, callback: Any) -> None:
        """Accept callbacks without using them."""

    def train(self, **kwargs: Any) -> object:
        """Write minimal training artifacts."""
        weights = self.run_dir / "weights"
        weights.mkdir(parents=True, exist_ok=True)
        (weights / "best.pt").write_bytes(b"best")
        (self.run_dir / "results.csv").write_text(
            "epoch,metrics/mAP50(B),metrics/mAP50-95(B)\n0,0.6,0.3\n",
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
    Image.new("RGB", (64, 64), color=(64, 64, 64)).save(path)


def make_mapping(site: Path, image_name: str) -> None:
    """Create mapping.json without calling Scanner."""
    encoder = PathEncoder()
    image_path = site / "CodeA" / "Product1" / image_name
    (site / ".autolabeler").mkdir(parents=True, exist_ok=True)
    (site / ".autolabeler" / "classes.txt").write_text("CodeA\n", encoding="utf-8")
    manager = MappingManager(site / ".autolabeler" / "mapping.json").create_new(site)
    manager.add_class(0, "CodeA")
    manager.add_image(
        encoder.encode("CodeA", "Product1", image_name),
        ImageInfo(
            original_relative=image_path.relative_to(site).as_posix(),
            code="CodeA",
            product="Product1",
            original_name=image_name,
            format=image_path.suffix.lower(),
            sampled=True,
            split="train",
        ),
    )
    manager.save()


def write_database(database: Path) -> Path:
    """Create an already-sampled YOLO database."""
    (database / "images" / "train").mkdir(parents=True)
    (database / "labels" / "train").mkdir(parents=True)
    (database / "images" / "val").mkdir(parents=True)
    (database / "labels" / "val").mkdir(parents=True)
    make_image(database / "images" / "train" / "CodeA__Product1__a1.jpg")
    (database / "labels" / "train" / "CodeA__Product1__a1.txt").write_text(
        "0 0.5 0.5 0.2 0.2\n",
        encoding="utf-8",
    )
    (database / "classes.txt").write_text("CodeA\n", encoding="utf-8")
    data_yaml = database / "data.yaml"
    data_yaml.write_text(
        "\n".join(
            (
                f"path: {database}",
                "train: images/train",
                "val: images/val",
                "nc: 1",
                "names: [CodeA]",
                "",
            )
        ),
        encoding="utf-8",
    )
    return data_yaml


def test_scenario_b_train_infer_restore_without_scanner(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    """Existing mapping and database can drive train, infer, and restore."""
    site = tmp_path / "site"
    make_image(site / "CodeA" / "Product1" / "a1.jpg")
    make_mapping(site, "a1.jpg")
    data_yaml = write_database(tmp_path / "database")
    model_path = tmp_path / "base.pt"
    model_path.write_bytes(b"model")
    train_output = tmp_path / "train_runs"
    monkeypatch.setattr(
        "core.trainer._load_yolo_model",
        lambda path: FakeTrainerModel(train_output / "train"),
    )

    train_result = Trainer().train(
        TrainConfig(data_yaml=data_yaml, base_model=model_path, output_dir=train_output)
    )

    monkeypatch.setattr(
        "core.inferencer._load_yolo_model", lambda path: FakeInferModel()
    )
    monkeypatch.setattr("core.inferencer._run_id", lambda: "run_20260514_104000")
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

    assert train_result.best_model.exists()
    assert infer_result.statistics.success == 1
    assert restore_result.success == 1
    assert (site / "CodeA" / "Product1" / "a1.xml").exists()
