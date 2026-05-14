"""Tests for desktop LabelImg worker adapter."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from core.labelimg_launcher import LabelImgConfig, LabelImgLaunchResult, LabelImgValidateConfig, LabelImgValidateResult
from gui.workers.labelimg_worker import LabelImgWorker
from utils.task_registry import TaskRegistry


@dataclass
class FakeLauncher:
    """Fake launcher for worker tests."""

    validate_result: LabelImgValidateResult = LabelImgValidateResult(
        is_valid=True,
        labelimg_version="labelImg 1.8.6",
        python_version="Python 3.11.14",
        error_message=None,
    )
    launch_result: LabelImgLaunchResult = LabelImgLaunchResult(process_id=1234, command="python -m labelImg")

    def validate(self, config: LabelImgValidateConfig) -> LabelImgValidateResult:
        """Return a configured validation result."""
        return self.validate_result

    def launch(self, config: LabelImgConfig) -> LabelImgLaunchResult:
        """Return a configured launch result."""
        return self.launch_result


def make_python(path: Path) -> Path:
    """Create a fake Python executable file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("python", encoding="utf-8")
    return path


def test_labelimg_worker_validates_environment_and_updates_task(tmp_path: Path) -> None:
    """Desktop LabelImg worker validates through the shared service."""
    registry = TaskRegistry(tmp_path / "tasks")
    python_path = make_python(tmp_path / "python.exe")

    outcome = LabelImgWorker(registry=registry, launcher=FakeLauncher()).validate(
        LabelImgValidateConfig(python_path=python_path)
    )

    assert outcome.success is True
    assert outcome.result is not None
    assert outcome.result.is_valid is True
    assert registry.get(outcome.task.task_id).status == "succeeded"


def test_labelimg_worker_launches_and_updates_task(tmp_path: Path) -> None:
    """Desktop LabelImg worker launches through the shared service."""
    registry = TaskRegistry(tmp_path / "tasks")
    python_path = make_python(tmp_path / "python.exe")
    image_dir = tmp_path / "images"
    image_dir.mkdir()

    outcome = LabelImgWorker(registry=registry, launcher=FakeLauncher()).launch(
        LabelImgConfig(python_path=python_path, image_dir=image_dir)
    )

    assert outcome.success is True
    assert outcome.result is not None
    assert outcome.result.process_id == 1234
    assert registry.get(outcome.task.task_id).status == "succeeded"


def test_labelimg_worker_converts_launch_errors_to_failed_task(tmp_path: Path) -> None:
    """Desktop LabelImg worker records business failures on the shared registry."""
    registry = TaskRegistry(tmp_path / "tasks")

    outcome = LabelImgWorker(registry=registry).launch(
        LabelImgConfig(python_path=tmp_path / "missing.exe", image_dir=tmp_path / "images")
    )

    assert outcome.success is False
    assert outcome.error is not None
    assert outcome.error.code == "LABELIMG_PYTHON_NOT_FOUND"
    assert registry.get(outcome.task.task_id).status == "failed"
