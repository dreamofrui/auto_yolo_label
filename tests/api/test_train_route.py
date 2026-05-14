"""Tests for the train HTTP route."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from api.main import create_app
from utils.task_registry import TaskRegistry


@dataclass
class FakeTrainerState:
    """Minimal Ultralytics trainer-like callback state."""

    epoch: int
    epochs: int
    metrics: dict[str, float]


class FakeYOLO:
    """Small fake model that writes YOLO training outputs."""

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


def test_train_route_returns_task_result_and_metrics(
    tmp_path: Path, monkeypatch: Any
) -> None:
    """HTTP train route converts camelCase JSON to core TrainConfig and back."""
    data_yaml = tmp_path / "database" / "data.yaml"
    write_data_yaml(data_yaml)
    base_model = tmp_path / "base.pt"
    base_model.write_bytes(b"model")
    output_dir = tmp_path / "runs"
    registry = TaskRegistry(task_dir=tmp_path / "tasks")
    client = TestClient(create_app(task_registry=registry))
    monkeypatch.setattr("core.trainer._load_yolo_model", lambda base_model: FakeYOLO())

    response = client.post(
        "/api/train",
        json={
            "dataYaml": str(data_yaml),
            "baseModel": str(base_model),
            "outputDir": str(output_dir),
            "epochs": 2,
            "batchSize": 1,
            "device": "cpu",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["task"]["status"] == "succeeded"
    assert payload["result"]["bestModel"].replace("\\", "/").endswith("weights/best.pt")
    assert payload["result"]["metrics"]["bestMap50"] == 0.7
    assert payload["result"]["metrics"]["finalMap5095"] == 0.4
    assert registry.get(payload["task"]["taskId"]).status == "succeeded"


def test_train_route_maps_missing_base_model_to_json_error(tmp_path: Path) -> None:
    """Trainer business errors become stable JSON error responses."""
    data_yaml = tmp_path / "database" / "data.yaml"
    write_data_yaml(data_yaml)
    registry = TaskRegistry(task_dir=tmp_path / "tasks")
    client = TestClient(create_app(task_registry=registry))

    response = client.post(
        "/api/train",
        json={
            "dataYaml": str(data_yaml),
            "baseModel": str(tmp_path / "missing.pt"),
            "outputDir": str(tmp_path / "runs"),
            "epochs": 2,
            "batchSize": 1,
            "device": "cpu",
        },
    )

    assert response.status_code == 400
    payload = response.json()
    assert payload["success"] is False
    assert payload["error"]["code"] == "TRAIN_BASE_MODEL_NOT_FOUND"
