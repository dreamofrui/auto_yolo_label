"""Tests for external LabelImg launcher integration."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

from core.labelimg_launcher import (
    LabelImgConfig,
    LabelImgLaunchError,
    LabelImgLauncher,
    LabelImgNotInstalledError,
    LabelImgPythonNotFoundError,
    LabelImgValidateConfig,
)
from utils.exceptions import ErrorCode


@dataclass
class FakeCompletedProcess:
    """Minimal subprocess completion object."""

    returncode: int
    stdout: str = ""
    stderr: str = ""


@dataclass
class FakeProcess:
    """Minimal started process object."""

    pid: int


class FakeRunner:
    """Fake subprocess runner for LabelImg tests."""

    def __init__(self) -> None:
        """Create an empty fake runner."""
        self.run_calls: list[list[str]] = []
        self.popen_calls: list[list[str]] = []
        self.python_result = FakeCompletedProcess(
            returncode=0, stdout="Python 3.11.14\n"
        )
        self.labelimg_result = FakeCompletedProcess(
            returncode=0, stdout="labelImg 1.8.6\n"
        )
        self.popen_result = FakeProcess(pid=1234)
        self.run_error: Exception | None = None
        self.popen_error: Exception | None = None

    def run(self, args: list[str], timeout: int) -> FakeCompletedProcess:
        """Record a probe call and return a configured completion."""
        self.run_calls.append(args)
        if self.run_error is not None:
            raise self.run_error
        if args[1:] == ["--version"]:
            return self.python_result
        return self.labelimg_result

    def popen(self, args: list[str]) -> FakeProcess:
        """Record a process start call and return a configured process."""
        self.popen_calls.append(args)
        if self.popen_error is not None:
            raise self.popen_error
        return self.popen_result


def make_python(path: Path) -> Path:
    """Create a fake python executable file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("python", encoding="utf-8")
    return path


def test_labelimg_launcher_constructs_successfully() -> None:
    """LabelImgLauncher can be constructed with default dependencies."""
    launcher = LabelImgLauncher()

    assert isinstance(launcher, LabelImgLauncher)


def test_labelimg_config_defaults_label_and_classes_to_none(tmp_path: Path) -> None:
    """LabelImgConfig optional paths default to None."""
    config = LabelImgConfig(
        python_path=tmp_path / "python.exe", image_dir=tmp_path / "images"
    )

    assert config.label_dir is None
    assert config.classes_file is None


def test_validate_returns_versions_when_python_and_labelimg_available(
    tmp_path: Path,
) -> None:
    """validate returns valid result with Python and LabelImg versions."""
    python_path = make_python(tmp_path / "python.exe")
    runner = FakeRunner()

    result = LabelImgLauncher(runner=runner).validate(
        LabelImgValidateConfig(python_path=python_path)
    )

    assert result.is_valid is True
    assert result.python_version == "Python 3.11.14"
    assert result.labelimg_version == "labelImg 1.8.6"
    assert result.error_message is None
    assert runner.run_calls == [
        [str(python_path), "--version"],
        [str(python_path), "-m", "labelImg", "--version"],
    ]


def test_validate_missing_python_returns_invalid_result(tmp_path: Path) -> None:
    """validate is a non-throwing probe for missing Python paths."""
    missing = tmp_path / "missing.exe"

    result = LabelImgLauncher(runner=FakeRunner()).validate(
        LabelImgValidateConfig(python_path=missing)
    )

    assert result.is_valid is False
    assert result.python_version == ""
    assert result.labelimg_version is None
    assert str(missing) in str(result.error_message)


def test_validate_labelimg_missing_returns_invalid_result(tmp_path: Path) -> None:
    """validate returns invalid result when LabelImg is not installed."""
    python_path = make_python(tmp_path / "python.exe")
    runner = FakeRunner()
    runner.labelimg_result = FakeCompletedProcess(
        returncode=1, stderr="No module named labelImg"
    )

    result = LabelImgLauncher(runner=runner).validate(
        LabelImgValidateConfig(python_path=python_path)
    )

    assert result.is_valid is False
    assert result.python_version == "Python 3.11.14"
    assert result.labelimg_version is None
    assert "LabelImg" in str(result.error_message)


def test_launch_missing_python_raises_python_not_found(tmp_path: Path) -> None:
    """launch raises a module exception for missing Python."""
    with pytest.raises(LabelImgPythonNotFoundError) as exc_info:
        LabelImgLauncher(runner=FakeRunner()).launch(
            LabelImgConfig(
                python_path=tmp_path / "missing.exe", image_dir=tmp_path / "images"
            )
        )

    assert exc_info.value.code == ErrorCode.LABELIMG_PYTHON_NOT_FOUND


