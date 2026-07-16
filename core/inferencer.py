"""YOLO inference module."""

from __future__ import annotations

import importlib
import json
import shutil
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Protocol, SupportsFloat, SupportsIndex, cast

from loguru import logger

from utils.device import get_optimal_batch_size, resolve_device
from utils.exceptions import (
    AutoLabelerError,
    ErrorCode,
    PathNotFoundError,
    TaskCancelledError,
)
from utils.mapping_manager import MappedImage, MappingManager
from utils.task_registry import TaskHandle

_VALID_IMAGE_SOURCES = {"unsampled", "all", "custom", "folder"}
_SUPPORTED_IMAGE_SUFFIXES = (".jpg", ".jpeg", ".png", ".bmp")


class _YoloModel(Protocol):
    """Minimal YOLO prediction protocol."""

    def predict(self, **kwargs: Any) -> list[object]:
        """Run model prediction."""


@dataclass(frozen=True)
class InferConfig:
    """Inferencer input contract."""

    model_path: Path
    site_folder: Path
    output_base_dir: Path | None = None
    confidence: float = 0.25
    iou: float = 0.7
    batch_size: int = -1
    device: str = "auto"
    save_to_separate_dir: bool = True
    image_source: str = "unsampled"
    custom_images: list[Path] | None = None
    image_folder: Path | None = None
    overwrite_output: bool = False
    label_y_offset_px: float = 0.0


@dataclass(frozen=True)
class InferStatistics:
    """Aggregate inference counters."""

    pending: int
    processed: int
    success: int
    failed: int
    predicted: int
    empty_prediction: int


@dataclass(frozen=True)
class InferResult:
    """Inferencer output contract."""

    mapping_path: Path | None
    run_id: str
    inference_output_dir: Path
    config_path: Path
    classes_path: Path | None
    statistics: InferStatistics


@dataclass(frozen=True)
class _InferTarget:
    """One image selected for inference."""

    image_path: Path
    output_relative: Path
    mapping_key: str | None


class InferencerError(AutoLabelerError):
    """Base class for inferencer business errors."""

    code = ErrorCode.INTERNAL_ERROR


class InferModelNotFoundError(InferencerError):
    """Raised when the model file does not exist."""

    code = ErrorCode.INFER_MODEL_NOT_FOUND


class InferModelLoadError(InferencerError):
    """Raised when the model cannot be loaded or used."""

    code = ErrorCode.INFER_MODEL_LOAD


class InferImageNotFoundError(InferencerError):
    """Raised when required inference images are missing."""

    code = ErrorCode.INFER_IMAGE_NOT_FOUND


class InferDeviceUnavailableError(InferencerError):
    """Raised when the requested inference device is unavailable."""

    code = ErrorCode.INFER_DEVICE_UNAVAILABLE


