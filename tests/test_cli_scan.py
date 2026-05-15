"""Tests for the JSON CLI scan adapter."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from PIL import Image

from cli.main import run


def make_image(path: Path) -> None:
    """Create a tiny image fixture."""
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (32, 32), color=(128, 128, 128)).save(path)


def test_cli_scan_outputs_success_json(tmp_path: Path, capsys: object) -> None:
    """Scan command reads JSON input and writes a stable JSON response."""
    site = tmp_path / "site"
    make_image(site / "CodeA" / "Product1" / "a1.jpg")
    request_path = tmp_path / "scan.json"
    request_path.write_text(
        json.dumps(
            {
                "siteFolder": str(site),
                "taskDir": str(tmp_path / "tasks"),
            }
        ),
        encoding="utf-8",
    )

    exit_code = run(["scan", str(request_path)])

    assert exit_code == 0
    output = json.loads(capsys.readouterr().out)
    assert output["success"] is True
    assert output["task"]["status"] == "succeeded"
    assert output["result"]["statistics"]["totalImages"] == 1
    assert output["result"]["mappingPath"].endswith(".autolabeler/mapping.json")


def test_cli_scan_outputs_error_json(tmp_path: Path, capsys: object) -> None:
    """Scan command reports business failures as JSON and non-zero exit code."""
    request_path = tmp_path / "scan.json"
    request_path.write_text(
        json.dumps(
            {
                "siteFolder": str(tmp_path / "missing"),
                "taskDir": str(tmp_path / "tasks"),
            }
        ),
        encoding="utf-8",
    )

    exit_code = run(["scan", str(request_path)])

    assert exit_code == 1
    output = json.loads(capsys.readouterr().out)
    assert output["success"] is False
    assert output["task"]["status"] == "failed"
    assert output["error"]["code"] == "SCAN_PATH_NOT_FOUND"


def test_cli_scan_module_entrypoint_outputs_json(tmp_path: Path) -> None:
    """Node-style subprocess callers can run the CLI module."""
    site = tmp_path / "site"
    make_image(site / "CodeA" / "Product1" / "a1.jpg")
    request_path = tmp_path / "scan.json"
    request_path.write_text(
        json.dumps(
            {
                "siteFolder": str(site),
                "taskDir": str(tmp_path / "tasks"),
            }
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [sys.executable, "-m", "cli.main", "scan", str(request_path)],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    output = json.loads(result.stdout)
    assert output["success"] is True
    assert output["result"]["statistics"]["totalImages"] == 1
