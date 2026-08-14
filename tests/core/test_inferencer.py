"""Tests for the YOLO inference core module."""

from __future__ import annotations

from dataclasses import dataclass
import json
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

    def __init__(
        self,
        results: list[FakeResult],
        names: dict[int, str] | list[str] | None = None,
    ) -> None:
        """Create fake model with fixed results."""
        self.results = results
        self.names = names if names is not None else {0: "CodeA"}
        self.predict_kwargs: dict[str, Any] | None = None

    def predict(self, **kwargs: Any) -> list[FakeResult]:
        """Return configured fake results."""
        self.predict_kwargs = kwargs
        return self.results


class RecordingYOLO:
    """Fake YOLO model that records prediction chunk sizes."""

    def __init__(self) -> None:
        self.names = {0: "CodeA"}
        self.source_lengths: list[int] = []

    def predict(self, **kwargs: Any) -> list[FakeResult]:
        """Return one empty result per source image."""
        source = kwargs["source"]
        self.source_lengths.append(len(source))
        return [FakeResult([]) for _ in source]


class _CancelAfterValues:
    """Normalized box values that request cancellation after first label write."""

    def __init__(self, handle: TaskHandle) -> None:
        self._handle = handle

    def tolist(self) -> list[float]:
        self._handle.is_cancel_requested = True
        return [0.5, 0.5, 0.25, 0.25]


class CancelsAfterFirstBatchYOLO:
    """Fake YOLO model that requests cancellation while writing first batch."""

    def __init__(self, handle: TaskHandle) -> None:
        self.names = {0: "CodeA"}
        self.handle = handle
        self.calls = 0

    def predict(self, **kwargs: Any) -> list[FakeResult]:
        """Return one result whose serialization requests cancellation."""
        self.calls += 1
        return [FakeResult([FakeBox(0, _CancelAfterValues(self.handle))])]


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
    assert (result.inference_output_dir / "labels" / "one.txt").read_text(
        encoding="utf-8"
    ).strip() == "0 0.500000 0.500000 0.250000 0.250000"
    assert (result.inference_output_dir / "labels" / "two.txt").read_text(
        encoding="utf-8"
    ) == ""
    assert result.config_path.exists()
    assert result.config_path == result.inference_output_dir / "inference_config.json"
    assert fake.predict_kwargs is not None
    assert fake.predict_kwargs["conf"] == 0.25
    assert fake.predict_kwargs["iou"] == 0.7