class Inferencer:
    """Run YOLO inference and write reviewable label outputs."""

    def __init__(
        self,
        mapping_manager: MappingManager | None = None,
        task_handle: TaskHandle | None = None,
        progress_callback: Callable[[int, int, str], None] | None = None,
    ) -> None:
        """Create an inferencer with optional mapping and task dependencies.

        Args:
            mapping_manager: Optional mapping manager for tests or callers.
            task_handle: Optional task state used for progress and cancellation.
            progress_callback: Optional callback for persisting/reporting progress.
        """
        self._mapping_manager = mapping_manager
        self._task_handle = task_handle
        self._progress_callback = progress_callback

    def infer(self, config: InferConfig) -> InferResult:
        """Run inference for mapped or custom images.

        Args:
            config: Inference configuration.

        Returns:
            Output run metadata and aggregate statistics.

        Raises:
            InferModelNotFoundError: If model_path does not exist.
            InferModelLoadError: If model loading or prediction fails.
            InferImageNotFoundError: If selected images are unavailable.
            InferDeviceUnavailableError: If device resolution fails.
            TaskCancelledError: If the injected task requests cancellation.
        """
        self._validate_model(config.model_path)
        device = self._resolve_device(config.device)
        batch_size = _resolve_batch_size(config, device)
        mapping_path = config.site_folder / ".autolabeler" / "mapping.json"
        manager: MappingManager | None = None
        targets: list[_InferTarget]
        if config.image_source == "custom":
            targets = self._custom_targets(config.custom_images, config.site_folder)
        elif config.image_source == "folder":
            targets = self._folder_targets(config.image_folder)
        else:
            manager = self._load_mapping(config, mapping_path)
            targets = self._mapping_targets(config, manager)

        self._raise_if_cancelled()
        model = self._load_model(config.model_path)
        run_id = _run_id()
        output_base_dir = (
            config.output_base_dir
            or config.site_folder / ".autolabeler" / "inference_results"
        )
        output_dir = (
            output_base_dir / run_id if config.save_to_separate_dir else output_base_dir
        )
        if output_dir.exists() and any(output_dir.iterdir()) and not config.overwrite_output:
            raise InferImageNotFoundError(
                "inference output directory is not empty", details=str(output_dir)
            )
        if output_dir.exists() and config.overwrite_output:
            shutil.rmtree(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        self._set_progress(0, len(targets), "准备推理")

        logger.info("开始推理: {} 张图片", len(targets))
        labels_dir = output_dir / "labels"
        statistics = self._predict_and_write_outputs(
            labels_dir, targets, model, config, device, batch_size
        )
        classes_path = _write_model_classes(output_dir, model)
        if manager is not None:
            manager.mark_inferred(
                [
                    target.mapping_key
                    for target in targets
                    if target.mapping_key is not None
                ]
            )
            manager.save(mapping_path)
        config_path = output_dir / "inference_config.json"
        _write_config_snapshot(
            config_path, config, run_id, device, batch_size, statistics
        )
        self._set_progress(statistics.processed, statistics.pending, "推理完成")
        return InferResult(
            mapping_path=mapping_path if manager is not None else None,
            run_id=run_id,
            inference_output_dir=output_dir,
            config_path=config_path,
            classes_path=classes_path,
            statistics=statistics,
        )

    def _validate_model(self, model_path: Path) -> None:
        """Validate model file existence."""
        if not model_path.exists() or not model_path.is_file():
            raise InferModelNotFoundError("模型文件不存在", details=str(model_path))

    def _resolve_device(self, requested: str) -> str:
        """Resolve inference device or raise an inferencer-specific error."""
        try:
            return resolve_device(requested)
        except AutoLabelerError as exc:
            raise InferDeviceUnavailableError(
                "推理设备不可用", details=str(exc)
            ) from exc

    def _load_model(self, model_path: Path) -> _YoloModel:
        """Load YOLO model and wrap load failures."""
        try:
            return _load_yolo_model(model_path)
        except Exception as exc:
            raise InferModelLoadError("模型加载失败", details=str(exc)) from exc

    def _load_mapping(self, config: InferConfig, mapping_path: Path) -> MappingManager:
        """Load mapping for non-custom inference modes."""
        if config.image_source not in _VALID_IMAGE_SOURCES:
            raise InferImageNotFoundError("图片来源无效", details=config.image_source)
        manager = self._mapping_manager or MappingManager(mapping_path)
        manager.mapping_path = mapping_path
        try:
            return manager.load()
        except PathNotFoundError as exc:
            raise InferImageNotFoundError(
                "mapping.json 不存在", details=str(mapping_path)
            ) from exc

    def _mapping_targets(
        self, config: InferConfig, manager: MappingManager
    ) -> list[_InferTarget]:
        """Select mapped images for inference."""
        if config.image_source == "unsampled":
            mapped_images = manager.get_pending_inference_images()
        elif config.image_source == "all":
            mapped_images = [
                MappedImage(key, value) for key, value in manager.data.images.items()
            ]
        else:
            raise InferImageNotFoundError("图片来源无效", details=config.image_source)
        targets: list[_InferTarget] = []
        for mapped in mapped_images:
            image_path = config.site_folder / Path(mapped.info.original_relative)
            if not image_path.exists():
                raise InferImageNotFoundError(
                    "待推理图片不存在", details=str(image_path)
                )
            targets.append(
                _InferTarget(
                    image_path=image_path,
                    output_relative=Path(mapped.info.code)
                    / mapped.info.product
                    / f"{Path(mapped.info.original_name).stem}.txt",
                    mapping_key=mapped.encoded_name,
                )
            )
        return targets

    def _custom_targets(
        self, custom_images: list[Path] | None, site_folder: Path
    ) -> list[_InferTarget]:
        """Resolve custom image targets independent of mapping.json."""
        if custom_images is None:
            raise InferImageNotFoundError("custom_images 不能为空")
        targets: list[_InferTarget] = []
        for image_path in custom_images:
            if not image_path.exists() or not image_path.is_file():
                raise InferImageNotFoundError(
                    "待推理图片不存在", details=str(image_path)
                )
            targets.append(
                _InferTarget(
                    image_path=image_path,
                    output_relative=_custom_output_relative(image_path, site_folder),
                    mapping_key=None,
                )
            )
        return targets

    def _folder_targets(self, image_folder: Path | None) -> list[_InferTarget]:
        """Resolve independent folder targets without mapping.json."""
        if image_folder is None or not image_folder.exists() or not image_folder.is_dir():
            raise InferImageNotFoundError(
                "image_folder is invalid", details="" if image_folder is None else str(image_folder)
            )
        image_paths = sorted(
            path
            for path in image_folder.rglob("*")
            if path.is_file() and path.suffix.lower() in _SUPPORTED_IMAGE_SUFFIXES
        )
        if not image_paths:
            raise InferImageNotFoundError(
                "image_folder contains no supported images", details=str(image_folder)
            )
        return [
            _InferTarget(
                image_path=image_path,
                output_relative=image_path.relative_to(image_folder).with_suffix(".txt"),
                mapping_key=None,
            )
            for image_path in image_paths
        ]

    def _predict_and_write_outputs(
        self,
        output_dir: Path,
        targets: list[_InferTarget],
        model: _YoloModel,
        config: InferConfig,
        device: str,
        batch_size: int,
    ) -> InferStatistics:
        """Run YOLO in bounded chunks and write prediction TXT files."""
        success = 0
        failed = 0
        predicted = 0
        empty_prediction = 0
        for start in range(0, len(targets), batch_size):
            self._raise_if_cancelled()
            chunk = targets[start : start + batch_size]
            try:
                results = model.predict(
                    source=[str(target.image_path) for target in chunk],
                    conf=config.confidence,
                    iou=config.iou,
                    device=device,
                    batch=batch_size,
                    save=False,
                    verbose=False,
                )
            except Exception as exc:
                raise InferModelLoadError("模型推理失败", details=str(exc)) from exc
            for offset, target in enumerate(chunk):
                self._raise_if_cancelled()
                result = results[offset] if offset < len(results) else None
                output_path = output_dir / target.output_relative
                output_path.parent.mkdir(parents=True, exist_ok=True)
                lines = _prediction_lines(result, config.label_y_offset_px)
                output_path.write_text(
                    "".join(f"{line}\n" for line in lines), encoding="utf-8"
                )
                if lines:
                    predicted += 1
                else:
                    empty_prediction += 1
                success += 1
                self._set_progress(success, len(targets), f"已推理 {success}/{len(targets)}")
        return InferStatistics(
            pending=len(targets),
            processed=success + failed,
            success=success,
            failed=failed,
            predicted=predicted,
            empty_prediction=empty_prediction,
        )

    def _raise_if_cancelled(self) -> None:
        """Raise TaskCancelledError when the injected task has been cancelled."""
        if self._task_handle is not None and self._task_handle.is_cancel_requested:
            logger.warning("推理任务已取消")
            raise TaskCancelledError("推理任务已取消")

    def _set_progress(self, current: int, total: int, message: str) -> None:
        """Update task progress fields when a task handle is available."""
        if self._task_handle is not None:
            self._task_handle.progress_current = current
            self._task_handle.progress_total = total
            self._task_handle.progress_message = message
        if self._progress_callback is not None:
            self._progress_callback(current, total, message)


def _load_yolo_model(model_path: Path) -> _YoloModel:
    """Load an Ultralytics YOLO model lazily."""
    module = importlib.import_module("ultralytics")
    yolo_class = getattr(module, "YOLO")
    return cast(_YoloModel, yolo_class(str(model_path)))


def _write_model_classes(output_dir: Path, model: _YoloModel) -> Path | None:
    """Write model class names beside one inference run when available."""
    names = getattr(model, "names", None)
    if names is None:
        return None
    class_names = _model_class_names(names)
    if not class_names:
        return None
    classes_path = output_dir / "classes.txt"
    classes_path.write_text(
        "".join(f"{name}\n" for name in class_names), encoding="utf-8"
    )
    return classes_path


def _model_class_names(names: object) -> list[str]:
    """Normalize common Ultralytics class-name containers."""
    if isinstance(names, dict):
        if not names:
            return []
        max_index = max(int(index) for index in names)
        return [str(names.get(index, "")) for index in range(max_index + 1)]
    if isinstance(names, (list, tuple)):
        return [str(name) for name in names]
    return []


def _run_id() -> str:
    """Create a timestamped inference run id."""
    return datetime.now().strftime("run_%Y%m%d_%H%M%S")


def _resolve_batch_size(config: InferConfig, device: str) -> int:
    """Resolve effective inference batch size."""
    if config.batch_size == -1:
        return max(1, get_optimal_batch_size(device))
    return max(1, config.batch_size)


def _custom_output_relative(image_path: Path, site_folder: Path) -> Path:
    """Return custom inference output path, preserving direct Code/Product layout."""
    try:
        relative = image_path.relative_to(site_folder)
    except ValueError:
        return Path(f"{image_path.stem}.txt")
    if len(relative.parts) == 3:
        return Path(relative.parts[0]) / relative.parts[1] / f"{image_path.stem}.txt"
    return Path(f"{image_path.stem}.txt")


def _prediction_lines(result: object, label_y_offset_px: float = 0.0) -> list[str]:
    """Convert a YOLO prediction result object to YOLO TXT lines."""
    boxes = [] if result is None else getattr(result, "boxes", [])
    lines: list[str] = []
    for box in boxes:
        class_id = int(_scalar(getattr(box, "cls", 0)))
        xywhn = getattr(box, "xywhn", (0.0, 0.0, 0.0, 0.0))
        values = _xywhn_values(xywhn)
        if label_y_offset_px:
            values = _shift_y_center(values, label_y_offset_px, result)
        lines.append(
            f"{class_id} {values[0]:.6f} {values[1]:.6f} {values[2]:.6f} {values[3]:.6f}"
        )
    return lines


def _shift_y_center(
    values: tuple[float, float, float, float],
    offset_px: float,
    result: object,
) -> tuple[float, float, float, float]:
    """Shift normalized y-center by a pixel offset while preserving box size."""
    image_height = _result_image_height(result)
    if image_height <= 0:
        return values
    x_center, y_center, width, height = values
    shifted_y = y_center + (offset_px / image_height)
    if height >= 1:
        shifted_y = 0.5
    else:
        min_center = height / 2
        max_center = 1 - min_center
        shifted_y = min(max(shifted_y, min_center), max_center)
    return (x_center, shifted_y, width, height)


def _result_image_height(result: object) -> float:
    """Read image height from common Ultralytics result attributes."""
    orig_shape = getattr(result, "orig_shape", None)
    if isinstance(orig_shape, (list, tuple)) and orig_shape:
        return float(orig_shape[0])
    orig_img = getattr(result, "orig_img", None)
    shape = getattr(orig_img, "shape", None)
    if isinstance(shape, (list, tuple)) and shape:
        return float(shape[0])
    return 0.0


def _xywhn_values(value: object) -> tuple[float, float, float, float]:
    """Extract four normalized bbox values from common result shapes."""
    if hasattr(value, "tolist"):
        value = value.tolist()
    if isinstance(value, list) and value and isinstance(value[0], list):
        value = value[0]
    if isinstance(value, tuple) and value and isinstance(value[0], tuple):
        value = value[0]
    sequence = list(value) if isinstance(value, (list, tuple)) else [0.0, 0.0, 0.0, 0.0]
    return (
        float(sequence[0]),
        float(sequence[1]),
        float(sequence[2]),
        float(sequence[3]),
    )


def _scalar(value: object) -> float:
    """Extract one scalar from tensors, lists, or plain numbers."""
    if hasattr(value, "item"):
        value = value.item()
    if hasattr(value, "tolist"):
        value = value.tolist()
    if isinstance(value, (list, tuple)):
        return _scalar(value[0])
    if isinstance(value, (str, bytes, bytearray)) or isinstance(
        value, (SupportsFloat, SupportsIndex)
    ):
        return float(value)
    raise TypeError(f"Cannot convert {type(value).__name__} to float")


def _write_config_snapshot(
    config_path: Path,
    config: InferConfig,
    run_id: str,
    device: str,
    batch_size: int,
    statistics: InferStatistics,
) -> None:
    """Write inference_config.json."""
    payload = {
        "run_id": run_id,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "mode": "independent" if config.image_source in {"custom", "folder"} else "flow",
        "source_mode": config.image_source,
        "image_root": str(config.image_folder or config.site_folder),
        "model_path": str(config.model_path),
        "confidence": config.confidence,
        "iou": config.iou,
        "device": device,
        "batch_size": batch_size,
        "label_y_offset_px": config.label_y_offset_px,
        "image_count": statistics.pending,
        "predicted_count": statistics.predicted,
        "empty_prediction_count": statistics.empty_prediction,
    }
    config_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
