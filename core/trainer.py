"""YOLO training module."""

from __future__ import annotations

import csv
import importlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol, cast

from loguru import logger

from utils.device import get_optimal_batch_size, resolve_device
from utils.exceptions import AutoLabelerError, ErrorCode
from utils.task_registry import TaskHandle

_REQUIRED_DATA_YAML_KEYS = ("path", "train", "val", "nc", "names")


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
    metrics: TrainMetrics = field(default_factory=lambda: TrainMetrics(0, 0.0, 0.0, 0.0, 0.0))


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

    def __init__(self, task_handle: TaskHandle | None = None) -> None:
        """Create a trainer with optional task state.

        Args:
            task_handle: Optional task state used for progress and cancellation.
        """
        self._task_handle = task_handle

    def train(self, config: TrainConfig) -> TrainResult:
        """Train a YOLO model.

        Args:
            config: Training configuration.

        Returns:
            Paths, effective config, and parsed metrics.

        Raises:
            TrainDataYamlInvalidError: If data.yaml is missing or malformed.
            TrainBaseModelNotFoundError: If the base model is missing.
            TrainDeviceUnavailableError: If the requested device is invalid.
            TrainOOMError: If training reports an out-of-memory failure.
            TrainInterruptedError: If cancellation is requested.
        """
        self._validate_inputs(config)
        self._raise_if_cancelled()
        try:
            device = resolve_device(config.device)
        except AutoLabelerError as exc:
            raise TrainDeviceUnavailableError("训练设备不可用", details=str(exc)) from exc
        batch_size = _resolve_batch_size(config, device)
        run_dir = config.output_dir / "train"
        effective_config = _effective_config(config, device, batch_size)
        model = _load_yolo_model(config.base_model)
        self._register_progress_callback(model, config.epochs)

        logger.info("开始训练 YOLO: data={}, model={}", config.data_yaml, config.base_model)
        try:
            model.train(
                data=str(config.data_yaml),
                model=str(config.base_model),
                project=str(config.output_dir),
                name="train",
                exist_ok=True,
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
            raise TrainInterruptedError("训练已取消", details=str(exc)) from exc
        except RuntimeError as exc:
            if _is_oom_error(exc):
                raise TrainOOMError("训练显存不足", details=str(exc)) from exc
            raise

        best_model = run_dir / "weights" / "best.pt"
        last_model = run_dir / "weights" / "last.pt"
        metrics = _parse_metrics(run_dir / "results.csv")
        return TrainResult(
            best_model=best_model,
            last_model=last_model if last_model.exists() else None,
            output_dir=run_dir,
            effective_config=effective_config,
            metrics=metrics,
        )

    def _validate_inputs(self, config: TrainConfig) -> None:
        """Validate training inputs."""
        if not config.data_yaml.exists() or not config.data_yaml.is_file():
            raise TrainDataYamlInvalidError("data.yaml 不存在", details=str(config.data_yaml))
        text = config.data_yaml.read_text(encoding="utf-8")
        missing_keys = [key for key in _REQUIRED_DATA_YAML_KEYS if f"{key}:" not in text]
        if missing_keys:
            raise TrainDataYamlInvalidError("data.yaml 缺少必要字段", details=", ".join(missing_keys))
        if not config.base_model.exists() or not config.base_model.is_file():
            raise TrainBaseModelNotFoundError("预训练模型不存在", details=str(config.base_model))

    def _register_progress_callback(self, model: _YoloModel, total_epochs: int) -> None:
        """Register a YOLO epoch callback when supported."""

        def on_fit_epoch_end(trainer_state: Any) -> None:
            """Update progress from a YOLO epoch-end callback."""
            self._raise_if_cancelled()
            epoch = int(getattr(trainer_state, "epoch", 0)) + 1
            epochs = int(getattr(trainer_state, "epochs", total_epochs))
            metrics = getattr(trainer_state, "metrics", None)
            map50 = _metric_value(metrics, "mAP50")
            self._set_progress(epoch, epochs, f"Epoch {epoch}/{epochs} - mAP50: {map50:.3f}")

        add_callback = getattr(model, "add_callback", None)
        if callable(add_callback):
            add_callback("on_fit_epoch_end", on_fit_epoch_end)

    def _raise_if_cancelled(self) -> None:
        """Raise TrainInterruptedError when cancellation has been requested."""
        if self._task_handle is not None and self._task_handle.is_cancel_requested:
            raise TrainInterruptedError("训练已取消")

    def _set_progress(self, current: int, total: int, message: str) -> None:
        """Update task progress fields when a task handle is available."""
        if self._task_handle is None:
            return
        self._task_handle.progress_current = current
        self._task_handle.progress_total = total
        self._task_handle.progress_message = message


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


def _effective_config(config: TrainConfig, device: str, batch_size: int) -> dict[str, Any]:
    """Return the effective training parameters."""
    return {
        "data_yaml": str(config.data_yaml),
        "base_model": str(config.base_model),
        "output_dir": str(config.output_dir),
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


def _parse_metrics(results_csv: Path) -> TrainMetrics:
    """Parse YOLO results.csv metrics, defaulting missing values to zero."""
    if not results_csv.exists():
        return TrainMetrics(best_epoch=0, best_map50=0.0, best_map50_95=0.0, final_map50=0.0, final_map50_95=0.0)
    with results_csv.open("r", encoding="utf-8", newline="") as file_obj:
        rows = list(csv.DictReader(file_obj))
    if not rows:
        return TrainMetrics(best_epoch=0, best_map50=0.0, best_map50_95=0.0, final_map50=0.0, final_map50_95=0.0)
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
