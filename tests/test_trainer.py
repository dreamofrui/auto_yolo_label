"""Tests for the YOLO trainer core module."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from core.trainer import (
    TrainBaseModelNotFoundError,
    TrainConfig,
    TrainDataYamlInvalidError,
    TrainInterruptedError,
    TrainOOMError,
    Trainer,
)
from utils.task_registry import TaskHandle


@dataclass
class FakeTrainerState:
    """Minimal Ultralytics trainer-like callback state."""

    epoch: int
    epochs: int
    metrics: dict[str, float]


class FakeYOLO:
    """Small fake model with callback support."""

    def __init__(self, run_dir: Path, error: BaseException | None = None) -> None:
        """Create a fake model."""
        self.run_dir = run_dir
        self.error = error
        self.callbacks: dict[str, list[Any]] = {}
        self.train_kwargs: dict[str, Any] | None = None

    def add_callback(self, event: str, callback: Any) -> None:
        """Store a callback for later training simulation."""
        self.callbacks.setdefault(event, []).append(callback)

    def train(self, **kwargs: Any) -> object:
        """Simulate a YOLO train call."""
        self.train_kwargs = kwargs
        for callback in self.callbacks.get("on_fit_epoch_end", []):
            callback(FakeTrainerState(epoch=0, epochs=int(kwargs["epochs"]), metrics={"mAP50": 0.5, "mAP50-95": 0.25}))
        if self.error is not None:
            raise self.error
        weights = self.run_dir / "weights"
        weights.mkdir(parents=True, exist_ok=True)
        (weights / "best.pt").write_bytes(b"best")
        (weights / "last.pt").write_bytes(b"last")
        (self.run_dir / "results.csv").write_text(
            "epoch,metrics/mAP50(B),metrics/mAP50-95(B)\n0,0.5,0.25\n1,0.7,0.4\n",
            encoding="utf-8",
        )
        return object()


def make_task_handle(cancelled: bool = False) -> TaskHandle:
    """Create an in-memory train task handle."""
    return TaskHandle(
        task_id="task_train_test",
        task_type="train",
        status="running",
        progress_current=0,
        progress_total=0,
        progress_message="",
        logs=[],
        result=None,
        error=None,
        created_at="2026-05-13 00:00:00",
        started_at="2026-05-13 00:00:00",
        finished_at=None,
        is_cancel_requested=cancelled,
    )


def write_data_yaml(path: Path) -> None:
    """Write a minimal YOLO data.yaml."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            (
                f"path: {path.parent}",
                "train: images/train",
                "val: images/val",
                "nc: 1",
                "names: [CodeA]",
                "",
            )
        ),
        encoding="utf-8",
    )


def test_trainer_constructs_successfully() -> None:
    """Trainer can be constructed with default dependencies."""
    trainer = Trainer()

    assert isinstance(trainer, Trainer)


def test_train_missing_data_yaml_raises_invalid(tmp_path: Path) -> None:
    """Missing data.yaml raises a trainer-specific validation error."""
    model = tmp_path / "model.pt"
    model.write_bytes(b"model")

    with pytest.raises(TrainDataYamlInvalidError):
        Trainer().train(TrainConfig(data_yaml=tmp_path / "missing.yaml", base_model=model, output_dir=tmp_path / "runs"))


def test_train_invalid_data_yaml_raises_invalid(tmp_path: Path) -> None:
    """data.yaml must contain the required YOLO fields."""
    data_yaml = tmp_path / "data.yaml"
    data_yaml.write_text("path: .\ntrain: images/train\n", encoding="utf-8")
    model = tmp_path / "model.pt"
    model.write_bytes(b"model")

    with pytest.raises(TrainDataYamlInvalidError):
        Trainer().train(TrainConfig(data_yaml=data_yaml, base_model=model, output_dir=tmp_path / "runs"))


