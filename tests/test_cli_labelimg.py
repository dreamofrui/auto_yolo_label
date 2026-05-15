"""Tests for the JSON CLI LabelImg adapter."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from cli.main import run


def write_request(path: Path, payload: dict[str, object]) -> None:
    """Write one JSON request file."""
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_cli_labelimg_validate_outputs_probe_json(
    tmp_path: Path, capsys: object
) -> None:
    """Validate command returns a non-throwing environment probe result."""
    request_path = tmp_path / "request.json"
    missing_python = tmp_path / "missing-python.exe"
    write_request(
        request_path,
        {
            "pythonPath": str(missing_python),
            "taskDir": str(tmp_path / "tasks"),
        },
    )

    exit_code = run(["labelimg", "validate", str(request_path)])

    assert exit_code == 0
    output = json.loads(capsys.readouterr().out)
    assert output["success"] is True
    assert output["task"]["status"] == "succeeded"
    assert output["result"]["isValid"] is False
    assert output["result"]["pythonVersion"] == ""
    assert str(missing_python) in output["result"]["errorMessage"]


def test_cli_labelimg_validate_outputs_error_json(
    tmp_path: Path, capsys: object
) -> None:
    """Validate command reports invalid request JSON as an error payload."""
    request_path = tmp_path / "request.json"
    write_request(request_path, {"taskDir": str(tmp_path / "tasks")})

    exit_code = run(["labelimg", "validate", str(request_path)])

    assert exit_code == 1
    output = json.loads(capsys.readouterr().out)
    assert output["success"] is False
    assert output["task"] is None
    assert output["error"]["code"] == "VALIDATION_ERROR"


def test_cli_labelimg_validate_module_entrypoint_outputs_json(tmp_path: Path) -> None:
    """Node-style subprocess callers can run the LabelImg validate command."""
    request_path = tmp_path / "request.json"
    write_request(
        request_path,
        {
            "pythonPath": str(tmp_path / "missing-python.exe"),
            "taskDir": str(tmp_path / "tasks"),
        },
    )

    result = subprocess.run(
        [sys.executable, "-m", "cli.main", "labelimg", "validate", str(request_path)],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    output = json.loads(result.stdout)
    assert output["success"] is True
    assert output["result"]["isValid"] is False
