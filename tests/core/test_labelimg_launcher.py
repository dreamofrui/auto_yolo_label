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
        self.run_envs: list[dict[str, str] | None] = []
        self.popen_calls: list[list[str]] = []
        self.popen_envs: list[dict[str, str] | None] = []
        self.python_result = FakeCompletedProcess(
            returncode=0, stdout="Python 3.11.14\n"
        )
        self.labelimg_result = FakeCompletedProcess(
            returncode=0, stdout="labelImg 1.8.6\n"
        )
        self.labelimg_probe_result = FakeCompletedProcess(
            returncode=0, stdout="labelImg 1.8.6\n"
        )
        self.image_formats_result = FakeCompletedProcess(
            returncode=0, stdout="bmp,jpeg,jpg,png\n"
        )
        self.popen_result = FakeProcess(pid=1234)
        self.run_error: Exception | None = None
        self.popen_error: Exception | None = None

    def run(
        self,
        args: list[str],
        timeout: int,
        env: dict[str, str] | None = None,
    ) -> FakeCompletedProcess:
        """Record a probe call and return a configured completion."""
        self.run_calls.append(args)
        self.run_envs.append(env)
        if self.run_error is not None:
            raise self.run_error
        if args[1:] == ["--version"]:
            return self.python_result
        if len(args) >= 3 and args[1] == "-c" and "importlib.metadata" in args[2]:
            return self.labelimg_probe_result
        if len(args) >= 2 and args[1] == "-c":
            return self.image_formats_result
        return self.labelimg_result

    def popen(
        self,
        args: list[str],
        env: dict[str, str] | None = None,
    ) -> FakeProcess:
        """Record a process start call and return a configured process."""
        self.popen_calls.append(args)
        self.popen_envs.append(env)
        if self.popen_error is not None:
            raise self.popen_error
        return self.popen_result


