"""Tests for shared service cancellation lifecycle handling."""

from __future__ import annotations

from pathlib import Path

from core.scanner import ScanConfig
from core.trainer import TrainConfig, TrainInterruptedError
from utils.exceptions import TaskCancelledError
from utils.task_registry import TaskHandle, TaskRegistry


class CancellingScanner:
    """Scanner test double that simulates core acknowledging cancellation."""

    def __init__(self, task_handle: TaskHandle) -> None:
        """Create the fake scanner with the service task handle."""
        self._task_handle = task_handle

    def scan(self, config: ScanConfig) -> object:
        """Raise the core cancellation exception."""
        raise TaskCancelledError("扫描任务已取消")


class InterruptedTrainer:
    """Trainer test double that simulates a cancelled training backend."""

    def __init__(self, task_handle: TaskHandle) -> None:
        """Create the fake trainer with the service task handle."""
        self._task_handle = task_handle

    def train(self, config: TrainConfig) -> object:
        """Raise the trainer cancellation exception."""
        raise TrainInterruptedError("训练已取消")


def test_scan_service_records_cancelled_task(
    tmp_path: Path, monkeypatch: object
) -> None:
    """TaskCancelledError marks shared service tasks as cancelled."""
    from api.services import scan_service

    registry = TaskRegistry(tmp_path / "tasks")
    monkeypatch.setattr(scan_service, "Scanner", CancellingScanner)

    outcome = scan_service.run_scan(ScanConfig(site_folder=tmp_path), registry)

    task = registry.get(outcome.task.task_id)
    assert outcome.success is False
    assert outcome.error is not None
    assert task.status == "cancelled"
    assert task.error is None
    assert task.is_cancel_requested is True


def test_train_service_records_interrupted_task(
    tmp_path: Path, monkeypatch: object
) -> None:
    """TrainInterruptedError marks shared service tasks as cancelled."""
    from api.services import train_service

    registry = TaskRegistry(tmp_path / "tasks")
    monkeypatch.setattr(train_service, "Trainer", InterruptedTrainer)

    outcome = train_service.run_train(
        TrainConfig(
            data_yaml=tmp_path / "data.yaml",
            base_model=tmp_path / "base.pt",
            output_dir=tmp_path / "runs",
        ),
        registry,
    )

    task = registry.get(outcome.task.task_id)
    assert outcome.success is False
    assert outcome.error is not None
    assert task.status == "cancelled"
    assert task.error is None
    assert task.is_cancel_requested is True
