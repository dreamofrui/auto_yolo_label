"""Desktop LabelImg worker adapter."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from api.services.labelimg_service import launch_labelimg, validate_labelimg
from core.labelimg_launcher import (
    LabelImgConfig,
    LabelImgLaunchResult,
    LabelImgLauncher,
    LabelImgValidateConfig,
    LabelImgValidateResult,
)
from utils.exceptions import ErrorInfo
from utils.task_registry import TaskHandle, TaskRegistry


@dataclass(frozen=True)
class LabelImgWorkerOutcome:
    """Desktop LabelImg worker outcome."""

    success: bool
    task: TaskHandle
    result: LabelImgValidateResult | LabelImgLaunchResult | None
    error: ErrorInfo | None


class LabelImgWorker:
    """Thin desktop adapter for LabelImgLauncher operations."""

    def __init__(
        self,
        registry: TaskRegistry | None = None,
        launcher: LabelImgLauncher | None = None,
    ) -> None:
        """Create a LabelImg worker with optional dependencies."""
        self._registry = registry or TaskRegistry(
            Path.home() / ".autolabeler" / "tasks"
        )
        self._launcher = launcher

    def validate(self, config: LabelImgValidateConfig) -> LabelImgWorkerOutcome:
        """Validate LabelImg and return a desktop-friendly outcome."""
        outcome = validate_labelimg(config, self._registry, self._launcher)
        return LabelImgWorkerOutcome(
            success=outcome.success,
            task=outcome.task,
            result=outcome.result,
            error=None if outcome.error is None else outcome.error.to_error_info(),
        )

    def launch(self, config: LabelImgConfig) -> LabelImgWorkerOutcome:
        """Launch LabelImg and return a desktop-friendly outcome."""
        outcome = launch_labelimg(config, self._registry, self._launcher)
        return LabelImgWorkerOutcome(
            success=outcome.success,
            task=outcome.task,
            result=outcome.result,
            error=None if outcome.error is None else outcome.error.to_error_info(),
        )
