#!/usr/bin/env python3
"""Standalone YOLO folder prediction script for Linux servers."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from dataclasses import dataclass, replace
from datetime import datetime
from pathlib import Path
from typing import Any

_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp"}


@dataclass(frozen=True)
class PredictScriptConfig:
    """Command-line prediction configuration."""

    model_path: Path
    image_folder: Path
    output_base_dir: Path
    confidence: float = 0.25
    iou: float = 0.7
    batch_size: int = -1
    device: str = "auto"
    label_y_offset_px: float = 0.0
    log_file: Path | None = None
    overwrite_output: bool = False


@dataclass(frozen=True)
class PredictStats:
    """Prediction counters."""

    processed: int
    success: int
    predicted: int
    empty: int
    failed: int


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments for server prediction."""
    parser = argparse.ArgumentParser(description="Predict an image folder with YOLO.")
    parser.add_argument("--model", required=True, help="Trained .pt model path")
    parser.add_argument(
        "--image-folder",
        required=True,
        help="Folder containing images. Subfolders are scanned recursively.",
    )
    parser.add_argument("--output-dir", required=True, help="Inference output root")
    parser.add_argument("--device", default="auto", help="auto, cpu, gpu, 0, or 0,1")
    parser.add_argument("--conf", type=float, default=0.25, help="Confidence threshold")
    parser.add_argument("--iou", type=float, default=0.7, help="NMS IoU threshold")
    parser.add_argument("--batch", type=int, default=-1, help="-1 means auto")
    parser.add_argument(
        "--label-y-offset-px",
        type=float,
        default=0.0,
        help="Shift saved YOLO label boxes down by this many image pixels. Default 0.",
    )
    parser.add_argument(
        "--log-file",
        default=None,
        help="Optional log file. Defaults to <output-dir>/run_YYYYMMDD_HHMMSS/predict.log",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Allow replacing the generated run directory if its name already exists.",
    )
    return parser.parse_args(argv)


def build_predict_config(args: argparse.Namespace) -> PredictScriptConfig:
    """Build a lightweight prediction config from parsed arguments."""
    return PredictScriptConfig(
        model_path=Path(args.model),
        image_folder=Path(args.image_folder),
        output_base_dir=Path(args.output_dir),
        confidence=args.conf,
        iou=args.iou,
        batch_size=args.batch,
        device=args.device,
        label_y_offset_px=args.label_y_offset_px,
        log_file=None if args.log_file is None else Path(args.log_file),
        overwrite_output=args.overwrite,
    )


def main(argv: list[str] | None = None) -> int:
    """Run folder prediction and print the output paths."""
    config = build_predict_config(parse_args(argv))
    run_id = _run_id()
    log_file = config.log_file or config.output_base_dir / run_id / "predict.log"
    config = replace(config, log_file=log_file)
    try:
        with _tee_output(log_file):
            print(f"Log file: {log_file}")
            try:
                output_dir, stats, classes_path = run_prediction(config, run_id=run_id)
            except Exception as exc:
                print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
                return 1
            print("Prediction finished.")
            print(f"Output dir: {output_dir}")
            print(f"Labels dir: {output_dir / 'labels'}")
            if classes_path is not None:
                print(f"Classes: {classes_path}")
            print(
                "Stats: "
                f"processed={stats.processed}, success={stats.success}, "
                f"predicted={stats.predicted}, empty={stats.empty}, failed={stats.failed}"
            )
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


