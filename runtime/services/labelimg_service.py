"""Shared LabelImg services for desktop and future CLI adapters."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TypeAlias

from core.labelimg_launcher import (
    LabelImgConfig,
    LabelImgLaunchResult,
    LabelImgLauncher,
    LabelImgValidateConfig,
    LabelImgValidateResult,
)
from runtime.services.common import finish_error_task
from utils.exceptions import AutoLabelerError
from utils.task_registry import TaskHandle, TaskRegistry

LabelImgResult: TypeAlias = LabelImgValidateResult | LabelImgLaunchResult


@dataclass(frozen=True)
class LabelImgServiceOutcome:
    """Result of a LabelImg adapter call."""

    success: bool
    task: TaskHandle
    result: LabelImgResult | None
    error: AutoLabelerError | None


def validate_labelimg(
    config: LabelImgValidateConfig,
    registry: TaskRegistry,
    launcher: LabelImgLauncher | None = None,
) -> LabelImgServiceOutcome:
    """Validate LabelImg environment with TaskRegistry lifecycle handling."""
    task = registry.create_task("labelimg")
    registry.start_task(task.task_id, message="Validating LabelImg")
    result = (launcher or LabelImgLauncher()).validate(config)
    registry.succeed_task(task.task_id, result=_validate_result_dict(result))
    return LabelImgServiceOutcome(success=True, task=task, result=result, error=None)


def launch_labelimg(
    config: LabelImgConfig,
    registry: TaskRegistry,
    launcher: LabelImgLauncher | None = None,
) -> LabelImgServiceOutcome:
    """Launch LabelImg with TaskRegistry lifecycle handling."""
    task = registry.create_task("labelimg")
    registry.start_task(task.task_id, message="Launching LabelImg")
    try:
        result = (launcher or LabelImgLauncher()).launch(config)
    except AutoLabelerError as exc:
        finish_error_task(registry, task, exc)
        return LabelImgServiceOutcome(success=False, task=task, result=None, error=exc)
    registry.succeed_task(task.task_id, result=_launch_result_dict(result))
    return LabelImgServiceOutcome(success=True, task=task, result=result, error=None)


def _validate_result_dict(result: LabelImgValidateResult) -> dict[str, object]:
    """Convert LabelImgValidateResult to a JSON-compatible dict."""
    return {
        "is_valid": result.is_valid,
        "labelimg_version": result.labelimg_version,
        "python_version": result.python_version,
        "error_message": result.error_message,
    }


def _launch_result_dict(result: LabelImgLaunchResult) -> dict[str, object]:
    """Convert LabelImgLaunchResult to a JSON-compatible dict."""
    return {"process_id": result.process_id, "command": result.command}
