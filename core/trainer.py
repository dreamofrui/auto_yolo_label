"""YOLO training module."""

from __future__ import annotations

import csv
import importlib
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from math import isfinite
from pathlib import Path
from typing import Any, Protocol, cast

from loguru import logger

from utils.device import get_optimal_batch_size, resolve_device
from utils.exceptions import AutoLabelerError, ErrorCode
from utils.task_registry import TaskHandle

_REQUIRED_DATA_YAML_KEYS = ("path", "train", "val", "nc", "names")
_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp"}


class _YoloModel(Protocol):
    """Minimal YOLO model protocol used by Trainer."""

    def add_callback(self, event: str, callback: Any) -> None:
        """Register a callback for a training event."""

    def train(self, **kwargs: Any) -> object:
        """Run training and return the backend result."""


@dataclass(frozen=True)
class TrainConfig:
    """Trainer input contract."""

    data_yaml: Path
    base_model: Path
    output_dir: Path
    epochs: int = 100
    batch_size: int = -1
    image_size: int = 640
    device: str = "auto"
    patience: int = 50
    workers: int = 8
    optimizer: str = "AdamW"
    lr0: float = 0.01
    box: float = 7.5
    cls: float = 0.5
    dfl: float = 1.5
    scale: float = 0.5
    cache: str | bool = "ram"
    run_name: str | None = None
    overwrite_output: bool = False


@dataclass(frozen=True)
class TrainMetrics:
    """Training metrics extracted from YOLO results."""

    best_epoch: int
    best_map50: float
    best_map50_95: float
    final_map50: float
    final_map50_95: float


@dataclass(frozen=True)
class TrainResult:
    """Trainer output contract."""

    best_model: Path
    last_model: Path | None
    output_dir: Path
    effective_config: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    preflight: dict[str, Any] = field(default_factory=dict)
    log_file: Path | None = None
    metrics: TrainMetrics = field(
        default_factory=lambda: TrainMetrics(0, 0.0, 0.0, 0.0, 0.0)
    )


class TrainerError(AutoLabelerError):
    """Base class for trainer business errors."""

    code = ErrorCode.INTERNAL_ERROR


class TrainDataYamlInvalidError(TrainerError):
    """Raised when data.yaml is missing or invalid."""

    code = ErrorCode.TRAIN_DATA_YAML_INVALID


class TrainBaseModelNotFoundError(TrainerError):
    """Raised when the base model does not exist."""

    code = ErrorCode.TRAIN_BASE_MODEL_NOT_FOUND


class TrainDeviceUnavailableError(TrainerError):
    """Raised when the requested device cannot be used."""

    code = ErrorCode.TRAIN_DEVICE_UNAVAILABLE


class TrainOOMError(TrainerError):
    """Raised when training fails due to out-of-memory conditions."""

    code = ErrorCode.TRAIN_OOM


class TrainInterruptedError(TrainerError):
    """Raised when training is interrupted or cancelled."""

    code = ErrorCode.TRAIN_INTERRUPTED