def test_train_missing_base_model_raises_not_found(tmp_path: Path) -> None:
    """Missing base model raises a trainer-specific path error."""
    data_yaml = tmp_path / "data.yaml"
    write_data_yaml(data_yaml)

    with pytest.raises(TrainBaseModelNotFoundError):
        Trainer().train(TrainConfig(data_yaml=data_yaml, base_model=tmp_path / "missing.pt", output_dir=tmp_path / "runs"))


def test_train_success_returns_weights_metrics_and_effective_config(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Successful training returns output paths, metrics, and effective config."""
    data_yaml = tmp_path / "data.yaml"
    write_data_yaml(data_yaml)
    model = tmp_path / "model.pt"
    model.write_bytes(b"model")
    run_dir = tmp_path / "runs" / "train"
    fake = FakeYOLO(run_dir)
    monkeypatch.setattr("core.trainer._load_yolo_model", lambda base_model: fake)
    monkeypatch.setattr("core.trainer.resolve_device", lambda requested: "cpu")

    result = Trainer().train(
        TrainConfig(data_yaml=data_yaml, base_model=model, output_dir=tmp_path / "runs", epochs=2, batch_size=-1)
    )

    assert result.best_model == run_dir / "weights" / "best.pt"
    assert result.last_model == run_dir / "weights" / "last.pt"
    assert result.output_dir == run_dir
    assert result.effective_config["device"] == "cpu"
    assert result.effective_config["batch_size"] == 1
    assert result.metrics.best_epoch == 1
    assert result.metrics.best_map50 == 0.7
    assert result.metrics.final_map50_95 == 0.4
    assert fake.train_kwargs is not None
    assert fake.train_kwargs["data"] == str(data_yaml)
    assert fake.train_kwargs["project"] == str(tmp_path / "runs")
    assert fake.train_kwargs["name"] == "train"
    assert fake.train_kwargs["cache"] == "ram"


def test_task_handle_progress_updates_from_epoch_callback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Trainer callback writes epoch progress into TaskHandle."""
    data_yaml = tmp_path / "data.yaml"
    write_data_yaml(data_yaml)
    model = tmp_path / "model.pt"
    model.write_bytes(b"model")
    handle = make_task_handle()
    fake = FakeYOLO(tmp_path / "runs" / "train")
    monkeypatch.setattr("core.trainer._load_yolo_model", lambda base_model: fake)

    Trainer(task_handle=handle).train(
        TrainConfig(data_yaml=data_yaml, base_model=model, output_dir=tmp_path / "runs", epochs=3, batch_size=2)
    )

    assert handle.progress_current == 1
    assert handle.progress_total == 3
    assert "Epoch 1/3" in handle.progress_message


def test_cancelled_task_raises_train_interrupted(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cancellation before training raises TrainInterruptedError."""
    data_yaml = tmp_path / "data.yaml"
    write_data_yaml(data_yaml)
    model = tmp_path / "model.pt"
    model.write_bytes(b"model")
    monkeypatch.setattr("core.trainer._load_yolo_model", lambda base_model: FakeYOLO(tmp_path / "runs" / "train"))

    with pytest.raises(TrainInterruptedError):
        Trainer(task_handle=make_task_handle(cancelled=True)).train(
            TrainConfig(data_yaml=data_yaml, base_model=model, output_dir=tmp_path / "runs")
        )


def test_oom_runtime_error_raises_train_oom(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """CUDA out-of-memory errors map to TrainOOMError."""
    data_yaml = tmp_path / "data.yaml"
    write_data_yaml(data_yaml)
    model = tmp_path / "model.pt"
    model.write_bytes(b"model")
    fake = FakeYOLO(tmp_path / "runs" / "train", error=RuntimeError("CUDA out of memory"))
    monkeypatch.setattr("core.trainer._load_yolo_model", lambda base_model: fake)

    with pytest.raises(TrainOOMError):
        Trainer().train(TrainConfig(data_yaml=data_yaml, base_model=model, output_dir=tmp_path / "runs"))
