"""Loguru initialization for AutoLabeler."""

from __future__ import annotations

import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, cast

from loguru import logger


class LoggerLike(Protocol):
    """Protocol for log methods exposed by the shared logger."""

    debug: Callable[..., None]
    info: Callable[..., None]
    warning: Callable[..., None]
    error: Callable[..., None]
    critical: Callable[..., None]


@dataclass(frozen=True)
class LoggingConfig:
    """Configuration for managed loguru sinks."""

    level: str = "INFO"
    log_file: Path | None = None
    enable_stderr: bool = True
    rotation: str = "10 MB"
    retention: str = "14 days"
    enqueue: bool = True


_MANAGED_SINK_IDS: list[int] = []
_LOG_FORMAT = (
    "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level:<8} | "
    "{name}:{function}:{line} - {message}"
)


def setup_logging(config: LoggingConfig | None = None) -> LoggerLike:
    """Configure shared loguru sinks for the current process.

    Args:
        config: Optional logging configuration. Defaults to stderr INFO logs.

    Returns:
        The shared loguru logger object.
    """
    effective = config or LoggingConfig()
    _remove_managed_sinks()

    if effective.enable_stderr:
        _MANAGED_SINK_IDS.append(
            logger.add(
                sys.stderr,
                level=effective.level,
                format=_LOG_FORMAT,
                enqueue=effective.enqueue,
            )
        )

    if effective.log_file is not None:
        effective.log_file.parent.mkdir(parents=True, exist_ok=True)
        _MANAGED_SINK_IDS.append(
            logger.add(
                effective.log_file,
                level=effective.level,
                format=_LOG_FORMAT,
                rotation=effective.rotation,
                retention=effective.retention,
                encoding="utf-8",
                enqueue=effective.enqueue,
            )
        )

    return cast(LoggerLike, logger)


def _remove_managed_sinks() -> None:
    """Remove sinks previously added by setup_logging."""
    while _MANAGED_SINK_IDS:
        sink_id = _MANAGED_SINK_IDS.pop()
        logger.remove(sink_id)