class Trainer:
    """Train YOLO models from a data.yaml file."""

    def __init__(
        self,
        task_handle: TaskHandle | None = None,
        progress_callback: Callable[[int, int, str], None] | None = None,
    ) -> None:
        """Create a trainer with optional task state."""
        self._task_handle = task_handle
        self._progress_callback = progress_callback

    def train(self, config: TrainConfig) -> TrainResult:
        """Train a YOLO model."""
        preflight = self._validate_inputs(config)
        self._raise_if_cancelled()
        try:
            device = resolve_device(config.device)
        except AutoLabelerError as exc:
            raise TrainDeviceUnavailableError(
                "training device unavailable", details=str(exc)
            ) from exc
        batch_size = _resolve_batch_size(config, device)
        run_name = _resolve_run_name(config)
        run_dir = config.output_dir / run_name
        effective_config = _effective_config(config, device, batch_size, run_name)
        model = _load_yolo_model(config.base_model)
        self._register_progress_callback(model, config.epochs)

        logger.info(
            "Starting YOLO training: data={}, model={}",
            config.data_yaml,
            config.base_model,
        )
        try:
            model.train(
                data=str(config.data_yaml),
                model=str(config.base_model),
                project=str(config.output_dir),
                name=run_name,
                exist_ok=config.overwrite_output,
                epochs=config.epochs,
                batch=batch_size,
                imgsz=config.image_size,
                device=device,
                patience=config.patience,
                workers=config.workers,
                optimizer=config.optimizer,
                lr0=config.lr0,
                box=config.box,
                cls=config.cls,
                dfl=config.dfl,
                scale=config.scale,
                cache=config.cache,
            )
        except TrainInterruptedError:
            raise
        except KeyboardInterrupt as exc:
            raise TrainInterruptedError("training cancelled", details=str(exc)) from exc
        except RuntimeError as exc:
            if _is_oom_error(exc):
                raise TrainOOMError("training out of memory", details=str(exc)) from exc
            raise

        best_model = run_dir / "weights" / "best.pt"
        last_model = run_dir / "weights" / "last.pt"
        log_file = run_dir / "results.csv"
        metrics = _parse_metrics(log_file)
        return TrainResult(
            best_model=best_model,
            last_model=last_model if last_model.exists() else None,
            output_dir=run_dir,
            effective_config=effective_config,
            warnings=preflight["warnings"],
            preflight=preflight["stats"],
            log_file=log_file if log_file.exists() else None,
            metrics=metrics,
        )

    def _validate_inputs(self, config: TrainConfig) -> dict[str, Any]:
        """Validate training inputs and return preflight details."""
        if not config.data_yaml.exists() or not config.data_yaml.is_file():
            raise TrainDataYamlInvalidError(
                "data.yaml does not exist", details=str(config.data_yaml)
            )
        data = _parse_data_yaml(config.data_yaml.read_text(encoding="utf-8"))
        missing_keys = [key for key in _REQUIRED_DATA_YAML_KEYS if key not in data]
        if missing_keys:
            raise TrainDataYamlInvalidError(
                "data.yaml missing required fields", details=", ".join(missing_keys)
            )

        dataset_root = _resolve_dataset_path(config.data_yaml.parent, data["path"])
        classes = _parse_names(data["names"])
        nc = _parse_int(data["nc"])
        if not classes or nc <= 0:
            raise TrainDataYamlInvalidError(
                "data.yaml classes must be non-empty", details="names/nc"
            )
        if nc != len(classes):
            raise TrainDataYamlInvalidError(
                "data.yaml nc does not match classes",
                details=f"nc={nc}, names={len(classes)}",
            )

        train_images_dir = _resolve_dataset_path(dataset_root, data["train"])
        val_images_dir = _resolve_dataset_path(dataset_root, data["val"])
        train_labels_dir = _labels_dir_for_images(train_images_dir, dataset_root)
        val_labels_dir = _labels_dir_for_images(val_images_dir, dataset_root)
        _validate_standard_dataset_paths(
            dataset_root, train_images_dir, val_images_dir, train_labels_dir
        )
        train_images = _image_files(train_images_dir)
        val_images = _image_files(val_images_dir)
        if not train_images:
            raise TrainDataYamlInvalidError(
                "images/train must contain at least one image",
                details=str(train_images_dir),
            )

        label_stats = _count_train_labels(train_images, train_labels_dir, len(classes))
        if label_stats["invalid_train_label_rows"] > 0:
            raise TrainDataYamlInvalidError(
                "labels/train contains invalid YOLO label rows",
                details=str(train_labels_dir),
            )
        if label_stats["valid_train_label_rows"] < 1:
            raise TrainDataYamlInvalidError(
                "labels/train must contain at least one valid YOLO label row",
                details=str(train_labels_dir),
            )

        warnings: list[str] = []
        if not val_images:
            warnings.append("images/val is empty")
        if not _non_empty_label_files(val_labels_dir):
            warnings.append("labels/val is empty")
        if config.run_name is not None:
            _validate_fixed_output(config.output_dir / config.run_name, config)
        if not config.base_model.exists() or not config.base_model.is_file():
            raise TrainBaseModelNotFoundError(
                "base model does not exist", details=str(config.base_model)
            )

        stats = {
            "dataset_root": str(dataset_root),
            "classes": classes,
            "train_images": len(train_images),
            "val_images": len(val_images),
            **label_stats,
        }
        return {"warnings": warnings, "stats": stats}

    def _register_progress_callback(self, model: _YoloModel, total_epochs: int) -> None:
        """Register a YOLO epoch callback when supported."""

        def on_fit_epoch_end(trainer_state: Any) -> None:
            """Update progress from a YOLO epoch-end callback."""
            self._raise_if_cancelled()
            epoch = int(getattr(trainer_state, "epoch", 0)) + 1
            epochs = int(getattr(trainer_state, "epochs", total_epochs))
            metrics = getattr(trainer_state, "metrics", None)
            map50 = _metric_value(metrics, "mAP50")
            self._set_progress(
                epoch, epochs, f"Epoch {epoch}/{epochs} - mAP50: {map50:.3f}"
            )

        add_callback = getattr(model, "add_callback", None)
        if callable(add_callback):
            add_callback("on_fit_epoch_end", on_fit_epoch_end)

    def _raise_if_cancelled(self) -> None:
        """Raise TrainInterruptedError when cancellation has been requested."""
        if self._task_handle is not None and self._task_handle.is_cancel_requested:
            raise TrainInterruptedError("training cancelled")

    def _set_progress(self, current: int, total: int, message: str) -> None:
        """Update task progress fields when a task handle is available."""
        if self._task_handle is not None:
            self._task_handle.progress_current = current
            self._task_handle.progress_total = total
            self._task_handle.progress_message = message
        if self._progress_callback is not None:
            self._progress_callback(current, total, message)


