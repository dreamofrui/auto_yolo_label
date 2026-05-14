"""Tests for the YOLO inference core module."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from core.inferencer import (
    InferConfig,
    InferDeviceUnavailableError,
    InferImageNotFoundError,
    InferModelLoadError,
    InferModelNotFoundError,
    Inferencer,
)
from utils.exceptions import TaskCancelledError
from utils.mapping_manager import ImageInfo, MappingManager
from utils.path_encoder import PathEncoder
from utils.task_registry import TaskHandle


@dataclass
class FakeBox:
    """Minimal predicted YOLO box."""

    cls: int
    xywhn: tuple[float, float, float, float]


@dataclass
class FakeResult:
    """Minimal Ultralytics prediction result."""

    boxes: list[FakeBox]


class FakeYOLO:
    """Fake YOLO model for inference tests."""

    def __init__(self, results: list[FakeResult]) -> None:
        """Create fake model with fixed results."""
        self.results = results
        self.predict_kwargs: dict[str, Any] | None = None

    def predict(self, **kwargs: Any) -> list[FakeResult]:
        """Return configured fake results."""
        self.predict_kwargs = kwargs
        return self.results


def make_task_handle(cancelled: bool = False) -> TaskHandle:
    """Create an in-memory inference task handle."""
    return TaskHandle(
        task_id="task_infer_test",
        task_type="infer",
        status="running",
        progress_current=0,
        progress_total=0,
        progress_message="",
        logs=[],
        result=None,
        error=None,
        created_at="2026-05-13 00:00:00",
        started_at="2026-05-13 00:00:00",
        finished_at=None,
        is_cancel_requested=cancelled,
    )


def make_image(path: Path) -> None:
    """Create a lightweight image placeholder."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"image")


def make_mapping(
    site: Path, sampled: bool = False, inferred: bool = False
) -> MappingManager:
    """Create a mapping with two images."""
    encoder = PathEncoder()
    manager = MappingManager(site / ".autolabeler" / "mapping.json").create_new(site)
    manager.add_class(0, "CodeA")
    for index, name in enumerate(("a1.jpg", "a2.jpg"), start=1):
        image_path = site / "CodeA" / "Product1" / name
        make_image(image_path)
        info = ImageInfo(
            original_relative=image_path.relative_to(site).as_posix(),
            code="CodeA",
            product="Product1",
            original_name=name,
            format=".jpg",
            sampled=sampled if index == 1 else False,
            inferred=inferred,
        )
        manager.add_image(encoder.encode("CodeA", "Product1", name), info)
    manager.save()
    return manager


def test_inferencer_constructs_successfully() -> None:
    """Inferencer can be constructed with default dependencies."""
    inferencer = Inferencer()

    assert isinstance(inferencer, Inferencer)


