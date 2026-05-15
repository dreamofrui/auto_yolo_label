"""Tests for the JSON CLI label-inspector adapters."""

from __future__ import annotations

import json
from pathlib import Path

from cli.main import run


def make_label(path: Path, text: str = "") -> None:
    """Create one label file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def make_image(path: Path) -> None:
    """Create a lightweight image placeholder."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"image")


def write_request(path: Path, payload: dict[str, str]) -> None:
    """Write one JSON request file."""
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_cli_inspect_list_runs_outputs_json(tmp_path: Path, capsys: object) -> None:
    """List-runs command returns inference run metadata."""
    site = tmp_path / "site"
    run_dir = site / ".autolabeler" / "inference_results" / "run_20260513_104000"
    run_dir.mkdir(parents=True)
    (run_dir / "inference_config.json").write_text(
        json.dumps({"run_id": "run_20260513_104000"}),
        encoding="utf-8",
    )
    request_path = tmp_path / "request.json"
    write_request(
        request_path,
        {"siteFolder": str(site), "taskDir": str(tmp_path / "tasks")},
    )

    exit_code = run(["inspect", "list-runs", str(request_path)])

    assert exit_code == 0
    output = json.loads(capsys.readouterr().out)
    assert output["success"] is True
    assert output["result"]["runs"][0]["runId"] == "run_20260513_104000"
    assert output["result"]["runs"][0]["configExists"] is True


def test_cli_inspect_run_tree_outputs_json(tmp_path: Path, capsys: object) -> None:
    """Run-tree command returns Code/Product label counts."""
    site = tmp_path / "site"
    product_dir = (
        site
        / ".autolabeler"
        / "inference_results"
        / "run_20260513_104000"
        / "CodeA"
        / "Product1"
    )
    make_label(product_dir / "one.txt", "0 0.5 0.5 0.2 0.2\n")
    make_label(product_dir / "two.txt", "\n")
    request_path = tmp_path / "request.json"
    write_request(
        request_path,
        {
            "siteFolder": str(site),
            "taskDir": str(tmp_path / "tasks"),
            "runId": "run_20260513_104000",
        },
    )

    exit_code = run(["inspect", "run-tree", str(request_path)])

    assert exit_code == 0
    output = json.loads(capsys.readouterr().out)
    assert output["result"]["nodes"][0]["code"] == "CodeA"
    assert output["result"]["nodes"][0]["labelCount"] == 2
    assert output["result"]["nodes"][0]["emptyCount"] == 1


def test_cli_inspect_product_labels_outputs_json(
    tmp_path: Path, capsys: object
) -> None:
    """Product-labels command returns label details and original image path."""
    site = tmp_path / "site"
    product_dir = (
        site
        / ".autolabeler"
        / "inference_results"
        / "run_20260513_104000"
        / "CodeA"
        / "Product1"
    )
    make_label(product_dir / "one.txt", "0 0.5 0.5 0.2 0.2\n")
    image_path = site / "CodeA" / "Product1" / "one.jpg"
    make_image(image_path)
    request_path = tmp_path / "request.json"
    write_request(
        request_path,
        {
            "siteFolder": str(site),
            "taskDir": str(tmp_path / "tasks"),
            "runId": "run_20260513_104000",
            "code": "CodeA",
            "product": "Product1",
        },
    )

    exit_code = run(["inspect", "product-labels", str(request_path)])

    assert exit_code == 0
    output = json.loads(capsys.readouterr().out)
    assert output["result"]["labels"][0]["imageName"] == "one.jpg"
    assert output["result"]["labels"][0]["imagePath"].endswith("one.jpg")
    assert output["result"]["labels"][0]["objectCount"] == 1


def test_cli_inspect_run_tree_outputs_error_json(
    tmp_path: Path, capsys: object
) -> None:
    """Inspect commands report business errors as JSON."""
    request_path = tmp_path / "request.json"
    write_request(
        request_path,
        {
            "siteFolder": str(tmp_path / "site"),
            "taskDir": str(tmp_path / "tasks"),
            "runId": "missing",
        },
    )

    exit_code = run(["inspect", "run-tree", str(request_path)])

    assert exit_code == 1
    output = json.loads(capsys.readouterr().out)
    assert output["success"] is False
    assert output["error"]["code"] == "INSPECTOR_RUN_NOT_FOUND"