def _load_yolo_model(base_model: Path) -> _YoloModel:
    """Load an Ultralytics YOLO model lazily."""
    module = importlib.import_module("ultralytics")
    yolo_class = getattr(module, "YOLO")
    return cast(_YoloModel, yolo_class(str(base_model)))


def _resolve_batch_size(config: TrainConfig, device: str) -> int:
    """Resolve the effective batch size."""
    if config.batch_size == -1:
        return max(1, get_optimal_batch_size(device, config.image_size))
    return max(1, config.batch_size)


def _effective_config(
    config: TrainConfig, device: str, batch_size: int, run_name: str
) -> dict[str, Any]:
    """Return the effective training parameters."""
    return {
        "data_yaml": str(config.data_yaml),
        "base_model": str(config.base_model),
        "output_dir": str(config.output_dir),
        "run_name": run_name,
        "overwrite_output": config.overwrite_output,
        "epochs": config.epochs,
        "batch_size": batch_size,
        "image_size": config.image_size,
        "device": device,
        "patience": config.patience,
        "workers": config.workers,
        "optimizer": config.optimizer,
        "lr0": config.lr0,
        "box": config.box,
        "cls": config.cls,
        "dfl": config.dfl,
        "scale": config.scale,
        "cache": config.cache,
    }


def _resolve_run_name(config: TrainConfig) -> str:
    """Return a fixed or available training run name."""
    if config.run_name is not None:
        return config.run_name
    default_run = config.output_dir / "train"
    if not default_run.exists() or not any(default_run.iterdir()):
        return "train"

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_name = f"train_{timestamp}"
    candidate = base_name
    counter = 1
    while (config.output_dir / candidate).exists():
        counter += 1
        candidate = f"{base_name}_{counter}"
    return candidate


def _validate_standard_dataset_paths(
    dataset_root: Path,
    train_images_dir: Path,
    val_images_dir: Path,
    train_labels_dir: Path,
) -> None:
    """Validate the first-version standard YOLO dataset layout."""
    expected_train = dataset_root / "images" / "train"
    expected_val = dataset_root / "images" / "val"
    if train_images_dir != expected_train or val_images_dir != expected_val:
        raise TrainDataYamlInvalidError(
            "data.yaml must use standard images/train and images/val paths",
            details=f"train={train_images_dir}, val={val_images_dir}",
        )
    if not train_labels_dir.exists() or not train_labels_dir.is_dir():
        raise TrainDataYamlInvalidError(
            "labels/train directory does not exist", details=str(train_labels_dir)
        )


def _validate_fixed_output(run_dir: Path, config: TrainConfig) -> None:
    """Reject non-empty fixed output dirs unless overwrite is confirmed."""
    if run_dir.exists() and any(run_dir.iterdir()) and not config.overwrite_output:
        raise TrainDataYamlInvalidError(
            "output directory is non-empty; confirm overwrite",
            details=str(run_dir),
        )


def _parse_data_yaml(text: str) -> dict[str, str]:
    """Parse the small data.yaml subset this module needs."""
    data: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        data[key.strip()] = value.strip()
    return data


def _parse_names(value: str) -> list[str]:
    """Parse inline YOLO names values like [a, b] or a single name."""
    value = value.strip()
    if not value:
        return []
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [_strip_yaml_scalar(part) for part in inner.split(",")]
    return [_strip_yaml_scalar(value)]


def _strip_yaml_scalar(value: str) -> str:
    """Strip minimal YAML scalar quoting."""
    return value.strip().strip("'\"")


def _parse_int(value: str) -> int:
    """Parse an integer YAML scalar."""
    try:
        return int(value)
    except ValueError:
        return -1


def _resolve_dataset_path(base: Path, value: str) -> Path:
    """Resolve absolute or relative dataset paths."""
    path = Path(_strip_yaml_scalar(value))
    if path.is_absolute():
        return path
    return base / path