def test_custom_inference_writes_predictions_and_empty_files(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Custom image inference writes one TXT per input image, including empty predictions."""
    model_path = tmp_path / "model.pt"
    model_path.write_bytes(b"model")
    image_one = tmp_path / "custom" / "one.jpg"
    image_two = tmp_path / "custom" / "two.jpg"
    make_image(image_one)
    make_image(image_two)
    fake = FakeYOLO([FakeResult([FakeBox(0, (0.5, 0.5, 0.25, 0.25))]), FakeResult([])])
    monkeypatch.setattr("core.inferencer._load_yolo_model", lambda path: fake)
    monkeypatch.setattr("core.inferencer._run_id", lambda: "run_20260513_103000")

    result = Inferencer().infer(
        InferConfig(
            model_path=model_path,
            site_folder=tmp_path / "site",
            output_base_dir=tmp_path / "runs",
            image_source="custom",
            custom_images=[image_one, image_two],
            batch_size=2,
            device="cpu",
        )
    )

    assert result.run_id == "run_20260513_103000"
    assert result.statistics.pending == 2
    assert result.statistics.success == 2
    assert result.statistics.predicted == 1
    assert result.statistics.empty_prediction == 1
    assert (result.inference_output_dir / "one.txt").read_text(
        encoding="utf-8"
    ).strip() == "0 0.500000 0.500000 0.250000 0.250000"
    assert (result.inference_output_dir / "two.txt").read_text(encoding="utf-8") == ""
    assert result.config_path.exists()
    assert fake.predict_kwargs is not None
    assert fake.predict_kwargs["conf"] == 0.25
    assert fake.predict_kwargs["iou"] == 0.7


def test_unsampled_mapping_inference_marks_inferred_and_ignores_inferred_filter(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Unsampled mapping selection ignores existing inferred flags and marks images inferred again."""
    site = tmp_path / "site"
    make_mapping(site, sampled=False, inferred=True)
    model_path = tmp_path / "model.pt"
    model_path.write_bytes(b"model")
    monkeypatch.setattr(
        "core.inferencer._load_yolo_model",
        lambda path: FakeYOLO([FakeResult([]), FakeResult([])]),
    )
    monkeypatch.setattr("core.inferencer._run_id", lambda: "run_20260513_103000")

    result = Inferencer().infer(
        InferConfig(model_path=model_path, site_folder=site, device="cpu")
    )

    assert result.statistics.pending == 2
    mapping = MappingManager(result.mapping_path).load()
    assert mapping.get_statistics()["inferred_count"] == 2
    assert (result.inference_output_dir / "CodeA" / "Product1" / "a1.txt").exists()


def test_all_mapping_inference_includes_sampled_images(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """image_source='all' includes sampled and unsampled mapped images."""
    site = tmp_path / "site"
    make_mapping(site, sampled=True)
    model_path = tmp_path / "model.pt"
    model_path.write_bytes(b"model")
    monkeypatch.setattr(
        "core.inferencer._load_yolo_model",
        lambda path: FakeYOLO([FakeResult([]), FakeResult([])]),
    )

    result = Inferencer().infer(
        InferConfig(
            model_path=model_path, site_folder=site, image_source="all", device="cpu"
        )
    )

    assert result.statistics.pending == 2


def test_missing_mapping_for_unsampled_raises_image_error(tmp_path: Path) -> None:
    """Non-custom inference requires mapping.json."""
    model_path = tmp_path / "model.pt"
    model_path.write_bytes(b"model")
    (tmp_path / "site").mkdir()

    with pytest.raises(InferImageNotFoundError):
        Inferencer().infer(
            InferConfig(model_path=model_path, site_folder=tmp_path / "site")
        )


def test_missing_custom_image_raises_image_error(tmp_path: Path) -> None:
    """Custom image lists validate every image path."""
    model_path = tmp_path / "model.pt"
    model_path.write_bytes(b"model")

    with pytest.raises(InferImageNotFoundError):
        Inferencer().infer(
            InferConfig(
                model_path=model_path,
                site_folder=tmp_path / "site",
                image_source="custom",
                custom_images=[tmp_path / "missing.jpg"],
            )
        )


def test_missing_model_raises_model_not_found(tmp_path: Path) -> None:
    """Missing model files raise a model-not-found error."""
    with pytest.raises(InferModelNotFoundError):
        Inferencer().infer(
            InferConfig(
                model_path=tmp_path / "missing.pt",
                site_folder=tmp_path / "site",
                image_source="custom",
                custom_images=[],
            )
        )


def test_model_load_failure_raises_model_load(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Model loader failures are wrapped as InferModelLoadError."""
    model_path = tmp_path / "model.pt"
    model_path.write_bytes(b"model")
    monkeypatch.setattr(
        "core.inferencer._load_yolo_model",
        lambda path: (_ for _ in ()).throw(RuntimeError("bad model")),
    )

    with pytest.raises(InferModelLoadError):
        Inferencer().infer(
            InferConfig(
                model_path=model_path,
                site_folder=tmp_path / "site",
                image_source="custom",
                custom_images=[],
            )
        )


def test_invalid_device_raises_device_unavailable(tmp_path: Path) -> None:
    """Invalid device values map to InferDeviceUnavailableError."""
    model_path = tmp_path / "model.pt"
    model_path.write_bytes(b"model")

    with pytest.raises(InferDeviceUnavailableError):
        Inferencer().infer(
            InferConfig(
                model_path=model_path,
                site_folder=tmp_path / "site",
                image_source="custom",
                custom_images=[],
                device="bad-device",
            )
        )


def test_task_handle_progress_updates(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Inference updates progress on the injected task handle."""
    model_path = tmp_path / "model.pt"
    model_path.write_bytes(b"model")
    image_path = tmp_path / "custom" / "one.jpg"
    make_image(image_path)
    handle = make_task_handle()
    monkeypatch.setattr(
        "core.inferencer._load_yolo_model", lambda path: FakeYOLO([FakeResult([])])
    )

    Inferencer(task_handle=handle).infer(
        InferConfig(
            model_path=model_path,
            site_folder=tmp_path / "site",
            image_source="custom",
            custom_images=[image_path],
            device="cpu",
        )
    )

    assert handle.progress_current == 1
    assert handle.progress_total == 1
    assert handle.progress_message


def test_cancelled_task_raises_task_cancelled(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Pre-requested cancellation raises before prediction starts."""
    model_path = tmp_path / "model.pt"
    model_path.write_bytes(b"model")
    image_path = tmp_path / "custom" / "one.jpg"
    make_image(image_path)
    handle = make_task_handle(cancelled=True)
    monkeypatch.setattr(
        "core.inferencer._load_yolo_model", lambda path: FakeYOLO([FakeResult([])])
    )

    with pytest.raises(TaskCancelledError):
        Inferencer(task_handle=handle).infer(
            InferConfig(
                model_path=model_path,
                site_folder=tmp_path / "site",
                image_source="custom",
                custom_images=[image_path],
                device="cpu",
            )
        )
