"""Tests for LabelImg HTTP routes."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from fastapi.testclient import TestClient

from api.main import create_app
from core.labelimg_launcher import LabelImgLaunchResult, LabelImgValidateResult
from utils.exceptions import ErrorCode
from utils.task_registry import TaskRegistry


@dataclass
class FakeLauncher:
    """Fake LabelImgLauncher for route tests."""

    validate_result: LabelImgValidateResult = LabelImgValidateResult(
        is_valid=True,
        labelimg_version="labelImg 1.8.6",
        python_version="Python 3.11.14",
        error_message=None,
    )
    launch_result: LabelImgLaunchResult = LabelImgLaunchResult(process_id=1234, command="python -m labelImg")

    def validate(self, config: object) -> LabelImgValidateResult:
        """Return a configured validation result."""
        return self.validate_result

    def launch(self, config: object) -> LabelImgLaunchResult:
        """Return a configured launch result."""
        return self.launch_result


def make_client(registry: TaskRegistry, launcher: FakeLauncher | None = None) -> TestClient:
    """Create a test client from the main API app."""
    app = create_app(task_registry=registry)
    if launcher is not None:
        app.state.labelimg_launcher = launcher
    return TestClient(app)


def make_python(path: Path) -> Path:
    """Create a fake Python executable file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("python", encoding="utf-8")
    return path


def test_labelimg_validate_route_returns_probe_result(tmp_path: Path) -> None:
    """Validate route returns the non-throwing core validation result."""
    registry = TaskRegistry(tmp_path / "tasks")
    client = make_client(registry, FakeLauncher())
    python_path = make_python(tmp_path / "python.exe")

    response = client.post("/api/labelimg/validate", json={"pythonPath": str(python_path)})

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["task"]["status"] == "succeeded"
    assert payload["result"]["isValid"] is True
    assert payload["result"]["pythonVersion"] == "Python 3.11.14"
    assert registry.get(payload["task"]["taskId"]).status == "succeeded"


def test_labelimg_launch_route_returns_process_metadata(tmp_path: Path) -> None:
    """Launch route returns command metadata from the core launcher."""
    registry = TaskRegistry(tmp_path / "tasks")
    client = make_client(registry, FakeLauncher())
    python_path = make_python(tmp_path / "python.exe")
    image_dir = tmp_path / "images"
    image_dir.mkdir()

    response = client.post(
        "/api/labelimg/launch",
        json={"pythonPath": str(python_path), "imageDir": str(image_dir)},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["result"]["processId"] == 1234
    assert payload["result"]["command"] == "python -m labelImg"


def test_labelimg_validate_route_maps_missing_python_to_invalid_result(tmp_path: Path) -> None:
    """Validate route succeeds with invalid result when Python path is absent."""
    registry = TaskRegistry(tmp_path / "tasks")
    client = make_client(registry)

    response = client.post("/api/labelimg/validate", json={"pythonPath": str(tmp_path / "missing.exe")})

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["result"]["isValid"] is False
    assert payload["result"]["errorMessage"] is not None


def test_labelimg_launch_route_maps_business_errors_to_json(tmp_path: Path) -> None:
    """Launch route raises core launch errors as stable JSON errors."""
    registry = TaskRegistry(tmp_path / "tasks")
    client = make_client(registry)

    response = client.post(
        "/api/labelimg/launch",
        json={"pythonPath": str(tmp_path / "missing.exe"), "imageDir": str(tmp_path / "images")},
    )

    assert response.status_code == 400
    payload = response.json()
    assert payload["success"] is False
    assert payload["error"]["code"] == ErrorCode.LABELIMG_PYTHON_NOT_FOUND.value
