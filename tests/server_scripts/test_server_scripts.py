from __future__ import annotations

import json
from pathlib import Path

from server_scripts.predict_yolo import (
    PredictScriptConfig,
    _result_to_yolo_rows,
    _write_config,
    build_predict_config,
    parse_args as parse_predict_args,
)
from server_scripts.train_yolo import (
    TrainScriptConfig,
    build_train_config,
    build_train_kwargs,
    parse_args as parse_train_args,
)


def test_train_script_builds_train_config_from_cli_args() -> None:
    args = parse_train_args(
        [
            "--data-yaml",
            "/data/dataset/data.yaml",
            "--base-model",
            "/data/models/yolov8n.pt",
            "--output-dir",
            "/data/runs/train",
            "--device",
            "gpu",
            "--epochs",
            "12",
            "--imgsz",
            "512",
            "--batch",
            "8",
            "--patience",
            "20",
            "--workers",
            "4",
            "--optimizer",
            "SGD",
            "--lr0",
            "0.005",
            "--box",
            "6.5",
            "--cls",
            "0.75",
            "--dfl",
            "1.25",
            "--scale",
            "0.25",
            "--cache",
            "disk",
            "--run-name",
            "server_train",
            "--log-file",
            "/data/logs/train.log",
            "--overwrite",
        ]
    )

    config = build_train_config(args)

    assert config == TrainScriptConfig(
        data_yaml=Path("/data/dataset/data.yaml"),
        base_model=Path("/data/models/yolov8n.pt"),
        output_dir=Path("/data/runs/train"),
        device="gpu",
        epochs=12,
        image_size=512,
        batch_size=8,
        patience=20,
        workers=4,
        optimizer="SGD",
        lr0=0.005,
        box=6.5,
        cls=0.75,
        dfl=1.25,
        scale=0.25,
        cache="disk",
        run_name="server_train",
        log_file=Path("/data/logs/train.log"),
        overwrite_output=True,
    )


def test_train_script_builds_ultralytics_kwargs() -> None:
    config = TrainScriptConfig(
        data_yaml=Path("/data/dataset/data.yaml"),
        base_model=Path("/data/models/yolov8n.pt"),
        output_dir=Path("/data/runs/train"),
        device="0",
        epochs=3,
        image_size=320,
        batch_size=4,
        patience=10,
        workers=2,
        optimizer="SGD",
        lr0=0.002,
        box=6.0,
        cls=0.4,
        dfl=1.2,
        scale=0.3,
        cache=False,
        run_name="linux_train",
        overwrite_output=True,
    )

    kwargs = build_train_kwargs(config, resolved_device="0")

    assert kwargs == {
        "data": "/data/dataset/data.yaml",
        "project": "/data/runs/train",
        "name": "linux_train",
        "exist_ok": True,
        "epochs": 3,
        "batch": 4,
        "imgsz": 320,
        "device": "0",
        "patience": 10,
        "workers": 2,
        "optimizer": "SGD",
        "lr0": 0.002,
        "box": 6.0,
        "cls": 0.4,
        "dfl": 1.2,
        "scale": 0.3,
        "cache": False,
    }


def test_predict_script_builds_folder_infer_config_from_cli_args() -> None:
    args = parse_predict_args(
        [
            "--model",
            "/data/runs/train/train/weights/best.pt",
            "--image-folder",
            "/data/images",
            "--output-dir",
            "/data/runs/infer",
            "--device",
            "0",
            "--conf",
            "0.4",
            "--iou",
            "0.55",
            "--batch",
            "16",
            "--label-y-offset-px",
            "4",
            "--log-file",
            "/data/logs/predict.log",
            "--overwrite",
        ]
    )

    config = build_predict_config(args)

    assert config == PredictScriptConfig(
        model_path=Path("/data/runs/train/train/weights/best.pt"),
        output_base_dir=Path("/data/runs/infer"),
        confidence=0.4,
        iou=0.55,
        batch_size=16,
        device="0",
        label_y_offset_px=4.0,
        image_folder=Path("/data/images"),
        log_file=Path("/data/logs/predict.log"),
        overwrite_output=True,
    )


def test_predict_script_can_shift_label_y_center_down_by_pixels() -> None:
    class FakeBox:
        cls = 0
        xywhn = [[0.5, 0.5, 0.2, 0.1]]

    class FakeResult:
        boxes = [FakeBox()]
        orig_shape = (100, 200)

    assert _result_to_yolo_rows(FakeResult(), label_y_offset_px=5) == [
        "0 0.500000 0.550000 0.200000 0.100000"
    ]


def test_predict_config_snapshot_records_running_progress(tmp_path: Path) -> None:
    config = PredictScriptConfig(
        model_path=Path("/data/runs/train/weights/best.pt"),
        image_folder=Path("/data/images"),
        output_base_dir=Path("/data/runs/infer"),
        confidence=0.4,
        iou=0.55,
        batch_size=16,
        device="gpu",
    )
    config_path = tmp_path / "run_20260525_063210" / "inference_config.json"
    config_path.parent.mkdir()
    current_batch_file = config_path.parent / "current_batch.txt"

    _write_config(
        config_path,
        config,
        resolved_device="0",
        run_id="run_20260525_063210",
        image_count=100,
        status="running_batch",
        processed=32,
        success=32,
        predicted=20,
        empty=12,
        failed=0,
        classes_path=config_path.parent / "classes.txt",
        current_batch_file=current_batch_file,
        current_batch_start=33,
        current_batch_end=48,
    )

    payload = json.loads(config_path.read_text(encoding="utf-8"))
    assert payload["status"] == "running_batch"
    assert payload["statistics"] == {
        "processed": 32,
        "success": 32,
        "predicted": 20,
        "empty": 12,
        "failed": 0,
    }
    assert payload["current_batch"] == {
        "start": 33,
        "end": 48,
        "file": str(current_batch_file),
    }
    assert payload["classes_path"] == str(config_path.parent / "classes.txt")