def make_python(path: Path) -> Path:
    """Create a fake python executable file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("python", encoding="utf-8")
    return path


def make_labelimg_executable(python_path: Path) -> Path:
    """Create a fake LabelImg console executable beside a fake Python."""
    labelimg_path = python_path.parent / "Scripts" / "labelImg.exe"
    labelimg_path.parent.mkdir(parents=True, exist_ok=True)
    labelimg_path.write_text("labelImg", encoding="utf-8")
    return labelimg_path


def make_qt_plugin_dir(python_path: Path) -> Path:
    """Create the Qt plugin directory expected in a conda-style env."""
    (python_path.parent / "Library" / "bin").mkdir(parents=True, exist_ok=True)
    plugin_dir = python_path.parent / "Library" / "plugins"
    plugin_dir.mkdir(parents=True, exist_ok=True)
    return plugin_dir


def assert_labelimg_wrapper_launch(
    runner: FakeRunner,
    python_path: Path,
    label_format: str,
    positional_args: list[Path],
) -> None:
    """Assert that LabelImg is launched through the format-setting wrapper."""
    assert len(runner.popen_calls) == 1
    call = runner.popen_calls[0]
    assert call[0] == str(python_path)
    assert call[1] == "-c"
    assert "get_main_app" in call[2]
    assert "set_format" in call[2]
    assert call[3] == label_format
    assert call[4:] == [str(path) for path in positional_args]


def labelimg_wrapper_script(runner: FakeRunner) -> str:
    """Return the inline LabelImg wrapper script from one launch call."""
    assert len(runner.popen_calls) == 1
    return runner.popen_calls[0][2]


def test_labelimg_launcher_constructs_successfully() -> None:
    """LabelImgLauncher can be constructed with default dependencies."""
    launcher = LabelImgLauncher()

    assert isinstance(launcher, LabelImgLauncher)


def test_labelimg_config_stores_explicit_labeling_paths(tmp_path: Path) -> None:
    """LabelImgConfig carries the three user-selected free-labeling paths."""
    config = LabelImgConfig(
        python_path=tmp_path / "python.exe",
        image_dir=tmp_path / "images",
        classes_file=tmp_path / "classes.txt",
        label_dir=tmp_path / "labels",
    )

    assert config.image_dir == tmp_path / "images"
    assert config.classes_file == tmp_path / "classes.txt"
    assert config.label_dir == tmp_path / "labels"
    assert config.annotation_format == "yolo"


def test_validate_returns_versions_when_python_and_labelimg_available(
    tmp_path: Path,
) -> None:
    """validate returns valid result with Python and LabelImg versions."""
    python_path = make_python(tmp_path / "python.exe")
    labelimg_path = make_labelimg_executable(python_path)
    make_qt_plugin_dir(python_path)
    runner = FakeRunner()

    result = LabelImgLauncher(runner=runner, environment={"PATH": "base"}).validate(
        LabelImgValidateConfig(python_path=python_path)
    )

    assert result.is_valid is True
    assert result.python_version == "Python 3.11.14"
    assert result.labelimg_version == "labelImg 1.8.6"
    assert result.error_message is None
    assert runner.run_calls == [
        [str(python_path), "--version"],
        [str(python_path), "-c", runner.run_calls[1][2]],
        [str(python_path), "-c", runner.run_calls[2][2]],
    ]
    assert "importlib.metadata" in runner.run_calls[1][2]
    compile(runner.run_calls[1][2], "<labelimg probe>", "exec")
    assert str(labelimg_path) not in runner.run_calls[1]
    assert runner.run_envs[2] is not None
    assert str(python_path.parent / "Library" / "bin") in str(
        runner.run_envs[2]["PATH"]
    )


def test_validate_rejects_labelimg_environment_without_jpeg_support(
    tmp_path: Path,
) -> None:
    """validate catches Qt image plugin environments that cannot read JPG."""
    python_path = make_python(tmp_path / "python.exe")
    make_labelimg_executable(python_path)
    runner = FakeRunner()
    runner.image_formats_result = FakeCompletedProcess(
        returncode=0,
        stdout="bmp,png\n",
    )

    result = LabelImgLauncher(runner=runner).validate(
        LabelImgValidateConfig(python_path=python_path)
    )

    assert result.is_valid is False
    assert "JPG" in str(result.error_message)


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


def test_launch_missing_explicit_label_dir_raises_launch_error(
    tmp_path: Path,
) -> None:
    """launch requires the user-selected label output folder."""
    python_path = make_python(tmp_path / "python.exe")
    image_dir = tmp_path / "images"
    image_dir.mkdir()
    classes_file = tmp_path / "classes.txt"
    classes_file.write_text("CodeA\n", encoding="utf-8")

    with pytest.raises(LabelImgLaunchError) as exc_info:
        LabelImgLauncher(runner=FakeRunner()).launch(
            LabelImgConfig(
                python_path=python_path,
                image_dir=image_dir,
                classes_file=classes_file,
            )
        )

    assert exc_info.value.code == ErrorCode.LABELIMG_LAUNCH


def test_launch_missing_explicit_classes_file_raises_launch_error(
    tmp_path: Path,
) -> None:
    """launch requires the user-selected classes.txt path."""
    python_path = make_python(tmp_path / "python.exe")
    image_dir = tmp_path / "images"
    label_dir = tmp_path / "labels"
    image_dir.mkdir()

    with pytest.raises(LabelImgLaunchError) as exc_info:
        LabelImgLauncher(runner=FakeRunner()).launch(
            LabelImgConfig(
                python_path=python_path,
                image_dir=image_dir,
                label_dir=label_dir,
            )
        )

    assert exc_info.value.code == ErrorCode.LABELIMG_LAUNCH


def test_preflight_rejects_missing_yolo_classes_without_launching(
    tmp_path: Path,
) -> None:
    """preflight validates YOLO launch inputs without starting LabelImg."""
    python_path = make_python(tmp_path / "python.exe")
    make_labelimg_executable(python_path)
    image_dir = tmp_path / "images"
    label_dir = tmp_path / "labels"
    image_dir.mkdir()
    (image_dir / "a.jpg").write_bytes(b"fake")
    runner = FakeRunner()

    result = LabelImgLauncher(runner=runner).preflight(
        LabelImgConfig(
            python_path=python_path,
            image_dir=image_dir,
            label_dir=label_dir,
            classes_file=tmp_path / "missing-classes.txt",
        )
    )

    assert result.is_valid is False
    assert "classes.txt" in str(result.error_message)
    assert runner.popen_calls == []
    assert not label_dir.exists()


def test_preflight_accepts_voc_image_folder_without_classes_or_label_dir(
    tmp_path: Path,
) -> None:
    """preflight accepts VOC folder labeling without YOLO-only paths."""
    python_path = make_python(tmp_path / "python.exe")
    make_labelimg_executable(python_path)
    image_dir = tmp_path / "images"
    image_dir.mkdir()
    (image_dir / "a.jpg").write_bytes(b"fake")
    runner = FakeRunner()

    result = LabelImgLauncher(runner=runner).preflight(
        LabelImgConfig(
            python_path=python_path,
            image_dir=image_dir,
            annotation_format="voc",
        )
    )

    assert result.is_valid is True
    assert result.python_version == "Python 3.11.14"
    assert result.labelimg_version == "labelImg 1.8.6"
    assert result.error_message is None
    assert runner.popen_calls == []


def test_launch_uses_explicit_label_dir_and_classes_file(tmp_path: Path) -> None:
    """launch uses explicit label and classes paths when provided."""
    python_path = make_python(tmp_path / "python.exe")
    make_labelimg_executable(python_path)
    make_qt_plugin_dir(python_path)
    image_dir = tmp_path / "images"
    label_dir = tmp_path / "labels"
    classes_file = tmp_path / "classes.txt"
    image_dir.mkdir()
    (image_dir / "a.jpg").write_bytes(b"fake")
    label_dir.mkdir()
    classes_file.write_text("CodeA\n", encoding="utf-8")
    runner = FakeRunner()

    LabelImgLauncher(runner=runner, environment={"PATH": "base"}).launch(
        LabelImgConfig(
            python_path=python_path,
            image_dir=image_dir,
            label_dir=label_dir,
            classes_file=classes_file,
        )
    )

    assert_labelimg_wrapper_launch(
        runner,
        python_path,
        "yolo",
        [image_dir, classes_file, label_dir],
    )
    wrapper = labelimg_wrapper_script(runner)
    assert "window.default_save_dir = save_dir" in wrapper
    assert "window.last_open_dir = image_dir" in wrapper
    assert "window.import_dir_images(image_dir)" in wrapper
    assert runner.popen_envs[0] is not None
    popen_path = runner.popen_envs[0]["PATH"]
    assert str(python_path.parent / "Library" / "bin") in popen_path
    assert str(python_path.parent / "Scripts") in popen_path


def test_launch_voc_mode_uses_image_folder_without_label_or_classes(
    tmp_path: Path,
) -> None:
    """VOC launch opens a folder and saves Pascal VOC XML beside images."""
    python_path = make_python(tmp_path / "python.exe")
    make_labelimg_executable(python_path)
    image_dir = tmp_path / "images"
    image_dir.mkdir()
    (image_dir / "a.jpg").write_bytes(b"fake")
    runner = FakeRunner()

    LabelImgLauncher(runner=runner).launch(
        LabelImgConfig(
            python_path=python_path,
            image_dir=image_dir,
            annotation_format="voc",
        )
    )

    assert_labelimg_wrapper_launch(runner, python_path, "voc", [image_dir])
    wrapper = labelimg_wrapper_script(runner)
    assert "default_class_file" in wrapper
    assert "window.default_save_dir = image_dir" in wrapper
    assert "window.last_open_dir = image_dir" in wrapper
    assert "window.import_dir_images(image_dir)" in wrapper
    assert "window.default_save_dir = None" not in wrapper
    assert "image_dir, default_class_file, image_dir" not in wrapper
    assert not (image_dir / "classes.txt").exists()


def test_launch_copies_classes_file_beside_yolo_labels(
    tmp_path: Path,
) -> None:
    """launch prepares LabelImg's required label-dir classes.txt sidecar."""
    python_path = make_python(tmp_path / "python.exe")
    make_labelimg_executable(python_path)
    image_dir = tmp_path / "images"
    label_dir = tmp_path / "run" / "labels"
    classes_file = tmp_path / "run" / "classes.txt"
    image_dir.mkdir()
    (image_dir / "a.jpg").write_bytes(b"fake")
    classes_file.parent.mkdir()
    classes_file.write_text("CodeA\nCodeB\n", encoding="utf-8")

    LabelImgLauncher(runner=FakeRunner()).launch(
        LabelImgConfig(
            python_path=python_path,
            image_dir=image_dir,
            label_dir=label_dir,
            classes_file=classes_file,
        )
    )

    assert (label_dir / "classes.txt").read_text(encoding="utf-8") == "CodeA\nCodeB\n"


