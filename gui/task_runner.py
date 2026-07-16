"""Small task runners for GUI-triggered worker calls."""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol, TypeVar

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal, Slot

T = TypeVar("T")


class TaskRunner(Protocol):
    """Interface for running worker calls without tying pages to threads."""

    def run(
        self,
        work: Callable[[], T],
        on_success: Callable[[T], None],
        on_error: Callable[[BaseException], None],
    ) -> None:
        """Run work and report either success or failure."""


class ImmediateTaskRunner:
    """Synchronous runner used by tests and very small controlled calls."""

    def run(
        self,
        work: Callable[[], T],
        on_success: Callable[[T], None],
        on_error: Callable[[BaseException], None],
    ) -> None:
        """Run work immediately in the current thread."""
        try:
            on_success(work())
        except BaseException as exc:
            on_error(exc)


class _WorkerSignals(QObject):
    """Signals emitted by a background worker runnable."""

    finished = Signal(object)
    failed = Signal(object)


class _WorkerRunnable(QRunnable):
    """Run one callable on a Qt thread-pool thread."""

    def __init__(self, work: Callable[[], object]) -> None:
        super().__init__()
        self.setAutoDelete(False)
        self._work = work
        self.signals = _WorkerSignals()

    @Slot()
    def run(self) -> None:
        """Execute work and emit the outcome."""
        try:
            self.signals.finished.emit(self._work())
        except BaseException as exc:
            self.signals.failed.emit(exc)


class AsyncTaskRunner(QObject):
    """Qt thread-pool runner for production GUI worker calls."""

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._pool = QThreadPool.globalInstance()
        self._active: set[_WorkerRunnable] = set()

    def run(
        self,
        work: Callable[[], T],
        on_success: Callable[[T], None],
        on_error: Callable[[BaseException], None],
    ) -> None:
        """Run work on the Qt global thread pool."""
        job = _WorkerRunnable(work)
        self._active.add(job)

        def finish(result: object) -> None:
            self._active.discard(job)
            on_success(result)  # type: ignore[arg-type]

        def fail(error: object) -> None:
            self._active.discard(job)
            if isinstance(error, BaseException):
                on_error(error)
                return
            on_error(RuntimeError(str(error)))

        job.signals.finished.connect(finish)
        job.signals.failed.connect(fail)
        self._pool.start(job)
