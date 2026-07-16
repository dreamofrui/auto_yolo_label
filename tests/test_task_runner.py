"""Tests for GUI task runner helpers."""

from __future__ import annotations

from gui.task_runner import ImmediateTaskRunner


def test_immediate_task_runner_reports_success() -> None:
    """Immediate runner calls success callback with work result."""
    seen: list[int] = []

    ImmediateTaskRunner().run(lambda: 42, seen.append, lambda exc: None)

    assert seen == [42]


def test_immediate_task_runner_reports_error() -> None:
    """Immediate runner calls error callback when work raises."""
    errors: list[BaseException] = []

    def fail() -> int:
        raise RuntimeError("boom")

    ImmediateTaskRunner().run(fail, lambda result: None, errors.append)

    assert len(errors) == 1
    assert str(errors[0]) == "boom"
