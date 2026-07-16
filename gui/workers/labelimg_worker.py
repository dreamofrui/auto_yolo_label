"""Desktop LabelImg worker adapter."""

from __future__ import annotations

import os
from dataclasses import dataclass

from core.labelimg_launcher import (
    LabelImgConfig,
    LabelImgLaunchResult,
    LabelImgLauncher,
    LabelImgValidateConfig,
    LabelImgValidateResult,
)
from gui.workers._task_lifecycle import (
    default_task_registry,
    finish_worker_error,
    finish_worker_success,
    start_worker_task,
)
from utils.exceptions import AutoLabelerError, ErrorInfo
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
        self._registry = registry or default_task_registry()
        self._launcher = launcher

    def validate(self, config: LabelImgValidateConfig) -> LabelImgWorkerOutcome:
        """Validate LabelImg and return a desktop-friendly outcome."""
        task = start_worker_task(self._registry, "labelimg", "验证 LabelImg 环境")
        try:
            result = (self._launcher or _default_launcher()).validate(config)
        except AutoLabelerError as exc:
            error = finish_worker_error(self._registry, task, exc)
            return LabelImgWorkerOutcome(False, task, None, error)
        finish_worker_success(self._registry, task, result)
        return LabelImgWorkerOutcome(True, task, result, None)

    def preflight(self, config: LabelImgConfig) -> LabelImgWorkerOutcome:
        """Preflight LabelImg launch inputs without starting LabelImg."""
        task = start_worker_task(self._registry, "labelimg", "预检 LabelImg 输入")
        try:
            result = (self._launcher or _default_launcher()).preflight(config)
        except AutoLabelerError as exc:
            error = finish_worker_error(self._registry, task, exc)
            return LabelImgWorkerOutcome(False, task, None, error)
        finish_worker_success(self._registry, task, result)
        return LabelImgWorkerOutcome(True, task, result, None)

    def launch(self, config: LabelImgConfig) -> LabelImgWorkerOutcome:
        """Launch LabelImg and return a desktop-friendly outcome."""
        task = start_worker_task(self._registry, "labelimg", "启动 LabelImg")
        try:
            result = (self._launcher or _default_launcher()).launch(config)
        except AutoLabelerError as exc:
            error = finish_worker_error(self._registry, task, exc)
            return LabelImgWorkerOutcome(False, task, None, error)
        finish_worker_success(self._registry, task, result)
        return LabelImgWorkerOutcome(True, task, result, None)


def _default_launcher() -> LabelImgLauncher:
    """Create the desktop launcher with the current process environment."""
    return LabelImgLauncher(environment=os.environ)