def test_launch_rejects_image_dir_with_no_readable_images(
    tmp_path: Path,
) -> None:
    """launch fails before opening a blank LabelImg window for unsupported images."""
    python_path = make_python(tmp_path / "python.exe")
    make_labelimg_executable(python_path)
    image_dir = tmp_path / "images"
    image_dir.mkdir()
    (image_dir / "a.jpg").write_bytes(b"fake")
    label_dir = tmp_path / "labels"
    classes_file = tmp_path / "classes.txt"
    classes_file.write_text("CodeA\n", encoding="utf-8")
    runner = FakeRunner()
    runner.image_formats_result = FakeCompletedProcess(returncode=0, stdout="png,bmp\n")

    with pytest.raises(LabelImgLaunchError) as exc_info:
        LabelImgLauncher(runner=runner).launch(
            LabelImgConfig(
                python_path=python_path,
                image_dir=image_dir,
                label_dir=label_dir,
                classes_file=classes_file,
            )
        )

    assert "readable" in exc_info.value.message
    assert runner.popen_calls == []


def test_launch_creates_missing_explicit_label_dir(tmp_path: Path) -> None:
    """launch creates label_dir because it is an output directory."""
    python_path = make_python(tmp_path / "python.exe")
    make_labelimg_executable(python_path)
    image_dir = tmp_path / "images"
    label_dir = tmp_path / "labels"
    classes_file = tmp_path / "classes.txt"
    image_dir.mkdir()
    (image_dir / "a.jpg").write_bytes(b"fake")
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
    label_dir = tmp_path / "labels"
    image_dir.mkdir()

    with pytest.raises(LabelImgLaunchError) as exc_info:
        LabelImgLauncher(runner=FakeRunner()).launch(
            LabelImgConfig(
                python_path=python_path,
                image_dir=image_dir,
                label_dir=label_dir,
                classes_file=tmp_path / "classes.txt",
            )
        )

    assert exc_info.value.code == ErrorCode.LABELIMG_LAUNCH


