"""Tests for the JSON CLI restore adapter."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from PIL import Image

from cli.main import run
from core.scanner import ScanConfig, Scanner
from utils.path_encoder import PathEncoder


def make_image(path: Path) -> None:
    """Create a tiny image fixture."""
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (32, 32), color=(128, 128, 128)).save(path)


def make_scanned_site(site: Path) -> str:
    """Create a site with one scanned image and return its encoded stem."""
    make_image(site / "CodeA" / "Product1" / "a.jpg")
    Scanner().scan(ScanConfig(site_folder=site))
    return Path(PathEncoder().encode("CodeA", "Product1", "a.jpg")).stem


def write_request(path: Path, payload: dict[str, object]) -> None:
    """Write one JSON request file."""
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_cli_restore_outputs_success_json(tmp_path: Path, capsys: object) -> None:
    """Restore command returns copy counters and updates source labels."""
    site = tmp_path / "site"
    database_dir = tmp_path / "database"
    encoded_stem = make_scanned_site(site)
    label_path = database_dir / "labels" / "train" / f"{encoded_stem}.txt"
    label_path.parent.mkdir(parents=True, exist_ok=True)
    label_path.write_text("0 0.5 0.5 0.2 0.2\n", encoding="utf-8")
    request_path = tmp_path / "request.json"
    write_request(
        request_path,
        {
            "siteFolder": str(site),
            "sourceType": "database",
            "databaseDir": str(database_dir),
            "taskDir": str(tmp_path / "tasks"),
        },
    )

    exit_code = run(["restore", str(request_path)])

    assert exit_code == 0
    output = json.loads(capsys.readouterr().out)
    assert output["success"] is True
    assert output["task"]["status"] == "succeeded"
    assert output["result"]["total"] == 1
    assert output["result"]["success"] == 1
    assert (site / "CodeA" / "Product1" / "a.txt").exists()


def test_cli_restore_outputs_error_json(tmp_path: Path, capsys: object) -> None:
    """Restore command reports business errors as JSON."""
    request_path = tmp_path / "request.json"
    write_request(
        request_path,
        {
            "siteFolder": str(tmp_path / "site"),
            "sourceType": "database",
            "databaseDir": str(tmp_path / "database"),
            "taskDir": str(tmp_path / "tasks"),
        },
    )

    exit_code = run(["restore", str(request_path)])

    assert exit_code == 1
    output = json.loads(capsys.readouterr().out)
    assert output["success"] is False
    assert output["task"]["status"] == "failed"
    assert output["error"]["code"] == "RESTORE_MAPPING_NOT_FOUND"


def test_cli_restore_module_entrypoint_outputs_json(tmp_path: Path) -> None:
    """Node-style subprocess callers can run the restore command."""
    site = tmp_path / "site"
    database_dir = tmp_path / "database"
    encoded_stem = make_scanned_site(site)
    label_path = database_dir / "labels" / "train" / f"{encoded_stem}.txt"
    label_path.parent.mkdir(parents=True, exist_ok=True)
    label_path.write_text("0 0.5 0.5 0.2 0.2\n", encoding="utf-8")
    request_path = tmp_path / "request.json"
    write_request(
        request_path,
        {
            "siteFolder": str(site),
            "sourceType": "database",
            "databaseDir": str(database_dir),
            "taskDir": str(tmp_path / "tasks"),
        },
    )

    result = subprocess.run(
        [sys.executable, "-m", "cli.main", "restore", str(request_path)],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    output = json.loads(result.stdout)
    assert output["success"] is True
    assert output["result"]["success"] == 1
