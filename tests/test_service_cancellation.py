"""Tests for desktop worker cancellation lifecycle handling."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from core.scanner import ScanConfig
from core.trainer import TrainConfig, TrainInterruptedError
from gui.workers import scan_worker, train_worker
from gui.workers.scan_worker import ScanWorker
from gui.workers.train_worker import TrainWorker
from utils.exceptions import TaskCancelledError
from utils.task_registry import TaskHandle, TaskRegistry


class CancellingScanner:
    """Scanner test double that simulates core acknowledging cancellation."""

    def __init__(self, task_handle: TaskHandle) -> None:
        """Create the fake scanner with the worker task handle."""
        self._task_handle = task_handle

    def scan(self, config: ScanConfig) -> object:
        """Raise the core cancellation exception."""
        del config
        raise TaskCancelledError("cancelled")


class InterruptedTrainer:
    """Trainer test double that simulates a cancelled training backend."""

    def __init__(self, task_handle: TaskHandle, progress_callback=None) -> None:
        """Create the fake trainer with the worker task handle."""
        self._task_handle = task_handle
        self._progress_callback = progress_callback

    def train(self, config: TrainConfig) -> object:
        """Raise the trainer cancellation exception."""
        del config
        raise TrainInterruptedError("interrupted")


def test_scan_worker_records_cancelled_task(
    tmp_path: Path, monkeypatch: Any
) -> None:
    """TaskCancelledError marks desktop worker tasks as cancelled."""
    registry = TaskRegistry(tmp_path / "tasks")
    monkeypatch.setattr(scan_worker, "Scanner", CancellingScanner)

    outcome = ScanWorker(registry=registry).run(ScanConfig(site_folder=tmp_path))

    task = registry.get(outcome.task.task_id)
    assert outcome.success is False
    assert outcome.error is not None
    assert outcome.error.code == "TASK_CANCELLED"
    assert task.status == "cancelled"
    assert task.error is None
    assert task.is_cancel_requested is True


def test_train_worker_records_interrupted_task(
    tmp_path: Path, monkeypatch: Any
) -> None:
    """TrainInterruptedError marks desktop worker tasks as cancelled."""
    registry = TaskRegistry(tmp_path / "tasks")
    monkeypatch.setattr(train_worker, "Trainer", InterruptedTrainer)

    outcome = TrainWorker(registry=registry).run(
        TrainConfig(
            data_yaml=tmp_path / "data.yaml",
            base_model=tmp_path / "base.pt",
            output_dir=tmp_path / "runs",
        )
    )

    task = registry.get(outcome.task.task_id)
    assert outcome.success is False
    assert outcome.error is not None
    assert outcome.error.code == "TRAIN_INTERRUPTED"
    assert task.status == "cancelled"
    assert task.error is None
    assert task.is_cancel_requested is True
