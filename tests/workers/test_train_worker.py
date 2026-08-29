"""Tests for the desktop train worker adapter."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from core.trainer import TrainConfig
from gui.workers.train_worker import TrainWorker
from utils.task_registry import TaskRegistry


@dataclass
class FakeTrainerState:
    """Minimal Ultralytics trainer-like callback state."""

    epoch: int
    epochs: int
    metrics: dict[str, float]


class FakeYOLO:
    """Small fake model that writes YOLO training outputs."""

    progress_probe: Any = None

    def __init__(self) -> None:
        """Create a fake model with callback storage."""
        self.callbacks: dict[str, list[Any]] = {}

    def add_callback(self, event: str, callback: Any) -> None:
        """Store a callback for later simulation."""
        self.callbacks.setdefault(event, []).append(callback)

    def train(self, **kwargs: Any) -> object:
        """Simulate an Ultralytics training run."""
        run_dir = Path(str(kwargs["project"])) / str(kwargs["name"])
        for callback in self.callbacks.get("on_fit_epoch_end", []):
            callback(
                FakeTrainerState(
                    epoch=0, epochs=int(kwargs["epochs"]), metrics={"mAP50": 0.5}
                )
            )
            if self.progress_probe is not None:
                self.progress_probe()
        weights_dir = run_dir / "weights"
        weights_dir.mkdir(parents=True, exist_ok=True)
        (weights_dir / "best.pt").write_bytes(b"best")
        (weights_dir / "last.pt").write_bytes(b"last")
        (run_dir / "results.csv").write_text(
            "epoch,metrics/mAP50(B),metrics/mAP50-95(B)\n0,0.5,0.25\n1,0.7,0.4\n",
            encoding="utf-8",
        )
        return object()


def write_data_yaml(path: Path) -> None:
    """Write a minimal valid YOLO dataset and data.yaml."""
    path.parent.mkdir(parents=True, exist_ok=True)
    (path.parent / "images" / "train").mkdir(parents=True)
    (path.parent / "images" / "val").mkdir(parents=True)
    (path.parent / "labels" / "train").mkdir(parents=True)
    (path.parent / "labels" / "val").mkdir(parents=True)
    (path.parent / "images" / "train" / "train1.jpg").write_bytes(b"image")
    (path.parent / "images" / "val" / "val1.jpg").write_bytes(b"image")
    (path.parent / "labels" / "train" / "train1.txt").write_text(
        "0 0.5 0.5 0.2 0.2\n", encoding="utf-8"
    )
    (path.parent / "labels" / "val" / "val1.txt").write_text(
        "0 0.5 0.5 0.2 0.2\n", encoding="utf-8"
    )
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


def test_train_worker_runs_core_train_and_updates_task(
    tmp_path: Path, monkeypatch: Any
) -> None:
    """Desktop train worker is a thin adapter over the shared train service."""
    data_yaml = tmp_path / "database" / "data.yaml"
    write_data_yaml(data_yaml)
    base_model = tmp_path / "base.pt"
    base_model.write_bytes(b"model")
    registry = TaskRegistry(task_dir=tmp_path / "tasks")
    monkeypatch.setattr("core.trainer._load_yolo_model", lambda base_model: FakeYOLO())

    outcome = TrainWorker(registry=registry).run(
        TrainConfig(
            data_yaml=data_yaml,
            base_model=base_model,
            output_dir=tmp_path / "runs",
            run_name="train",
            epochs=2,
            batch_size=1,
            device="cpu",
        )
    )

    assert outcome.success is True
    assert outcome.result is not None
    assert outcome.result.best_model.name == "best.pt"
    assert outcome.result.log_file is not None
    assert outcome.result.preflight["train_images"] == 1
    assert outcome.result.metrics.best_map50 == 0.7
    assert registry.get(outcome.task.task_id).status == "succeeded"
    stored = registry.get(outcome.task.task_id).result
    assert stored is not None
    assert stored["log_file"].endswith("results.csv")
    assert stored["preflight"]["classes"] == ["CodeA"]


def test_train_worker_persists_epoch_progress_before_completion(
    tmp_path: Path, monkeypatch: Any
) -> None:
    """Desktop training persists epoch progress while the task is running."""
    data_yaml = tmp_path / "database" / "data.yaml"
    write_data_yaml(data_yaml)
    base_model = tmp_path / "base.pt"
    base_model.write_bytes(b"model")
    registry = TaskRegistry(task_dir=tmp_path / "tasks")
    observed: list[tuple[int, int, str]] = []

    def make_fake_model(base_model: Path) -> FakeYOLO:
        del base_model
        fake = FakeYOLO()

        def probe() -> None:
            tasks = registry.list_tasks()
            assert len(tasks) == 1
            task = tasks[0]
            observed.append(
                (task.progress_current, task.progress_total, task.progress_message)
            )

        fake.progress_probe = probe
        return fake

    monkeypatch.setattr("core.trainer._load_yolo_model", make_fake_model)

    outcome = TrainWorker(registry=registry).run(
        TrainConfig(
            data_yaml=data_yaml,
            base_model=base_model,
            output_dir=tmp_path / "runs",
            run_name="train",
            epochs=2,
            batch_size=1,
            device="cpu",
        )
    )

    assert outcome.success is True
    assert observed
    assert observed[0][0:2] == (1, 2)
    assert "Epoch 1/2" in observed[0][2]


def test_train_worker_converts_errors_to_failed_task(tmp_path: Path) -> None:
    """Desktop train worker records business failures on the shared registry."""
    data_yaml = tmp_path / "database" / "data.yaml"
    write_data_yaml(data_yaml)
    registry = TaskRegistry(task_dir=tmp_path / "tasks")

    outcome = TrainWorker(registry=registry).run(
        TrainConfig(
            data_yaml=data_yaml,
            base_model=tmp_path / "missing.pt",
            output_dir=tmp_path / "runs",
            epochs=2,
            batch_size=1,
            device="cpu",
        )
    )

    assert outcome.success is False
    assert outcome.error is not None
    assert outcome.error.code == "TRAIN_BASE_MODEL_NOT_FOUND"
    assert registry.get(outcome.task.task_id).status == "failed"
