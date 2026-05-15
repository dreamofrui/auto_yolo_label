"""Tests for the JSON CLI infer adapter."""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from cli.main import run


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
    """Create a lightweight image placeholder."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"image")


def write_request(path: Path, payload: dict[str, object]) -> None:
    """Write one JSON request file."""
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_cli_infer_outputs_success_json(
    tmp_path: Path, capsys: object, monkeypatch: Any
) -> None:
    """Infer command returns run metadata without owning prediction logic."""
    model_path = tmp_path / "best.pt"
    model_path.write_bytes(b"model")
    image_path = tmp_path / "custom" / "one.jpg"
    make_image(image_path)
    monkeypatch.setattr("core.inferencer._load_yolo_model", lambda path: FakeModel())
    monkeypatch.setattr("core.inferencer._run_id", lambda: "run_20260515_120000")
    request_path = tmp_path / "request.json"
    write_request(
        request_path,
        {
            "modelPath": str(model_path),
            "siteFolder": str(tmp_path / "site"),
            "outputBaseDir": str(tmp_path / "runs"),
            "taskDir": str(tmp_path / "tasks"),
            "imageSource": "custom",
            "customImages": [str(image_path)],
            "batchSize": 1,
            "device": "cpu",
        },
    )

    exit_code = run(["infer", str(request_path)])

    assert exit_code == 0
    output = json.loads(capsys.readouterr().out)
    assert output["success"] is True
    assert output["task"]["status"] == "succeeded"
    assert output["result"]["runId"] == "run_20260515_120000"
    assert output["result"]["statistics"]["processed"] == 1
    assert output["result"]["inferenceOutputDir"].endswith("run_20260515_120000")


def test_cli_infer_outputs_error_json(tmp_path: Path, capsys: object) -> None:
    """Infer command reports inferencer business errors as JSON."""
    request_path = tmp_path / "request.json"
    write_request(
        request_path,
        {
            "modelPath": str(tmp_path / "missing.pt"),
            "siteFolder": str(tmp_path / "site"),
            "taskDir": str(tmp_path / "tasks"),
            "imageSource": "custom",
            "customImages": [],
            "device": "cpu",
        },
    )

    exit_code = run(["infer", str(request_path)])

    assert exit_code == 1
    output = json.loads(capsys.readouterr().out)
    assert output["success"] is False
    assert output["task"]["status"] == "failed"
    assert output["error"]["code"] == "INFER_MODEL_NOT_FOUND"


def test_cli_infer_module_entrypoint_reports_validation_json(tmp_path: Path) -> None:
    """Node-style subprocess callers can run the infer command."""
    request_path = tmp_path / "request.json"
    write_request(
        request_path,
        {
            "modelPath": str(tmp_path / "missing.pt"),
            "siteFolder": str(tmp_path / "site"),
            "taskDir": str(tmp_path / "tasks"),
            "imageSource": "custom",
            "customImages": [],
            "device": "cpu",
        },
    )

    result = subprocess.run(
        [sys.executable, "-m", "cli.main", "infer", str(request_path)],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    output = json.loads(result.stdout)
    assert output["success"] is False
    assert output["error"]["code"] == "INFER_MODEL_NOT_FOUND"
