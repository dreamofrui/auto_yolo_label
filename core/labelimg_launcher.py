"""External LabelImg validation and launch boundary."""

from __future__ import annotations

import shlex
import shutil
import subprocess
from collections.abc import Mapping
from dataclasses import dataclass
from os import pathsep
from pathlib import Path
from typing import Literal, Protocol

from loguru import logger

from utils.exceptions import AutoLabelerError, ErrorCode

_PROBE_TIMEOUT_SECONDS = 5
_CONFIG_DIR_NAME = ".autolabeler"
_CONFIG_FILE_NAME = "labelimg.json"
_LABELIMG_FORMATS = {"yolo", "voc"}
_LABELIMG_WRAPPER_SCRIPT = """
import sys
from pathlib import Path
import labelImg.labelImg as labelimg_module
from labelImg.labelImg import FORMAT_PASCALVOC, FORMAT_YOLO, get_main_app

annotation_format = sys.argv[1]
if annotation_format == "yolo":
    image_dir = sys.argv[2]
    class_file = sys.argv[3]
    save_dir = sys.argv[4]
    app, window = get_main_app([sys.argv[0], image_dir, class_file, save_dir])
    window.default_save_dir = save_dir
    window.last_open_dir = image_dir
    window.import_dir_images(image_dir)
    window.set_format(FORMAT_YOLO)
elif annotation_format == "voc":
    image_dir = sys.argv[2]
    default_class_file = str(
        Path(labelimg_module.__file__).resolve().parent
        / "data"
        / "predefined_classes.txt"
    )
    app, window = get_main_app([sys.argv[0], image_dir, default_class_file])
    window.default_save_dir = image_dir
    window.last_open_dir = image_dir
    window.import_dir_images(image_dir)
    window.set_format(FORMAT_PASCALVOC)
else:
    raise SystemExit(f"Unsupported LabelImg format: {annotation_format}")
sys.exit(app.exec_())
""".strip()


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

    def run(
        self,
        args: list[str],
        timeout: int,
        env: dict[str, str] | None = None,
    ) -> _CompletedProcess:
        """Run a short subprocess command."""

    def popen(
        self,
        args: list[str],
        env: dict[str, str] | None = None,
    ) -> _Process:
        """Start a long-running subprocess and return immediately."""


class _DefaultSubprocessRunner:
    """Default subprocess runner."""

    def run(
        self,
        args: list[str],
        timeout: int,
        env: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        """Run a command and capture text output."""
        return subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            env=env,
        )

    def popen(
        self,
        args: list[str],
        env: dict[str, str] | None = None,
    ) -> subprocess.Popen[bytes]:
        """Start a command without shell expansion."""
        return subprocess.Popen(args, env=env)


