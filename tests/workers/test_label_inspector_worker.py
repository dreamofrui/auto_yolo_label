"""Tests for desktop label inspector worker adapter."""

from __future__ import annotations

from pathlib import Path

from core.label_inspector import GetRunTreeConfig, ListRunsConfig
from gui.workers.label_inspector_worker import LabelInspectorWorker
from utils.task_registry import TaskRegistry


def make_label(path: Path, text: str = "") -> None:
    """Create one label file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_label_inspector_worker_lists_runs_and_updates_task(tmp_path: Path) -> None:
    """Desktop inspector worker is a thin adapter over the shared service."""
    site = tmp_path / "site"
    (site / ".autolabeler" / "inference_results" / "run_20260513_104000").mkdir(
        parents=True
    )
    registry = TaskRegistry(tmp_path / "tasks")

    outcome = LabelInspectorWorker(registry=registry).list_runs(
        ListRunsConfig(site_folder=site)
    )

    assert outcome.success is True
    assert outcome.result is not None
    assert isinstance(outcome.result, list)
    assert outcome.result[0].run_id == "run_20260513_104000"
    assert registry.get(outcome.task.task_id).status == "succeeded"


def test_label_inspector_worker_converts_errors_to_failed_task(tmp_path: Path) -> None:
    """Desktop inspector worker records business failures on the shared registry."""
    registry = TaskRegistry(tmp_path / "tasks")

    outcome = LabelInspectorWorker(registry=registry).get_run_tree(
        GetRunTreeConfig(site_folder=tmp_path / "site", run_id="missing")
    )

    assert outcome.success is False
    assert outcome.error is not None
    assert outcome.error.code == "INSPECTOR_RUN_NOT_FOUND"
    assert registry.get(outcome.task.task_id).status == "failed"
