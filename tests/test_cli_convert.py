"""Tests for the JSON CLI convert adapter."""

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


def write_request(path: Path, payload: dict[str, object]) -> None:
    """Write one JSON request file."""
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_cli_convert_txt_to_xml_outputs_success_json(
    tmp_path: Path, capsys: object
) -> None:
    """TXT-to-XML command returns conversion counters."""
    labels = tmp_path / "labels"
    make_image(labels / "a.jpg")
    (labels / "a.txt").write_text("0 0.5 0.5 0.5 0.5", encoding="utf-8")
    request_path = tmp_path / "request.json"
    write_request(
        request_path,
        {
            "folder": str(labels),
            "taskDir": str(tmp_path / "tasks"),
            "recursive": False,
            "classes": ["Product1"],
        },
    )

    exit_code = run(["convert", "txt-to-xml", str(request_path)])

    assert exit_code == 0
    output = json.loads(capsys.readouterr().out)
    assert output["success"] is True
    assert output["task"]["status"] == "succeeded"
    assert output["result"]["total"] == 1
    assert output["result"]["success"] == 1
    assert (labels / "a.xml").exists()


def test_cli_convert_xml_to_txt_outputs_error_json(
    tmp_path: Path, capsys: object
) -> None:
    """XML-to-TXT command reports converter business errors as JSON."""
    request_path = tmp_path / "request.json"
    write_request(
        request_path,
        {
            "xmlPath": str(tmp_path / "missing.xml"),
            "outputPath": str(tmp_path / "out.txt"),
            "taskDir": str(tmp_path / "tasks"),
            "classes": [],
        },
    )

    exit_code = run(["convert", "xml-to-txt", str(request_path)])

    assert exit_code == 1
    output = json.loads(capsys.readouterr().out)
    assert output["success"] is False
    assert output["task"]["status"] == "failed"
    assert output["error"]["code"] == "CONVERT_CLASSES_NOT_FOUND"


def test_cli_convert_module_entrypoint_outputs_json(tmp_path: Path) -> None:
    """Node-style subprocess callers can run the convert command."""
    labels = tmp_path / "labels"
    make_image(labels / "a.jpg")
    (labels / "a.txt").write_text("0 0.5 0.5 0.5 0.5", encoding="utf-8")
    request_path = tmp_path / "request.json"
    write_request(
        request_path,
        {
            "folder": str(labels),
            "taskDir": str(tmp_path / "tasks"),
            "recursive": False,
            "classes": ["Product1"],
        },
    )

    result = subprocess.run(
        [sys.executable, "-m", "cli.main", "convert", "txt-to-xml", str(request_path)],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    output = json.loads(result.stdout)
    assert output["success"] is True
    assert output["result"]["success"] == 1