def run_prediction(
    config: PredictScriptConfig, run_id: str | None = None
) -> tuple[Path, PredictStats, Path | None]:
    """Predict all supported images and write YOLO txt labels."""
    _validate_predict_paths(config)
    resolved_device = resolve_device(config.device)
    images = _find_images(config.image_folder)
    if not images:
        raise FileNotFoundError(f"no supported images found under: {config.image_folder}")

    run_id = run_id or _run_id()
    output_dir = config.output_base_dir / run_id
    existing_entries = _existing_output_entries(output_dir, config.log_file)
    if existing_entries and not config.overwrite_output:
        raise FileExistsError(f"inference output directory is not empty: {output_dir}")
    if output_dir.exists() and config.overwrite_output:
        shutil.rmtree(output_dir)

    labels_dir = output_dir / "labels"
    labels_dir.mkdir(parents=True, exist_ok=True)
    config_path = output_dir / "inference_config.json"
    current_batch_file = output_dir / "current_batch.txt"
    _write_config(
        config_path,
        config,
        resolved_device,
        run_id,
        len(images),
        status="starting",
        processed=0,
        success=0,
        predicted=0,
        empty=0,
        failed=0,
    )

    from ultralytics import YOLO

    print(f"Started at: {datetime.now().isoformat(timespec='seconds')}")
    print(f"Model: {config.model_path}")
    print(f"Image folder: {config.image_folder}")
    print(f"Output dir: {output_dir}")
    print(f"Device: {resolved_device}")
    print(f"Images: {len(images)}")

    model = YOLO(str(config.model_path))
    classes_path = _write_classes(output_dir, model)
    batch_size = _effective_batch_size(config.batch_size, resolved_device)
    print(f"Batch size: {batch_size}")
    success = 0
    predicted = 0
    failed = 0
    _write_config(
        config_path,
        config,
        resolved_device,
        run_id,
        len(images),
        status="running",
        processed=0,
        success=0,
        predicted=0,
        empty=0,
        failed=0,
        classes_path=classes_path,
    )

    try:
        for chunk_start in range(0, len(images), batch_size):
            chunk = images[chunk_start : chunk_start + batch_size]
            batch_start = chunk_start + 1
            batch_end = chunk_start + len(chunk)
            current_batch_file.write_text(
                "\n".join(str(path) for path in chunk) + "\n", encoding="utf-8"
            )
            print(
                f"[{datetime.now().isoformat(timespec='seconds')}] "
                f"batch_start {batch_start}-{batch_end}/{len(images)} "
                f"first={chunk[0]} last={chunk[-1]} "
                f"current_batch={current_batch_file}"
            )
            _write_config(
                config_path,
                config,
                resolved_device,
                run_id,
                len(images),
                status="running_batch",
                processed=success,
                success=success,
                predicted=predicted,
                empty=success - predicted,
                failed=failed,
                classes_path=classes_path,
                current_batch_file=current_batch_file,
                current_batch_start=batch_start,
                current_batch_end=batch_end,
            )
            try:
                results = model.predict(
                    source=[str(path) for path in chunk],
                    conf=config.confidence,
                    iou=config.iou,
                    device=resolved_device,
                    batch=batch_size,
                    save=False,
                    verbose=False,
                )
            except Exception as exc:
                print(
                    f"[{datetime.now().isoformat(timespec='seconds')}] "
                    f"batch_failed {batch_start}-{batch_end}/{len(images)} "
                    f"{type(exc).__name__}: {exc}"
                )
                _write_config(
                    config_path,
                    config,
                    resolved_device,
                    run_id,
                    len(images),
                    status="batch_failed_single_retry",
                    processed=success,
                    success=success,
                    predicted=predicted,
                    empty=success - predicted,
                    failed=failed,
                    classes_path=classes_path,
                    current_batch_file=current_batch_file,
                    current_batch_start=batch_start,
                    current_batch_end=batch_end,
                )
                single_success, single_predicted, single_failed = _predict_chunk_one_by_one(
                    model=model,
                    chunk=chunk,
                    config=config,
                    labels_dir=labels_dir,
                    resolved_device=resolved_device,
                )
                success += single_success
                predicted += single_predicted
                failed += single_failed
                processed = min(chunk_start + len(chunk), len(images))
                empty_so_far = success - predicted
                percent = processed / len(images) * 100
                print(
                    f"[{datetime.now().isoformat(timespec='seconds')}] "
                    f"progress {processed}/{len(images)} ({percent:.1f}%) "
                    f"success={success} predicted={predicted} empty={empty_so_far} failed={failed}"
                )
                _write_config(
                    config_path,
                    config,
                    resolved_device,
                    run_id,
                    len(images),
                    status="running",
                    processed=processed,
                    success=success,
                    predicted=predicted,
                    empty=empty_so_far,
                    failed=failed,
                    classes_path=classes_path,
                )
                continue
            for image_path, result in zip(chunk, results, strict=False):
                label_path = labels_dir / image_path.relative_to(
                    config.image_folder
                ).with_suffix(".txt")
                label_path.parent.mkdir(parents=True, exist_ok=True)
                rows = _result_to_yolo_rows(
                    result, label_y_offset_px=config.label_y_offset_px
                )
                label_path.write_text(
                    "\n".join(rows) + ("\n" if rows else ""), encoding="utf-8"
                )
                success += 1
                if rows:
                    predicted += 1

            processed = min(chunk_start + len(chunk), len(images))
            empty_so_far = success - predicted
            percent = processed / len(images) * 100
            print(
                f"[{datetime.now().isoformat(timespec='seconds')}] "
                f"progress {processed}/{len(images)} ({percent:.1f}%) "
                f"success={success} predicted={predicted} empty={empty_so_far} failed={failed}"
            )
            _write_config(
                config_path,
                config,
                resolved_device,
                run_id,
                len(images),
                status="running",
                processed=processed,
                success=success,
                predicted=predicted,
                empty=empty_so_far,
                failed=failed,
                classes_path=classes_path,
            )
    except KeyboardInterrupt:
        _write_config(
            config_path,
            config,
            resolved_device,
            run_id,
            len(images),
            status="interrupted",
            processed=success,
            success=success,
            predicted=predicted,
            empty=success - predicted,
            failed=failed,
            classes_path=classes_path,
        )
        raise
    except Exception:
        _write_config(
            config_path,
            config,
            resolved_device,
            run_id,
            len(images),
            status="failed",
            processed=success,
            success=success,
            predicted=predicted,
            empty=success - predicted,
            failed=failed,
            classes_path=classes_path,
        )
        raise

    empty = success - predicted
    _write_config(
        config_path,
        config,
        resolved_device,
        run_id,
        len(images),
        status="completed",
        processed=success,
        success=success,
        predicted=predicted,
        empty=empty,
        failed=failed,
        classes_path=classes_path,
    )
    return output_dir, PredictStats(len(images), success, predicted, empty, failed), classes_path