def test_launch_missing_image_dir_raises_launch_error(tmp_path: Path) -> None:
    """launch validates the image directory before starting LabelImg."""
    python_path = make_python(tmp_path / "python.exe")

    with pytest.raises(LabelImgLaunchError) as exc_info:
        LabelImgLauncher(runner=FakeRunner()).launch(
            LabelImgConfig(
                python_path=python_path, image_dir=tmp_path / "missing-images"
            )
        )

    assert exc_info.value.code == ErrorCode.LABELIMG_LAUNCH


def test_launch_uses_image_dir_as_default_label_dir_and_auto_classes_file(
    tmp_path: Path,
) -> None:
    """launch defaults label_dir to image_dir and auto-resolves classes.txt."""
    python_path = make_python(tmp_path / "python.exe")
    image_dir = tmp_path / "images"
    image_dir.mkdir()
    classes_file = image_dir / "classes.txt"
    classes_file.write_text("CodeA\n", encoding="utf-8")
    runner = FakeRunner()

    result = LabelImgLauncher(runner=runner).launch(
        LabelImgConfig(python_path=python_path, image_dir=image_dir)
    )

    assert runner.popen_calls == [
        [
            str(python_path),
            "-m",
            "labelImg",
            str(image_dir),
            str(classes_file),
            str(image_dir),
        ]
    ]
    assert result.process_id == 1234
    assert str(image_dir) in result.command


def test_launch_uses_explicit_label_dir_and_classes_file(tmp_path: Path) -> None:
    """launch uses explicit label and classes paths when provided."""
    python_path = make_python(tmp_path / "python.exe")
    image_dir = tmp_path / "images"
    label_dir = tmp_path / "labels"
    classes_file = tmp_path / "classes.txt"
    image_dir.mkdir()
    label_dir.mkdir()
    classes_file.write_text("CodeA\n", encoding="utf-8")
    runner = FakeRunner()

    LabelImgLauncher(runner=runner).launch(
        LabelImgConfig(
            python_path=python_path,
            image_dir=image_dir,
            label_dir=label_dir,
            classes_file=classes_file,
        )
    )

    assert runner.popen_calls == [
        [
            str(python_path),
            "-m",
            "labelImg",
            str(image_dir),
            str(classes_file),
            str(label_dir),
        ]
    ]


def test_launch_creates_missing_explicit_label_dir(tmp_path: Path) -> None:
    """launch creates label_dir because it is an output directory."""
    python_path = make_python(tmp_path / "python.exe")
    image_dir = tmp_path / "images"
    label_dir = tmp_path / "labels"
    classes_file = tmp_path / "classes.txt"
    image_dir.mkdir()
    classes_file.write_text("CodeA\n", encoding="utf-8")

    LabelImgLauncher(runner=FakeRunner()).launch(
        LabelImgConfig(
            python_path=python_path,
            image_dir=image_dir,
            label_dir=label_dir,
            classes_file=classes_file,
        )
    )

    assert label_dir.is_dir()


def test_launch_missing_classes_file_raises_launch_error(tmp_path: Path) -> None:
    """launch fails fast when no classes file can be resolved."""
    python_path = make_python(tmp_path / "python.exe")
    image_dir = tmp_path / "images"
    image_dir.mkdir()

    with pytest.raises(LabelImgLaunchError) as exc_info:
        LabelImgLauncher(runner=FakeRunner()).launch(
            LabelImgConfig(python_path=python_path, image_dir=image_dir)
        )

    assert exc_info.value.code == ErrorCode.LABELIMG_LAUNCH


def test_launch_raises_not_installed_when_validation_command_fails(
    tmp_path: Path,
) -> None:
    """launch checks LabelImg installation before starting the GUI."""
    python_path = make_python(tmp_path / "python.exe")
    image_dir = tmp_path / "images"
    image_dir.mkdir()
    (image_dir / "classes.txt").write_text("CodeA\n", encoding="utf-8")
    runner = FakeRunner()
    runner.labelimg_result = FakeCompletedProcess(
        returncode=1, stderr="No module named labelImg"
    )

    with pytest.raises(LabelImgNotInstalledError) as exc_info:
        LabelImgLauncher(runner=runner).launch(
            LabelImgConfig(python_path=python_path, image_dir=image_dir)
        )

    assert exc_info.value.code == ErrorCode.LABELIMG_NOT_INSTALLED
    assert runner.popen_calls == []


def test_launch_popen_failure_raises_launch_error(tmp_path: Path) -> None:
    """process start failures are mapped to LabelImgLaunchError."""
    python_path = make_python(tmp_path / "python.exe")
    image_dir = tmp_path / "images"
    image_dir.mkdir()
    (image_dir / "classes.txt").write_text("CodeA\n", encoding="utf-8")
    runner = FakeRunner()
    runner.popen_error = OSError("boom")

    with pytest.raises(LabelImgLaunchError) as exc_info:
        LabelImgLauncher(runner=runner).launch(
            LabelImgConfig(python_path=python_path, image_dir=image_dir)
        )

    assert exc_info.value.code == ErrorCode.LABELIMG_LAUNCH
    assert "boom" in str(exc_info.value.details)
