"""Tests for the JSON CLI train adapter."""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from cli.main import run


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
        """Simulate a short Ultralytics training run."""
        run_dir = Path(str(kwargs["project"])) / str(kwargs["name"])
        for callback in self.callbacks.get("on_fit_epoch_end", []):
            callback(
                FakeTrainerState(
                    epoch=0,
                    epochs=int(kwargs["epochs"]),
                    metrics={"mAP50": 0.5},
                )
            )
        weights_dir = run_dir / "weights"
        weights_dir.mkdir(parents=True, exist_ok=True)
        (weights_dir / "best.pt").write_bytes(b"best")
        (weights_dir / "last.pt").write_bytes(b"last")
        (run_dir / "results.csv").write_text(
            "epoch,metrics/mAP50(B),metrics/mAP50-95(B)\n0,0.5,0.25\n",
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


def write_request(path: Path, payload: dict[str, object]) -> None:
    """Write one JSON request file."""
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_cli_train_outputs_success_json(
    tmp_path: Path, capsys: object, monkeypatch: Any
) -> None:
    """Train command returns model paths and metrics without owning training logic."""
    data_yaml = tmp_path / "database" / "data.yaml"
    write_data_yaml(data_yaml)
    base_model = tmp_path / "base.pt"
    base_model.write_bytes(b"model")
    monkeypatch.setattr("core.trainer._load_yolo_model", lambda base_model: FakeYOLO())
    request_path = tmp_path / "request.json"
    write_request(
        request_path,
        {
            "dataYaml": str(data_yaml),
            "baseModel": str(base_model),
            "outputDir": str(tmp_path / "runs"),
            "taskDir": str(tmp_path / "tasks"),
            "epochs": 1,
            "batchSize": 1,
            "device": "cpu",
        },
    )

    exit_code = run(["train", str(request_path)])

    assert exit_code == 0
    output = json.loads(capsys.readouterr().out)
    assert output["success"] is True
    assert output["task"]["status"] == "succeeded"
    assert output["result"]["bestModel"].endswith("best.pt")
    assert output["result"]["lastModel"].endswith("last.pt")
    assert output["result"]["metrics"]["bestMap50"] == 0.5
    assert output["result"]["effectiveConfig"]["batch_size"] == 1


def test_cli_train_outputs_error_json(tmp_path: Path, capsys: object) -> None:
    """Train command reports trainer business errors as JSON."""
    data_yaml = tmp_path / "database" / "data.yaml"
    write_data_yaml(data_yaml)
    request_path = tmp_path / "request.json"
    write_request(
        request_path,
        {
            "dataYaml": str(data_yaml),
            "baseModel": str(tmp_path / "missing.pt"),
            "outputDir": str(tmp_path / "runs"),
            "taskDir": str(tmp_path / "tasks"),
            "epochs": 1,
            "batchSize": 1,
            "device": "cpu",
        },
    )

    exit_code = run(["train", str(request_path)])

    assert exit_code == 1
    output = json.loads(capsys.readouterr().out)
    assert output["success"] is False
    assert output["task"]["status"] == "failed"
    assert output["error"]["code"] == "TRAIN_BASE_MODEL_NOT_FOUND"


def test_cli_train_module_entrypoint_reports_validation_json(tmp_path: Path) -> None:
    """Node-style subprocess callers can run the train command."""
    data_yaml = tmp_path / "database" / "data.yaml"
    write_data_yaml(data_yaml)
    request_path = tmp_path / "request.json"
    write_request(
        request_path,
        {
            "dataYaml": str(data_yaml),
            "baseModel": str(tmp_path / "missing.pt"),
            "outputDir": str(tmp_path / "runs"),
            "taskDir": str(tmp_path / "tasks"),
            "epochs": 1,
            "batchSize": 1,
            "device": "cpu",
        },
    )

    result = subprocess.run(
        [sys.executable, "-m", "cli.main", "train", str(request_path)],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    output = json.loads(result.stdout)
    assert output["success"] is False
    assert output["error"]["code"] == "TRAIN_BASE_MODEL_NOT_FOUND"