def resolve_device(requested: str) -> str:
    """Resolve auto/gpu aliases to an Ultralytics-compatible device value."""
    value = requested.strip().lower()
    if value in {"cpu", "mps"}:
        return value
    if _is_cuda_id_list(value):
        return value

    import torch

    if value == "auto":
        return "0" if torch.cuda.is_available() else "cpu"
    if value == "gpu":
        if not torch.cuda.is_available():
            raise RuntimeError("GPU requested but torch.cuda.is_available() is False")
        return "0"
    raise ValueError("device must be auto, cpu, gpu, mps, 0, or 0,1")


def _validate_predict_paths(config: PredictScriptConfig) -> None:
    """Validate required prediction inputs."""
    if not config.model_path.is_file():
        raise FileNotFoundError(f"model does not exist: {config.model_path}")
    if not config.image_folder.is_dir():
        raise FileNotFoundError(f"image folder does not exist: {config.image_folder}")
    config.output_base_dir.mkdir(parents=True, exist_ok=True)


def _existing_output_entries(output_dir: Path, log_file: Path | None) -> list[Path]:
    """Return existing run entries that are not the log file opened by this run."""
    if not output_dir.exists():
        return []
    log_path = None if log_file is None else log_file.resolve()
    entries = []
    for path in output_dir.iterdir():
        if log_path is not None and path.resolve() == log_path:
            continue
        entries.append(path)
    return entries


def _find_images(image_folder: Path) -> list[Path]:
    """Return supported images recursively in stable order."""
    return sorted(
        path
        for path in image_folder.rglob("*")
        if path.is_file() and path.suffix.lower() in _IMAGE_SUFFIXES
    )


def _predict_chunk_one_by_one(
    *,
    model: object,
    chunk: list[Path],
    config: PredictScriptConfig,
    labels_dir: Path,
    resolved_device: str,
) -> tuple[int, int, int]:
    """Retry a failed batch one image at a time and record per-image failures."""
    success = 0
    predicted = 0
    failed = 0
    for image_path in chunk:
        print(
            f"[{datetime.now().isoformat(timespec='seconds')}] single_start {image_path}"
        )
        try:
            results = model.predict(
                source=str(image_path),
                conf=config.confidence,
                iou=config.iou,
                device=resolved_device,
                batch=1,
                save=False,
                verbose=False,
            )
            result = results[0] if results else None
            label_path = labels_dir / image_path.relative_to(
                config.image_folder
            ).with_suffix(".txt")
            label_path.parent.mkdir(parents=True, exist_ok=True)
            rows = (
                []
                if result is None
                else _result_to_yolo_rows(
                    result, label_y_offset_px=config.label_y_offset_px
                )
            )
            label_path.write_text(
                "\n".join(rows) + ("\n" if rows else ""), encoding="utf-8"
            )
            success += 1
            if rows:
                predicted += 1
            print(
                f"[{datetime.now().isoformat(timespec='seconds')}] "
                f"single_ok predicted={bool(rows)} {image_path}"
            )
        except Exception as exc:
            failed += 1
            error_path = labels_dir / image_path.relative_to(
                config.image_folder
            ).with_suffix(".error.txt")
            error_path.parent.mkdir(parents=True, exist_ok=True)
            error_path.write_text(
                f"{type(exc).__name__}: {exc}\nsource={image_path}\n",
                encoding="utf-8",
            )
            print(
                f"[{datetime.now().isoformat(timespec='seconds')}] "
                f"single_failed {type(exc).__name__}: {exc} source={image_path} "
                f"error={error_path}"
            )
    return success, predicted, failed