@dataclass(frozen=True)
class LabelImgConfig:
    """Configuration for launching LabelImg."""

    python_path: Path
    image_dir: Path
    label_dir: Path | None = None
    classes_file: Path | None = None
    annotation_format: Literal["yolo", "voc"] = "yolo"


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

    def __init__(
        self,
        runner: _SubprocessRunner | None = None,
        environment: Mapping[str, str] | None = None,
    ) -> None:
        """Create a launcher with an optional subprocess runner."""
        self._runner = runner or _DefaultSubprocessRunner()
        self._environment = dict(environment) if environment is not None else None
        self.config_path = Path.home() / _CONFIG_DIR_NAME / _CONFIG_FILE_NAME

    def validate(self, config: LabelImgValidateConfig) -> LabelImgValidateResult:
        """Validate that a Python interpreter can import LabelImg."""
        if not _existing_file(config.python_path):
            return LabelImgValidateResult(
                is_valid=False,
                labelimg_version=None,
                python_version="",
                error_message=f"Python interpreter does not exist: {config.python_path}",
            )
        try:
            python_version = self._python_version(config.python_path)
            labelimg_version = self._labelimg_version(config.python_path)
            self._ensure_image_format_support(config.python_path, {"jpg", "jpeg"})
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

    def preflight(self, config: LabelImgConfig) -> LabelImgValidateResult:
        """Validate LabelImg environment and launch inputs without starting it."""
        if not _existing_file(config.python_path):
            return LabelImgValidateResult(
                is_valid=False,
                labelimg_version=None,
                python_version="",
                error_message=f"Python interpreter does not exist: {config.python_path}",
            )
        try:
            python_version = self._python_version(config.python_path)
            labelimg_version = self._labelimg_version(config.python_path)
            self._validate_launch_inputs(config)
            self._ensure_image_dir_has_readable_images(
                config.image_dir, config.python_path
            )
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
        """Launch LabelImg with explicit image and annotation format paths."""
        label_dir, classes_file = self._validate_launch_inputs(config)
        self._ensure_labelimg_installed(config.python_path)
        self._ensure_image_dir_has_readable_images(config.image_dir, config.python_path)
        try:
            args = self._build_launch_args(config, label_dir, classes_file)
            logger.info(
                "Launching LabelImg: image_dir={}, label_dir={}, format={}",
                config.image_dir,
                config.label_dir,
                config.annotation_format,
            )
            process = self._runner.popen(
                args,
                env=_labelimg_env(config.python_path, self._environment),
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raise LabelImgLaunchError("Failed to launch LabelImg", details=str(exc)) from exc
        return LabelImgLaunchResult(process_id=process.pid, command=shlex.join(args))

    def _validate_launch_inputs(
        self, config: LabelImgConfig
    ) -> tuple[Path | None, Path | None]:
        """Validate shared launch inputs and format-specific paths."""
        if not _existing_file(config.python_path):
            raise LabelImgPythonNotFoundError(
                "Python interpreter does not exist", details=str(config.python_path)
            )
        if not config.image_dir.exists() or not config.image_dir.is_dir():
            raise LabelImgLaunchError(
                "Image directory does not exist", details=str(config.image_dir)
            )
        if config.annotation_format not in _LABELIMG_FORMATS:
            raise LabelImgLaunchError(
                "Unsupported LabelImg annotation format",
                details=config.annotation_format,
            )
        return self._validate_launch_paths(config)

    def _validate_launch_paths(
        self, config: LabelImgConfig
    ) -> tuple[Path | None, Path | None]:
        """Validate format-specific input paths without writing outputs."""
        if config.annotation_format == "voc":
            return None, None

        if config.label_dir is None:
            raise LabelImgLaunchError("label_dir is required")
        if config.classes_file is None:
            raise LabelImgLaunchError("classes_file is required")

        label_dir = config.label_dir
        classes_file = config.classes_file
        if not classes_file.exists() or not classes_file.is_file():
            raise LabelImgLaunchError(
                "classes.txt does not exist", details=str(classes_file)
            )
        if not _non_empty_classes_file(classes_file):
            raise LabelImgLaunchError("classes.txt is empty", details=str(classes_file))
        return label_dir, classes_file

    def _build_launch_args(
        self,
        config: LabelImgConfig,
        label_dir: Path | None,
        classes_file: Path | None,
    ) -> list[str]:
        """Build Python wrapper arguments for a validated LabelImg launch."""
        args = [
            str(config.python_path),
            "-c",
            _LABELIMG_WRAPPER_SCRIPT,
            config.annotation_format,
            str(config.image_dir),
        ]
        if config.annotation_format == "voc":
            return args

        if label_dir is None or classes_file is None:
            raise LabelImgLaunchError("YOLO launch paths are incomplete")
        label_dir.mkdir(parents=True, exist_ok=True)
        _prepare_labelimg_yolo_classes(classes_file, label_dir)
        args.extend([str(classes_file), str(label_dir)])
        return args

    def _python_version(self, python_path: Path) -> str:
        """Return the Python version string from the interpreter."""
        result = self._runner.run(
            [str(python_path), "--version"],
            timeout=_PROBE_TIMEOUT_SECONDS,
            env=_labelimg_env(python_path, self._environment),
        )
        if result.returncode != 0:
            raise LabelImgPythonNotFoundError(
                "Python interpreter is not usable", details=_combined_output(result)
            )
        version = _combined_output(result)
        if not version:
            raise LabelImgPythonNotFoundError(
                "Python version probe failed", details=str(python_path)
            )
        return version

    def _labelimg_version(self, python_path: Path) -> str | None:
        """Return LabelImg package version or an installed marker."""
        labelimg_path = _labelimg_executable_for_python(python_path)
        if labelimg_path is None:
            raise LabelImgNotInstalledError(
                "LabelImg executable is not installed",
                details=str(python_path.parent / "Scripts" / "labelImg.exe"),
            )
        result = self._runner.run(
            [
                str(python_path),
                "-c",
                (
                    "import importlib.metadata as metadata\n"
                    "import labelImg.labelImg\n"
                    "try:\n"
                    "    version = metadata.version('labelImg')\n"
                    "except metadata.PackageNotFoundError:\n"
                    "    version = 'installed'\n"
                    "print(f'labelImg {version}')"
                ),
            ],
            timeout=_PROBE_TIMEOUT_SECONDS,
            env=_labelimg_env(python_path, self._environment),
        )
        if result.returncode != 0:
            raise LabelImgNotInstalledError(
                "LabelImg is not installed", details=_combined_output(result)
            )
        output = _combined_output(result)
        return output or None

    def _ensure_labelimg_installed(self, python_path: Path) -> Path:
        """Raise when the configured Python environment lacks LabelImg."""
        self._labelimg_version(python_path)
        labelimg_path = _labelimg_executable_for_python(python_path)
        if labelimg_path is None:
            raise LabelImgNotInstalledError(
                "LabelImg executable is not installed",
                details=str(python_path.parent / "Scripts" / "labelImg.exe"),
            )
        return labelimg_path

    def _ensure_image_format_support(
        self, python_path: Path, required_formats: set[str]
    ) -> set[str]:
        """Return Qt image formats or raise when required formats are unavailable."""
        result = self._runner.run(
            [
                str(python_path),
                "-c",
                (
                    "from PyQt5.QtWidgets import QApplication; "
                    "from PyQt5.QtGui import QImageReader; "
                    "import sys; "
                    "app = QApplication.instance() or QApplication(sys.argv[:1]); "
                    "print(','.join(bytes(fmt).decode('ascii').lower() "
                    "for fmt in QImageReader.supportedImageFormats()))"
                ),
            ],
            timeout=_PROBE_TIMEOUT_SECONDS,
            env=_labelimg_env(python_path, self._environment),
        )
        if result.returncode != 0:
            raise LabelImgLaunchError(
                "LabelImg image format probe failed",
                details=_combined_output(result),
            )
        formats = {
            item.strip().lower()
            for item in _combined_output(result).replace("\n", ",").split(",")
            if item.strip()
        }
        missing = required_formats - formats
        if missing:
            raise LabelImgLaunchError(
                "LabelImg cannot read JPG images",
                details=f"missing formats: {', '.join(sorted(missing))}",
            )
        return formats

    def _ensure_image_dir_has_readable_images(
        self, image_dir: Path, python_path: Path
    ) -> None:
        """Fail before launch when LabelImg would open an empty image list."""
        formats = self._ensure_image_format_support(python_path, set())
        supported_suffixes = {f".{item}" for item in formats}
        readable = [
            path
            for path in image_dir.rglob("*")
            if path.is_file() and path.suffix.lower() in supported_suffixes
        ]
        if not readable:
            raise LabelImgLaunchError(
                "Image directory contains no LabelImg-readable images",
                details=str(image_dir),
            )


def _existing_file(path: Path) -> bool:
    """Return whether path exists as a regular file."""
    return path.exists() and path.is_file()


def _combined_output(result: _CompletedProcess) -> str:
    """Return first non-empty stdout/stderr text from a subprocess result."""
    return result.stdout.strip() or result.stderr.strip()


def _non_empty_classes_file(path: Path) -> bool:
    """Return whether classes.txt has at least one non-empty class name."""
    try:
        return any(
            line.strip() for line in path.read_text(encoding="utf-8").splitlines()
        )
    except OSError:
        return False


def _prepare_labelimg_yolo_classes(classes_file: Path, label_dir: Path) -> None:
    """Place classes.txt where LabelImg's YOLO reader expects it."""
    sidecar_path = label_dir / "classes.txt"
    if classes_file.resolve() == sidecar_path.resolve():
        return
    shutil.copyfile(classes_file, sidecar_path)


def _labelimg_executable_for_python(python_path: Path) -> Path | None:
    """Return the LabelImg console executable installed beside a Python env."""
    candidates = (
        python_path.parent / "Scripts" / "labelImg.exe",
        python_path.parent / "Scripts" / "labelImg",
        python_path.parent / "bin" / "labelImg",
    )
    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            return candidate
    return None


def _labelimg_env(
    python_path: Path, base_environment: Mapping[str, str] | None
) -> dict[str, str] | None:
    """Build an environment that lets PyQt load the env's Qt image plugins."""
    if base_environment is None:
        return None
    env = dict(base_environment)
    env_root = python_path.parent
    prepend = [
        env_root / "Library" / "bin",
        env_root / "Scripts",
        env_root,
    ]
    existing_path = env.get("PATH", "")
    env["PATH"] = pathsep.join(
        [str(path) for path in prepend if path.exists()] + [existing_path]
    )
    plugin_dir = env_root / "Library" / "plugins"
    if plugin_dir.exists():
        env["QT_PLUGIN_PATH"] = str(plugin_dir)
    return env
