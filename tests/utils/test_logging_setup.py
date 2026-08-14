"""Tests for loguru initialization helpers."""

from __future__ import annotations

from pathlib import Path

from loguru import logger

from utils.logging_setup import LoggingConfig, setup_logging


def test_logging_config_defaults_disable_file_sink() -> None:
    """LoggingConfig defaults are safe for tests and local CLI usage."""
    config = LoggingConfig()

    assert config.level == "INFO"
    assert config.log_file is None
    assert config.enable_stderr is True
    assert config.rotation == "10 MB"
    assert config.retention == "14 days"
    assert config.enqueue is True


def test_setup_logging_returns_loguru_logger() -> None:
    """setup_logging returns the shared loguru logger object."""
    configured = setup_logging(LoggingConfig(enable_stderr=False))

    assert configured is logger


def test_setup_logging_writes_to_configured_file(tmp_path: Path) -> None:
    """A file sink receives messages after setup."""
    log_file = tmp_path / "autolabeler.log"
    setup_logging(LoggingConfig(log_file=log_file, enable_stderr=False, enqueue=False))

    logger.info("hello file sink")
    logger.complete()

    assert "hello file sink" in log_file.read_text(encoding="utf-8")


def test_setup_logging_is_idempotent_for_managed_sinks(tmp_path: Path) -> None:
    """Repeated setup removes previous managed sinks instead of duplicating output."""
    log_file = tmp_path / "autolabeler.log"
    config = LoggingConfig(log_file=log_file, enable_stderr=False, enqueue=False)

    setup_logging(config)
    setup_logging(config)
    logger.info("single write")
    logger.complete()

    assert log_file.read_text(encoding="utf-8").count("single write") == 1