def _effective_batch_size(batch_size: int, device: str) -> int:
    """Resolve script batch size to a positive chunk size."""
    if batch_size > 0:
        return batch_size
    return 1 if device == "cpu" else 16


def _result_to_yolo_rows(
    result: object, *, label_y_offset_px: float = 0.0
) -> list[str]:
    """Convert one Ultralytics result into YOLO txt rows."""
    boxes = getattr(result, "boxes", None)
    if boxes is None or len(boxes) == 0:
        return []

    rows: list[str] = []
    for box in boxes:
        cls_id = int(_scalar(box.cls))
        xywhn = getattr(box, "xywhn")
        values = [_scalar(value) for value in xywhn[0]]
        if label_y_offset_px:
            values = _shift_y_center(values, label_y_offset_px, result)
        rows.append(f"{cls_id} " + " ".join(f"{value:.6f}" for value in values))
    return rows


def _shift_y_center(
    values: list[float], offset_px: float, result: object
) -> list[float]:
    """Shift normalized y-center by a pixel offset while preserving box size."""
    image_height = _result_image_height(result)
    if image_height <= 0:
        return values
    shifted = list(values)
    height = shifted[3]
    shifted[1] = shifted[1] + (offset_px / image_height)
    if height >= 1:
        shifted[1] = 0.5
    else:
        min_center = height / 2
        max_center = 1 - min_center
        shifted[1] = min(max(shifted[1], min_center), max_center)
    return shifted


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


def _scalar(value: object) -> float:
    """Return one float from a torch/numpy scalar-like value."""
    item = getattr(value, "item", None)
    if callable(item):
        return float(item())
    return float(value)


def _write_classes(output_dir: Path, model: object) -> Path | None:
    """Write model classes when Ultralytics exposes them."""
    names = getattr(model, "names", None)
    if not names:
        return None
    if isinstance(names, dict):
        values = [str(names[index]) for index in sorted(names)]
    else:
        values = [str(name) for name in names]
    classes_path = output_dir / "classes.txt"
    classes_path.write_text("\n".join(values) + "\n", encoding="utf-8")
    return classes_path


def _write_config(
    config_path: Path,
    config: PredictScriptConfig,
    resolved_device: str,
    run_id: str,
    image_count: int,
    *,
    status: str,
    processed: int,
    success: int,
    predicted: int,
    empty: int,
    failed: int,
    classes_path: Path | None = None,
    current_batch_file: Path | None = None,
    current_batch_start: int | None = None,
    current_batch_end: int | None = None,
) -> None:
    """Write a compact inference config snapshot."""
    timestamp = datetime.now().isoformat(timespec="seconds")
    payload: dict[str, Any] = {
        "run_id": run_id,
        "status": status,
        "model_path": str(config.model_path),
        "image_folder": str(config.image_folder),
        "output_dir": str(config_path.parent),
        "confidence": config.confidence,
        "iou": config.iou,
        "batch_size": config.batch_size,
        "label_y_offset_px": config.label_y_offset_px,
        "resolved_device": resolved_device,
        "image_count": image_count,
        "classes_path": None if classes_path is None else str(classes_path),
        "statistics": {
            "processed": processed,
            "success": success,
            "predicted": predicted,
            "empty": empty,
            "failed": failed,
        },
        "current_batch": None
        if current_batch_file is None
        else {
            "start": current_batch_start,
            "end": current_batch_end,
            "file": str(current_batch_file),
        },
        "created_at": timestamp,
        "updated_at": timestamp,
    }
    config_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _run_id() -> str:
    """Return a timestamped inference run id."""
    return datetime.now().strftime("run_%Y%m%d_%H%M%S")


def _is_cuda_id_list(value: str) -> bool:
    """Return whether value is a comma-separated CUDA id list."""
    return bool(value) and all(part.isdigit() for part in value.split(","))


def _default_log_file(output_dir: Path, prefix: str) -> Path:
    """Return a timestamped default log file under the output root."""
    return output_dir / f"{prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"


@contextmanager
def _tee_output(log_file: Path):
    """Mirror stdout and stderr to a log file."""
    log_file.parent.mkdir(parents=True, exist_ok=True)
    with log_file.open("a", encoding="utf-8", buffering=1) as file:
        with redirect_stdout(_Tee(sys.stdout, file)), redirect_stderr(
            _Tee(sys.stderr, file)
        ):
            yield


class _Tee:
    """Write command output to multiple streams."""

    def __init__(self, *streams: Any) -> None:
        self._streams = streams

    def write(self, text: str) -> int:
        for stream in self._streams:
            stream.write(text)
            stream.flush()
        return len(text)

    def flush(self) -> None:
        for stream in self._streams:
            stream.flush()


if __name__ == "__main__":
    raise SystemExit(main())