def _labels_dir_for_images(images_dir: Path, dataset_root: Path) -> Path:
    """Map a YOLO images split directory to its labels split directory."""
    try:
        relative = images_dir.relative_to(dataset_root)
    except ValueError:
        return dataset_root / "labels" / images_dir.name
    parts = list(relative.parts)
    if parts and parts[0] == "images":
        parts[0] = "labels"
        return dataset_root.joinpath(*parts)
    return dataset_root / "labels" / images_dir.name


def _image_files(folder: Path) -> list[Path]:
    """Return direct child image files for a YOLO split."""
    if not folder.exists() or not folder.is_dir():
        return []
    return sorted(
        path
        for path in folder.iterdir()
        if path.is_file() and path.suffix.lower() in _IMAGE_SUFFIXES
    )


def _non_empty_label_files(folder: Path) -> list[Path]:
    """Return non-empty TXT label files."""
    if not folder.exists() or not folder.is_dir():
        return []
    return sorted(
        path
        for path in folder.glob("*.txt")
        if path.is_file() and path.stat().st_size > 0
    )


def _count_train_labels(
    train_images: list[Path], labels_dir: Path, class_count: int
) -> dict[str, int]:
    """Count train label coverage and valid YOLO rows."""
    missing = 0
    empty = 0
    valid_rows = 0
    invalid_rows = 0
    for image in train_images:
        label = labels_dir / f"{image.stem}.txt"
        if not label.exists():
            missing += 1
            continue
        text = label.read_text(encoding="utf-8").strip()
        if not text:
            empty += 1
            continue
        for row in text.splitlines():
            if _is_valid_yolo_row(row, class_count):
                valid_rows += 1
            else:
                invalid_rows += 1
    return {
        "missing_train_labels": missing,
        "empty_train_labels": empty,
        "valid_train_label_rows": valid_rows,
        "invalid_train_label_rows": invalid_rows,
    }


def _is_valid_yolo_row(row: str, class_count: int) -> bool:
    """Return whether a row is a valid YOLO label row."""
    parts = row.split()
    if len(parts) != 5:
        return False
    try:
        class_id = int(parts[0])
        values = [float(part) for part in parts[1:]]
    except ValueError:
        return False
    if class_id < 0 or class_id >= class_count:
        return False
    x_center, y_center, width, height = values
    return (
        all(isfinite(value) for value in values)
        and 0.0 <= x_center <= 1.0
        and 0.0 <= y_center <= 1.0
        and 0.0 < width <= 1.0
        and 0.0 < height <= 1.0
    )


def _parse_metrics(results_csv: Path) -> TrainMetrics:
    """Parse YOLO results.csv metrics, defaulting missing values to zero."""
    if not results_csv.exists():
        return TrainMetrics(
            best_epoch=0,
            best_map50=0.0,
            best_map50_95=0.0,
            final_map50=0.0,
            final_map50_95=0.0,
        )
    with results_csv.open("r", encoding="utf-8", newline="") as file_obj:
        rows = list(csv.DictReader(file_obj))
    if not rows:
        return TrainMetrics(
            best_epoch=0,
            best_map50=0.0,
            best_map50_95=0.0,
            final_map50=0.0,
            final_map50_95=0.0,
        )
    best_index = 0
    best_map50 = -1.0
    best_map50_95 = 0.0
    for index, row in enumerate(rows):
        map50 = _float_row(row, "metrics/mAP50(B)")
        if map50 > best_map50:
            best_index = index
            best_map50 = map50
            best_map50_95 = _float_row(row, "metrics/mAP50-95(B)")
    final = rows[-1]
    return TrainMetrics(
        best_epoch=best_index,
        best_map50=max(best_map50, 0.0),
        best_map50_95=best_map50_95,
        final_map50=_float_row(final, "metrics/mAP50(B)"),
        final_map50_95=_float_row(final, "metrics/mAP50-95(B)"),
    )


def _float_row(row: dict[str, str], key: str) -> float:
    """Read one float value from a CSV row."""
    value = row.get(key, "0")
    try:
        return float(value)
    except ValueError:
        return 0.0


def _metric_value(metrics: object, key: str) -> float:
    """Read a metric from dict-like or object-like callback data."""
    if isinstance(metrics, dict):
        return float(metrics.get(key, 0.0))
    return float(getattr(metrics, key, 0.0))


def _is_oom_error(exc: RuntimeError) -> bool:
    """Return whether a runtime error looks like an OOM failure."""
    message = str(exc).lower()
    return "out of memory" in message or "oom" in message
