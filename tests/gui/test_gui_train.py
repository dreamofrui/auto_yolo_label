"""Scoped tests for the train tool page."""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from core.trainer import TrainResult
from utils.exceptions import ErrorCode, ErrorInfo
from utils.task_registry import TaskRegistry
from gui.workbench import AutoLabelerWindow

from conftest import (
    app,
    make_image,
    make_scanned_site,
    make_window,
    set_task_timestamp,
)

def test_train_page_shows_common_options_and_hides_advanced_by_default() -> None:
    """Train page keeps common options visible and hides rarer YOLO parameters."""
    qt_app = app()
    window = make_window()
    window.show()
    qt_app.processEvents()
    QTest.mouseClick(window.login_view.demo_login_button, Qt.MouseButton.LeftButton)
    QTest.mouseClick(
        window.workbench_view.nav_buttons["train"], Qt.MouseButton.LeftButton
    )

    train_page = window.workbench_view.train_page
    assert hasattr(train_page, "common_options_panel")
    assert train_page.common_options_panel.isVisible()
    assert hasattr(train_page, "advanced_toggle_button")
    assert hasattr(train_page, "advanced_options_panel")
    assert not train_page.advanced_options_panel.isVisible()
    assert train_page.device_input.currentText() == "auto"
    assert train_page.runtime_status_label.text() == "等待训练"
    assert "设备" in train_page.runtime_detail_label.text()
    assert hasattr(train_page, "stop_button")
    assert not train_page.stop_button.isEnabled()


class FakeTrainWorker:
    """Small fake worker that records TrainConfig from the GUI."""

    def __init__(self) -> None:
        self.config = None

    def run(self, config):
        self.config = config
        result = TrainResult(
            best_model=config.output_dir / "train" / "weights" / "best.pt",
            last_model=config.output_dir / "train" / "weights" / "last.pt",
            output_dir=config.output_dir / "train",
            warnings=["labels/val is empty"],
            preflight={"train_images": 3, "val_images": 0, "classes": ["CodeA"]},
        )

        class Outcome:
            success = True
            error = None
            task = None

            def __init__(self, result):
                self.result = result

        return Outcome(result)


class InterruptedTrainWorker:
    """Small fake worker that returns a user-stopped training outcome."""

    def __init__(self) -> None:
        self.config = None

    def run(self, config):
        self.config = config

        class Outcome:
            success = False
            result = None
            task = None
            error = ErrorInfo(
                code=ErrorCode.TRAIN_INTERRUPTED.value,
                message="训练已取消",
                details=None,
                retryable=False,
            )

        return Outcome()


def test_train_page_builds_config_and_renders_result(tmp_path: Path) -> None:
    """Train page builds TrainConfig from main fields and displays output paths."""
    qt_app = app()
    train_worker = FakeTrainWorker()
    window = make_window(train_worker=train_worker)
    window.show()
    qt_app.processEvents()
    QTest.mouseClick(window.login_view.demo_login_button, Qt.MouseButton.LeftButton)
    QTest.mouseClick(
        window.workbench_view.nav_buttons["train"], Qt.MouseButton.LeftButton
    )

    train_page = window.workbench_view.train_page
    dataset = tmp_path / "dataset"
    model = tmp_path / "yolov8n.pt"
    output = tmp_path / "runs"
    train_page.dataset_input.setText(str(dataset))
    train_page.model_input.setText(str(model))
    train_page.output_input.setText(str(output))
    train_page.epochs_input.setText("2")
    train_page.batch_input.setText("1")
    train_page.image_size_input.setText("640")
    train_page.device_input.setCurrentText("cpu")
    QTest.mouseClick(train_page.run_button, Qt.MouseButton.LeftButton)

    assert train_worker.config is not None
    assert train_worker.config.data_yaml == dataset / "data.yaml"
    assert train_worker.config.base_model == model
    assert train_worker.config.output_dir == output
    assert train_worker.config.epochs == 2
    assert train_worker.config.batch_size == 1
    assert train_worker.config.device == "cpu"
    assert "训练完成" in train_page.result_summary.text()
    assert "best.pt" in train_page.log_box.toPlainText()


def test_train_page_accepts_explicit_multi_gpu_device(tmp_path: Path) -> None:
    """Train page exposes explicit CUDA ids and passes selected ids to training."""
    qt_app = app()
    train_worker = FakeTrainWorker()
    window = make_window(train_worker=train_worker)
    window.show()
    qt_app.processEvents()
    QTest.mouseClick(window.login_view.demo_login_button, Qt.MouseButton.LeftButton)
    QTest.mouseClick(
        window.workbench_view.nav_buttons["train"], Qt.MouseButton.LeftButton
    )

    train_page = window.workbench_view.train_page
    device_items = [
        train_page.device_input.itemText(index)
        for index in range(train_page.device_input.count())
    ]
    assert {"All GPUs", "GPU 0", "GPU 1", "GPU 0+1"}.issubset(set(device_items))

    train_page.dataset_input.setText(str(tmp_path / "dataset"))
    train_page.model_input.setText(str(tmp_path / "yolov8n.pt"))
    train_page.output_input.setText(str(tmp_path / "runs"))
    train_page.batch_input.setText("16")
    train_page.workers_input.setText("4")
    train_page.device_input.setCurrentText("GPU 0+1")
    QTest.mouseClick(train_page.run_button, Qt.MouseButton.LeftButton)

    assert train_worker.config is not None
    assert train_worker.config.device == "0,1"
    assert train_worker.config.batch_size == 16
    assert train_worker.config.workers == 4


