"""External LabelImg validation and launch boundary."""

from __future__ import annotations

import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from loguru import logger

from utils.exceptions import AutoLabelerError, ErrorCode

_PROBE_TIMEOUT_SECONDS = 5
_CONFIG_DIR_NAME = ".autolabeler"
_CONFIG_FILE_NAME = "labelimg.json"


class _CompletedProcess(Protocol):
    """Minimal completed subprocess protocol."""

    returncode: int
    stdout: str
    stderr: str


class _Process(Protocol):
    """Minimal started subprocess protocol."""

    pid: int


class _SubprocessRunner(Protocol):
    """Subprocess boundary used by LabelImgLauncher."""

    def run(self, args: list[str], timeout: int) -> _CompletedProcess:
        """Run a short subprocess command."""

    def popen(self, args: list[str]) -> _Process:
        """Start a long-running subprocess and return immediately."""


class _DefaultSubprocessRunner:
    """Default subprocess runner."""

    def run(self, args: list[str], timeout: int) -> subprocess.CompletedProcess[str]:
        """Run a command and capture text output."""
        return subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )

    def popen(self, args: list[str]) -> subprocess.Popen[bytes]:
        """Start a command without shell expansion."""
        return subprocess.Popen(args)


@dataclass(frozen=True)
class LabelImgConfig:
    """Configuration for launching LabelImg."""

    python_path: Path
    image_dir: Path
    label_dir: Path | None = None
    classes_file: Path | None = None


@dataclass(frozen=True)
class LabelImgValidateConfig:
    """Configuration for validating a Python environment."""

    python_path: Path


@dataclass(frozen=True)
class LabelImgValidateResult:
    """Validation result for an external Python environment."""

    is_valid: bool
    labelimg_version: str | None
    python_version: str
    error_message: str | None


@dataclass(frozen=True)
class LabelImgLaunchResult:
    """Result for a launched LabelImg process."""

    process_id: int
    command: str


class LabelImgError(AutoLabelerError):
    """Base class for LabelImg integration errors."""

    code = ErrorCode.INTERNAL_ERROR


class LabelImgPythonNotFoundError(LabelImgError):
    """Raised when the configured Python interpreter does not exist."""

    code = ErrorCode.LABELIMG_PYTHON_NOT_FOUND


class LabelImgNotInstalledError(LabelImgError):
    """Raised when the configured Python environment lacks LabelImg."""

    code = ErrorCode.LABELIMG_NOT_INSTALLED


class LabelImgLaunchError(LabelImgError):
    """Raised when LabelImg cannot be launched."""

    code = ErrorCode.LABELIMG_LAUNCH


class LabelImgLauncher:
    """Validate and launch an external LabelImg process."""

    def __init__(self, runner: _SubprocessRunner | None = None) -> None:
        """Create a launcher with an optional subprocess runner.

        Args:
            runner: Optional subprocess boundary for tests.
        """
        self._runner = runner or _DefaultSubprocessRunner()
        self.config_path = Path.home() / _CONFIG_DIR_NAME / _CONFIG_FILE_NAME

    def validate(self, config: LabelImgValidateConfig) -> LabelImgValidateResult:
        """Validate that a Python interpreter can import LabelImg.

        Args:
            config: Python interpreter to probe.

        Returns:
            A non-throwing validation result for settings UI/API preflight.
        """
        if not _existing_file(config.python_path):
            return LabelImgValidateResult(
                is_valid=False,
                labelimg_version=None,
                python_version="",
                error_message=f"Python 解释器不存在: {config.python_path}",
            )
        try:
            python_version = self._python_version(config.python_path)
            labelimg_version = self._labelimg_version(config.python_path)
        except LabelImgError as exc:
            return LabelImgValidateResult(
                is_valid=False,
                labelimg_version=None,
                python_version=python_version if "python_version" in locals() else "",
                error_message=exc.message,
            )
        except (OSError, subprocess.SubprocessError, subprocess.TimeoutExpired) as exc:
            return LabelImgValidateResult(
                is_valid=False,
                labelimg_version=None,
                python_version="",
                error_message=str(exc),
            )
        return LabelImgValidateResult(
            is_valid=True,
            labelimg_version=labelimg_version,
            python_version=python_version,
            error_message=None,
        )

    def launch(self, config: LabelImgConfig) -> LabelImgLaunchResult:
        """Launch LabelImg and return immediately.

        Args:
            config: Launch configuration.

        Returns:
            Started process metadata.

        Raises:
            LabelImgPythonNotFoundError: If python_path is missing.
            LabelImgNotInstalledError: If LabelImg cannot be imported.
            LabelImgLaunchError: If paths are invalid or process start fails.
        """
        if not _existing_file(config.python_path):
            raise LabelImgPythonNotFoundError(
                "Python 解释器不存在", details=str(config.python_path)
            )
        if not config.image_dir.exists() or not config.image_dir.is_dir():
            raise LabelImgLaunchError("图片目录不存在", details=str(config.image_dir))

        label_dir = config.label_dir or config.image_dir
        classes_file = config.classes_file or config.image_dir / "classes.txt"
        if not classes_file.exists() or not classes_file.is_file():
            raise LabelImgLaunchError("classes.txt 不存在", details=str(classes_file))

        self._ensure_labelimg_installed(config.python_path)
        try:
            label_dir.mkdir(parents=True, exist_ok=True)
            args = [
                str(config.python_path),
                "-m",
                "labelImg",
                str(config.image_dir),
                str(classes_file),
                str(label_dir),
            ]
            logger.info(
                "启动 LabelImg: image_dir={}, label_dir={}", config.image_dir, label_dir
            )
            process = self._runner.popen(args)
        except (OSError, subprocess.SubprocessError) as exc:
            raise LabelImgLaunchError("启动 LabelImg 失败", details=str(exc)) from exc
        return LabelImgLaunchResult(process_id=process.pid, command=shlex.join(args))

    def _python_version(self, python_path: Path) -> str:
        """Return the Python version string from the interpreter."""
        result = self._runner.run(
            [str(python_path), "--version"], timeout=_PROBE_TIMEOUT_SECONDS
        )
        if result.returncode != 0:
            raise LabelImgPythonNotFoundError(
                "Python 解释器不可用", details=_combined_output(result)
            )
        version = _combined_output(result)
        if not version:
            raise LabelImgPythonNotFoundError(
                "Python 版本探测失败", details=str(python_path)
            )
        return version

    def _labelimg_version(self, python_path: Path) -> str | None:
        """Return LabelImg version or installed marker."""
        result = self._runner.run(
            [str(python_path), "-m", "labelImg", "--version"],
            timeout=_PROBE_TIMEOUT_SECONDS,
        )
        if result.returncode != 0:
            raise LabelImgNotInstalledError(
                "LabelImg 未安装", details=_combined_output(result)
            )
        output = _combined_output(result)
        return output or None

    def _ensure_labelimg_installed(self, python_path: Path) -> None:
        """Raise when the configured Python cannot run LabelImg."""
        self._labelimg_version(python_path)


def _existing_file(path: Path) -> bool:
    """Return whether path exists as a regular file."""
    return path.exists() and path.is_file()


def _combined_output(result: _CompletedProcess) -> str:
    """Return first non-empty stdout/stderr text from a subprocess result."""
    output = result.stdout.strip() or result.stderr.strip()
    return output