def test_inference_can_shift_prediction_labels_down_by_pixels(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Optional label y-offset moves the box down without changing box size."""
    model_path = tmp_path / "model.pt"
    model_path.write_bytes(b"model")
    image = tmp_path / "custom" / "one.jpg"
    make_image(image)
    result = FakeResult([FakeBox(0, (0.5, 0.5, 0.2, 0.1))])
    result.orig_shape = (100, 200)
    fake = FakeYOLO([result])
    monkeypatch.setattr("core.inferencer._load_yolo_model", lambda path: fake)
    monkeypatch.setattr("core.inferencer._run_id", lambda: "run_20260528_090000")

    output = Inferencer().infer(
        InferConfig(
            model_path=model_path,
            site_folder=tmp_path / "site",
            output_base_dir=tmp_path / "runs",
            image_source="custom",
            custom_images=[image],
            batch_size=1,
            device="cpu",
            label_y_offset_px=5,
        )
    )

    assert (output.inference_output_dir / "labels" / "one.txt").read_text(
        encoding="utf-8"
    ).strip() == "0 0.500000 0.550000 0.200000 0.100000"


def test_folder_inference_preserves_relative_structure_under_labels(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Independent folder inference recursively writes labels without mapping."""
    model_path = tmp_path / "model.pt"
    model_path.write_bytes(b"model")
    image_root = tmp_path / "images"
    make_image(image_root / "Product1" / "a.jpg")
    make_image(image_root / "Product2" / "nested" / "b.png")
    fake = FakeYOLO([FakeResult([]), FakeResult([])])
    monkeypatch.setattr("core.inferencer._load_yolo_model", lambda path: fake)
    monkeypatch.setattr("core.inferencer._run_id", lambda: "run_20260513_103000")

    result = Inferencer().infer(
        InferConfig(
            model_path=model_path,
            site_folder=tmp_path / "unused_site",
            output_base_dir=tmp_path / "runs",
            image_source="folder",
            image_folder=image_root,
            device="cpu",
        )
    )

    assert result.mapping_path is None
    assert (result.inference_output_dir / "labels" / "Product1" / "a.txt").exists()
    assert (
        result.inference_output_dir / "labels" / "Product2" / "nested" / "b.txt"
    ).exists()
    assert not (result.inference_output_dir / "Product1" / "a.txt").exists()
    assert (result.inference_output_dir / "classes.txt").read_text(
        encoding="utf-8"
    ) == "CodeA\n"
    config_data = json.loads(result.config_path.read_text(encoding="utf-8"))
    assert config_data["mode"] == "independent"
    assert config_data["image_root"] == str(image_root)


def test_independent_folder_inference_writes_model_classes_without_mapping(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Independent folder inference exports model classes without creating mapping."""
    model_path = tmp_path / "model.pt"
    model_path.write_bytes(b"model")
    image_root = tmp_path / "images"
    make_image(image_root / "a.jpg")
    fake = FakeYOLO([FakeResult([])], names={0: "scratch", 2: "dent"})
    monkeypatch.setattr("core.inferencer._load_yolo_model", lambda path: fake)
    monkeypatch.setattr("core.inferencer._run_id", lambda: "run_20260513_103000")

    result = Inferencer().infer(
        InferConfig(
            model_path=model_path,
            site_folder=tmp_path / "unused_site",
            output_base_dir=tmp_path / "runs",
            image_source="folder",
            image_folder=image_root,
            device="cpu",
        )
    )

    assert result.mapping_path is None
    assert not (image_root / ".autolabeler" / "mapping.json").exists()
    assert (result.inference_output_dir / "classes.txt").read_text(
        encoding="utf-8"
    ) == "scratch\n\ndent\n"


def test_folder_inference_predicts_in_batches_to_avoid_loading_every_image(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Folder inference sends bounded chunks to YOLO instead of all paths at once."""
    model_path = tmp_path / "model.pt"
    model_path.write_bytes(b"model")
    image_root = tmp_path / "images"
    for index in range(3):
        make_image(image_root / f"{index}.jpg")
    fake = RecordingYOLO()
    monkeypatch.setattr("core.inferencer._load_yolo_model", lambda path: fake)
    monkeypatch.setattr("core.inferencer._run_id", lambda: "run_20260513_103000")

    result = Inferencer().infer(
        InferConfig(
            model_path=model_path,
            site_folder=tmp_path / "unused_site",
            output_base_dir=tmp_path / "runs",
            image_source="folder",
            image_folder=image_root,
            batch_size=1,
            device="cpu",
        )
    )

    assert fake.source_lengths == [1, 1, 1]
    assert result.statistics.processed == 3


def test_cancelled_between_batches_does_not_start_next_predict(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cancellation requested after one batch stops before the next YOLO call."""
    model_path = tmp_path / "model.pt"
    model_path.write_bytes(b"model")
    image_root = tmp_path / "images"
    make_image(image_root / "one.jpg")
    make_image(image_root / "two.jpg")
    handle = make_task_handle()
    fake = CancelsAfterFirstBatchYOLO(handle)
    monkeypatch.setattr("core.inferencer._load_yolo_model", lambda path: fake)

    with pytest.raises(TaskCancelledError):
        Inferencer(task_handle=handle).infer(
            InferConfig(
                model_path=model_path,
                site_folder=image_root,
                output_base_dir=tmp_path / "runs",
                image_source="folder",
                image_folder=image_root,
                batch_size=1,
                device="cpu",
            )
        )

    assert fake.calls == 1


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
    assert (
        result.inference_output_dir / "labels" / "CodeA" / "Product1" / "a1.txt"
    ).exists()


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