def test_train_page_builds_advanced_yolo_config(tmp_path: Path) -> None:
    """Train page maps backend-supported rarer YOLO parameters from advanced fields."""
    qt_app = app()
    train_worker = FakeTrainWorker()
    window = make_window(train_worker=train_worker)
    window.show()
    qt_app.processEvents()
    QTest.mouseClick(window.login_view.demo_login_button, Qt.MouseButton.LeftButton)
    QTest.mouseClick(
        window.workbench_view.nav_buttons["train"], Qt.MouseButton.LeftButton
    )

    train_page = window.workbench_view.train_page
    train_page.dataset_input.setText(str(tmp_path / "dataset"))
    train_page.model_input.setText(str(tmp_path / "yolov8n.pt"))
    train_page.output_input.setText(str(tmp_path / "runs"))
    QTest.mouseClick(train_page.advanced_toggle_button, Qt.MouseButton.LeftButton)
    train_page.patience_input.setText("12")
    train_page.workers_input.setText("3")
    train_page.optimizer_input.setCurrentText("SGD")
    train_page.lr0_input.setText("0.02")
    train_page.box_input.setText("8.0")
    train_page.cls_input.setText("0.7")
    train_page.dfl_input.setText("1.9")
    train_page.scale_input.setText("0.3")
    train_page.cache_input.setCurrentText("false")
    train_page.run_name_input.setText("custom_train")
    train_page.overwrite_output_checkbox.setChecked(True)
    QTest.mouseClick(train_page.run_button, Qt.MouseButton.LeftButton)

    assert train_worker.config is not None
    assert train_worker.config.patience == 12
    assert train_worker.config.workers == 3
    assert train_worker.config.optimizer == "SGD"
    assert train_worker.config.lr0 == 0.02
    assert train_worker.config.box == 8.0
    assert train_worker.config.cls == 0.7
    assert train_worker.config.dfl == 1.9
    assert train_worker.config.scale == 0.3
    assert train_worker.config.cache is False
    assert train_worker.config.run_name == "custom_train"
    assert train_worker.config.overwrite_output is True


def test_train_page_renders_persisted_running_progress(tmp_path: Path) -> None:
    """Train page can render persisted epoch progress for a running train task."""
    qt_app = app()
    registry = TaskRegistry(task_dir=tmp_path / "tasks")
    task = registry.create_task("train")
    registry.start_task(task.task_id, total=10, message="准备训练")
    registry.update_progress(task.task_id, current=3, total=10, message="Epoch 3/10")
    window = make_window(task_registry=registry, train_worker=FakeTrainWorker())
    window.show()
    qt_app.processEvents()
    QTest.mouseClick(window.login_view.demo_login_button, Qt.MouseButton.LeftButton)
    QTest.mouseClick(
        window.workbench_view.nav_buttons["train"], Qt.MouseButton.LeftButton
    )

    train_page = window.workbench_view.train_page
    train_page.refresh_running_progress()

    assert "3/10" in train_page.progress_label.text()
    assert train_page.progress_bar.value() == 3
    assert train_page.progress_bar.maximum() == 10


def test_train_page_stop_button_requests_running_task_cancel(tmp_path: Path) -> None:
    """Train stop button requests cancellation on the active train task."""
    qt_app = app()
    registry = TaskRegistry(task_dir=tmp_path / "tasks")
    task = registry.create_task("train")
    registry.start_task(task.task_id, total=10, message="Epoch 3/10")
    window = make_window(task_registry=registry, train_worker=FakeTrainWorker())
    window.show()
    qt_app.processEvents()
    QTest.mouseClick(window.login_view.demo_login_button, Qt.MouseButton.LeftButton)
    QTest.mouseClick(
        window.workbench_view.nav_buttons["train"], Qt.MouseButton.LeftButton
    )

    train_page = window.workbench_view.train_page
    train_page.refresh_running_progress()
    assert train_page.stop_button.isEnabled()
    QTest.mouseClick(train_page.stop_button, Qt.MouseButton.LeftButton)

    cancelled = registry.get(task.task_id)
    assert cancelled.status == "running"
    assert cancelled.is_cancel_requested is True
    assert not train_page.stop_button.isEnabled()
    assert "停止" in train_page.result_summary.text()


def test_train_page_renders_interrupted_outcome_as_stopped(tmp_path: Path) -> None:
    """Train page treats worker interruption as a stopped run, not a failure."""
    qt_app = app()
    train_worker = InterruptedTrainWorker()
    window = make_window(train_worker=train_worker)
    window.show()
    qt_app.processEvents()
    QTest.mouseClick(window.login_view.demo_login_button, Qt.MouseButton.LeftButton)
    QTest.mouseClick(
        window.workbench_view.nav_buttons["train"], Qt.MouseButton.LeftButton
    )

    train_page = window.workbench_view.train_page
    train_page.dataset_input.setText(str(tmp_path / "dataset"))
    train_page.model_input.setText(str(tmp_path / "yolov8n.pt"))
    train_page.output_input.setText(str(tmp_path / "runs"))
    QTest.mouseClick(train_page.run_button, Qt.MouseButton.LeftButton)

    assert "停止" in train_page.result_summary.text()
    assert "failed" not in train_page.log_box.toPlainText()


def test_train_page_rejects_empty_paths_before_building_config() -> None:
    """Train page blocks blank paths instead of resolving them as cwd."""
    qt_app = app()
    train_worker = FakeTrainWorker()
    window = make_window(train_worker=train_worker)
    window.show()
    qt_app.processEvents()
    QTest.mouseClick(window.login_view.demo_login_button, Qt.MouseButton.LeftButton)
    QTest.mouseClick(
        window.workbench_view.nav_buttons["train"], Qt.MouseButton.LeftButton
    )

    train_page = window.workbench_view.train_page
    QTest.mouseClick(train_page.run_button, Qt.MouseButton.LeftButton)

    assert train_worker.config is None
    assert "请选择数据集目录" in train_page.result_summary.text()


