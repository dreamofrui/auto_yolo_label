#!/usr/bin/env python3
"""Standalone YOLO training script for a Linux server or Docker container."""

from __future__ import annotations

import argparse
import sys
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class TrainScriptConfig:
    """Command-line training configuration."""

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
    log_file: Path | None = None
    overwrite_output: bool = False


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments for server training."""
    parser = argparse.ArgumentParser(description="Train a YOLO model with Ultralytics.")
    parser.add_argument("--data-yaml", required=True, help="Path to YOLO data.yaml")
    parser.add_argument("--base-model", required=True, help="Initial .pt model path")
    parser.add_argument("--output-dir", required=True, help="Training output root")
    parser.add_argument("--device", default="auto", help="auto, cpu, gpu, 0, or 0,1")
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--imgsz", type=int, default=640, help="Image size")
    parser.add_argument("--batch", type=int, default=-1, help="-1 means auto")
    parser.add_argument("--patience", type=int, default=50)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--optimizer", default="AdamW")
    parser.add_argument("--lr0", type=float, default=0.01)
    parser.add_argument("--box", type=float, default=7.5)
    parser.add_argument("--cls", type=float, default=0.5)
    parser.add_argument("--dfl", type=float, default=1.5)
    parser.add_argument("--scale", type=float, default=0.5)
    parser.add_argument("--cache", default="ram", help="ram, disk, true, false")
    parser.add_argument("--run-name", default=None, help="Optional fixed YOLO run name")
    parser.add_argument(
        "--log-file",
        default=None,
        help="Optional log file. Defaults to <output-dir>/train_YYYYMMDD_HHMMSS.log",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Allow YOLO to reuse an existing run name.",
    )
    return parser.parse_args(argv)


def build_train_config(args: argparse.Namespace) -> TrainScriptConfig:
    """Build a lightweight training config from parsed arguments."""
    return TrainScriptConfig(
        data_yaml=Path(args.data_yaml),
        base_model=Path(args.base_model),
        output_dir=Path(args.output_dir),
        epochs=args.epochs,
        batch_size=args.batch,
        image_size=args.imgsz,
        device=args.device,
        patience=args.patience,
        workers=args.workers,
        optimizer=args.optimizer,
        lr0=args.lr0,
        box=args.box,
        cls=args.cls,
        dfl=args.dfl,
        scale=args.scale,
        cache=_parse_cache(args.cache),
        run_name=args.run_name,
        log_file=None if args.log_file is None else Path(args.log_file),
        overwrite_output=args.overwrite,
    )


def build_train_kwargs(
    config: TrainScriptConfig, *, resolved_device: str
) -> dict[str, Any]:
    """Build keyword arguments accepted by Ultralytics YOLO.train."""
    return {
        "data": config.data_yaml.as_posix(),
        "project": config.output_dir.as_posix(),
        "name": config.run_name,
        "exist_ok": config.overwrite_output,
        "epochs": config.epochs,
        "batch": config.batch_size,
        "imgsz": config.image_size,
        "device": resolved_device,
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


def main(argv: list[str] | None = None) -> int:
    """Run training and print the output paths."""
    config = build_train_config(parse_args(argv))
    log_file = config.log_file or _default_log_file(config.output_dir, "train")
    try:
        with _tee_output(log_file):
            print(f"Log file: {log_file}")
            return _run_train(config)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


def _run_train(config: TrainScriptConfig) -> int:
    """Run training under the active output/log context."""
    _validate_train_paths(config)
    resolved_device = resolve_device(config.device)
    from ultralytics import YOLO

    print(f"Started at: {datetime.now().isoformat(timespec='seconds')}")
    print(f"Data YAML: {config.data_yaml}")
    print(f"Base model: {config.base_model}")
    print(f"Output root: {config.output_dir}")
    print(f"Device: {resolved_device}")

    model = YOLO(str(config.base_model))
    result = model.train(**build_train_kwargs(config, resolved_device=resolved_device))
    save_dir = Path(getattr(result, "save_dir", config.output_dir))
    print("Training finished.")
    print(f"Device: {resolved_device}")
    print(f"Output dir: {save_dir}")
    print(f"Best model: {save_dir / 'weights' / 'best.pt'}")
    print(f"Last model: {save_dir / 'weights' / 'last.pt'}")
    print(f"Finished at: {datetime.now().isoformat(timespec='seconds')}")
    return 0


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


def _validate_train_paths(config: TrainScriptConfig) -> None:
    """Validate required training inputs before importing Ultralytics."""
    if not config.data_yaml.is_file():
        raise FileNotFoundError(f"data.yaml does not exist: {config.data_yaml}")
    if not config.base_model.is_file():
        raise FileNotFoundError(f"base model does not exist: {config.base_model}")
    config.output_dir.mkdir(parents=True, exist_ok=True)


def _parse_cache(value: str) -> str | bool:
    """Parse YOLO cache option from CLI text."""
    normalized = value.strip().lower()
    if normalized == "true":
        return True
    if normalized == "false":
        return False
    return value


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