def test_launch_empty_classes_file_raises_launch_error(tmp_path: Path) -> None:
    """launch blocks empty classes files before starting LabelImg."""
    python_path = make_python(tmp_path / "python.exe")
    image_dir = tmp_path / "images"
    label_dir = tmp_path / "labels"
    image_dir.mkdir()
    classes_file = tmp_path / "classes.txt"
    classes_file.write_text(" \n", encoding="utf-8")

    with pytest.raises(LabelImgLaunchError) as exc_info:
        LabelImgLauncher(runner=FakeRunner()).launch(
            LabelImgConfig(
                python_path=python_path,
                image_dir=image_dir,
                label_dir=label_dir,
                classes_file=classes_file,
            )
        )

    assert exc_info.value.code == ErrorCode.LABELIMG_LAUNCH


def test_launch_raises_not_installed_when_validation_command_fails(
    tmp_path: Path,
) -> None:
    """launch checks LabelImg installation before starting the GUI."""
    python_path = make_python(tmp_path / "python.exe")
    image_dir = tmp_path / "images"
    label_dir = tmp_path / "labels"
    classes_file = tmp_path / "classes.txt"
    image_dir.mkdir()
    (image_dir / "a.jpg").write_bytes(b"fake")
    classes_file.write_text("CodeA\n", encoding="utf-8")
    runner = FakeRunner()

    with pytest.raises(LabelImgNotInstalledError) as exc_info:
        LabelImgLauncher(runner=runner).launch(
            LabelImgConfig(
                python_path=python_path,
                image_dir=image_dir,
                label_dir=label_dir,
                classes_file=classes_file,
            )
        )

    assert exc_info.value.code == ErrorCode.LABELIMG_NOT_INSTALLED
    assert runner.popen_calls == []


def test_launch_popen_failure_raises_launch_error(tmp_path: Path) -> None:
    """process start failures are mapped to LabelImgLaunchError."""
    python_path = make_python(tmp_path / "python.exe")
    make_labelimg_executable(python_path)
    image_dir = tmp_path / "images"
    label_dir = tmp_path / "labels"
    classes_file = tmp_path / "classes.txt"
    image_dir.mkdir()
    (image_dir / "a.jpg").write_bytes(b"fake")
    classes_file.write_text("CodeA\n", encoding="utf-8")
    runner = FakeRunner()
    runner.popen_error = OSError("boom")

    with pytest.raises(LabelImgLaunchError) as exc_info:
        LabelImgLauncher(runner=runner).launch(
            LabelImgConfig(
                python_path=python_path,
                image_dir=image_dir,
                label_dir=label_dir,
                classes_file=classes_file,
            )
        )

    assert exc_info.value.code == ErrorCode.LABELIMG_LAUNCH
    assert "boom" in str(exc_info.value.details)
