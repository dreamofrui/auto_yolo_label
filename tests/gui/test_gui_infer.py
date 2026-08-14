"""Scoped tests for the infer tool page."""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QCheckBox
from core.inferencer import InferResult, InferStatistics
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

def test_infer_page_shows_common_settings_and_hides_rare_advanced_options() -> None:
    """Infer page keeps common prediction settings visible by default."""
    qt_app = app()
    window = make_window()
    window.show()
    qt_app.processEvents()
    QTest.mouseClick(window.login_view.demo_login_button, Qt.MouseButton.LeftButton)
    QTest.mouseClick(
        window.workbench_view.nav_buttons["infer"], Qt.MouseButton.LeftButton
    )

    infer_page = window.workbench_view.infer_page
    assert infer_page.flow_source_unsampled.text() == "未抽样图片（默认）"
    assert infer_page.flow_source_all.text() == "全部扫描图片（含已抽样）"
    assert hasattr(infer_page, "common_options_panel")
    assert infer_page.common_options_panel.isVisible()
    assert infer_page.confidence_input.isVisible()
    assert infer_page.iou_input.isVisible()
    assert infer_page.batch_input.isVisible()
    assert "NMS" in infer_page.iou_input.toolTip()
    assert infer_page.device_input.currentText() == "auto"
    assert hasattr(infer_page, "advanced_toggle_button")
    assert hasattr(infer_page, "advanced_options_panel")
    assert not infer_page.advanced_options_panel.isVisible()
    assert isinstance(infer_page.overwrite_output_checkbox, QCheckBox)
    assert hasattr(infer_page, "stop_button")
    assert not infer_page.stop_button.isEnabled()
    assert "run_YYYYMMDD_HHMMSS" in infer_page.run_path_preview.text()
    assert "不改变 sampled" in infer_page.flow_source_note.text()
    infer_page.site_input.setText("D:/site")
    assert "不改变 sampled" in infer_page.flow_source_note.text()
    assert "inference_results" in infer_page.run_path_preview.text()


class FakeInferWorker:
    """Small fake worker that records InferConfig from the GUI."""

    def __init__(self) -> None:
        self.config = None

    def run(self, config):
        self.config = config
        result = InferResult(
            mapping_path=config.site_folder / ".autolabeler" / "mapping.json"
            if config.image_source != "folder"
            else None,
            run_id="run_20260520_112000",
            inference_output_dir=(config.output_base_dir or config.site_folder / ".autolabeler" / "inference_results")
            / "run_20260520_112000",
            config_path=(config.output_base_dir or config.site_folder / ".autolabeler" / "inference_results")
            / "run_20260520_112000"
            / "inference_config.json",
            classes_path=(config.output_base_dir or config.site_folder / ".autolabeler" / "inference_results")
            / "run_20260520_112000"
            / "classes.txt",
            statistics=InferStatistics(
                pending=3,
                processed=3,
                success=3,
                failed=0,
                predicted=2,
                empty_prediction=1,
            ),
        )

        class Outcome:
            success = True
            error = None
            task = None

            def __init__(self, result):
                self.result = result

        return Outcome(result)


class CancelledInferWorker:
    """Small fake infer worker that returns a user-cancelled outcome."""

    def __init__(self) -> None:
        self.config = None

    def run(self, config):
        self.config = config

        class Outcome:
            success = False
            result = None
            task = None
            error = ErrorInfo(
                code=ErrorCode.TASK_CANCELLED.value,
                message="推理任务已取消",
                details=None,
                retryable=False,
            )

        return Outcome()


def test_infer_page_builds_flow_config_and_renders_result(tmp_path: Path) -> None:
    """Infer page builds Flow InferConfig with fixed site output root."""
    qt_app = app()
    infer_worker = FakeInferWorker()
    window = make_window(infer_worker=infer_worker)
    window.show()
    qt_app.processEvents()
    QTest.mouseClick(window.login_view.demo_login_button, Qt.MouseButton.LeftButton)
    QTest.mouseClick(
        window.workbench_view.nav_buttons["infer"], Qt.MouseButton.LeftButton
    )

    infer_page = window.workbench_view.infer_page
    site = tmp_path / "site"
    model = tmp_path / "best.pt"
    infer_page.site_input.setText(str(site))
    infer_page.model_input.setText(str(model))
    infer_page.confidence_input.setText("0.25")
    infer_page.iou_input.setText("0.7")
    infer_page.batch_input.setText("1")
    infer_page.label_y_offset_input.setText("4")
    infer_page.device_input.setCurrentText("cpu")
    infer_page.overwrite_output_checkbox.setChecked(True)
    QTest.mouseClick(infer_page.run_button, Qt.MouseButton.LeftButton)

    assert infer_worker.config is not None
    assert infer_worker.config.model_path == model
    assert infer_worker.config.site_folder == site
    assert infer_worker.config.image_source == "unsampled"
    assert infer_worker.config.output_base_dir is None
    assert infer_worker.config.overwrite_output is True
    assert infer_worker.config.label_y_offset_px == 4
    assert "推理完成" in infer_page.result_summary.text()
    assert "run_20260520_112000" in infer_page.log_box.toPlainText()


def test_infer_page_stop_button_requests_running_task_cancel(tmp_path: Path) -> None:
    """Infer stop button requests cancellation on the active infer task."""
    qt_app = app()
    registry = TaskRegistry(task_dir=tmp_path / "tasks")
    task = registry.create_task("infer")
    registry.start_task(task.task_id, total=3, message="正在推理")
    window = make_window(task_registry=registry, infer_worker=FakeInferWorker())
    window.show()
    qt_app.processEvents()
    QTest.mouseClick(window.login_view.demo_login_button, Qt.MouseButton.LeftButton)
    QTest.mouseClick(
        window.workbench_view.nav_buttons["infer"], Qt.MouseButton.LeftButton
    )

    infer_page = window.workbench_view.infer_page
    infer_page.refresh_running_progress()
    assert infer_page.stop_button.isEnabled()
    QTest.mouseClick(infer_page.stop_button, Qt.MouseButton.LeftButton)

    cancelled = registry.get(task.task_id)
    assert cancelled.status == "running"
    assert cancelled.is_cancel_requested is True
    assert not infer_page.stop_button.isEnabled()
    assert "停止" in infer_page.result_summary.text()


def test_infer_page_renders_cancelled_outcome_as_stopped(tmp_path: Path) -> None:
    """Infer page treats worker cancellation as a stopped run, not a failure."""
    qt_app = app()
    infer_worker = CancelledInferWorker()
    window = make_window(infer_worker=infer_worker)
    window.show()
    qt_app.processEvents()
    QTest.mouseClick(window.login_view.demo_login_button, Qt.MouseButton.LeftButton)
    QTest.mouseClick(
        window.workbench_view.nav_buttons["infer"], Qt.MouseButton.LeftButton
    )

    infer_page = window.workbench_view.infer_page
    infer_page.site_input.setText(str(tmp_path / "site"))
    infer_page.model_input.setText(str(tmp_path / "best.pt"))
    QTest.mouseClick(infer_page.run_button, Qt.MouseButton.LeftButton)

    assert "停止" in infer_page.result_summary.text()
    assert "failed" not in infer_page.log_box.toPlainText()


def test_infer_page_renders_persisted_running_progress(tmp_path: Path) -> None:
    """Infer page can render persisted progress for a running inference task."""
    qt_app = app()
    registry = TaskRegistry(task_dir=tmp_path / "tasks")
    task = registry.create_task("infer")
    registry.start_task(task.task_id, total=1000, message="准备推理")
    registry.update_progress(task.task_id, current=275, total=1000, message="已推理 275/1000")
    window = make_window(task_registry=registry, infer_worker=FakeInferWorker())
    window.show()
    qt_app.processEvents()
    QTest.mouseClick(window.login_view.demo_login_button, Qt.MouseButton.LeftButton)
    QTest.mouseClick(
        window.workbench_view.nav_buttons["infer"], Qt.MouseButton.LeftButton
    )

    infer_page = window.workbench_view.infer_page
    infer_page.refresh_running_progress()

    assert "275/1000" in infer_page.progress_label.text()
    assert infer_page.progress_bar.value() == 275
    assert infer_page.progress_bar.maximum() == 1000


def test_infer_page_keeps_waiting_before_task_is_registered(tmp_path: Path) -> None:
    """Infer page polling does not stop before the worker creates its task."""
    qt_app = app()
    registry = TaskRegistry(task_dir=tmp_path / "tasks")
    window = make_window(task_registry=registry, infer_worker=FakeInferWorker())
    window.show()
    qt_app.processEvents()
    QTest.mouseClick(window.login_view.demo_login_button, Qt.MouseButton.LeftButton)
    QTest.mouseClick(
        window.workbench_view.nav_buttons["infer"], Qt.MouseButton.LeftButton
    )

    infer_page = window.workbench_view.infer_page
    infer_page._infer_running = True
    infer_page._progress_timer.start()
    infer_page.refresh_running_progress()

    assert infer_page._progress_timer.isActive()
    assert "等待任务登记" in infer_page.progress_label.text()


def test_infer_page_builds_independent_folder_config(tmp_path: Path) -> None:
    """Infer page independent mode uses image_folder and output root without mapping."""
    qt_app = app()
    infer_worker = FakeInferWorker()
    window = make_window(infer_worker=infer_worker)
    window.show()
    qt_app.processEvents()
    QTest.mouseClick(window.login_view.demo_login_button, Qt.MouseButton.LeftButton)
    QTest.mouseClick(
        window.workbench_view.nav_buttons["infer"], Qt.MouseButton.LeftButton
    )

    infer_page = window.workbench_view.infer_page
    QTest.mouseClick(infer_page.independent_mode_button, Qt.MouseButton.LeftButton)
    image_root = tmp_path / "images"
    output_root = tmp_path / "runs"
    model = tmp_path / "best.pt"
    infer_page.image_folder_input.setText(str(image_root))
    infer_page.output_root_input.setText(str(output_root))
    infer_page.model_input.setText(str(model))
    QTest.mouseClick(infer_page.run_button, Qt.MouseButton.LeftButton)

    assert infer_worker.config is not None
    assert infer_worker.config.image_source == "folder"
    assert infer_worker.config.image_folder == image_root
    assert infer_worker.config.output_base_dir == output_root
    assert infer_worker.config.site_folder == image_root


def test_infer_page_rejects_empty_paths_before_building_config() -> None:
    """Infer page blocks blank model/source paths instead of resolving cwd."""
    qt_app = app()
    infer_worker = FakeInferWorker()
    window = make_window(infer_worker=infer_worker)
    window.show()
    qt_app.processEvents()
    QTest.mouseClick(window.login_view.demo_login_button, Qt.MouseButton.LeftButton)
    QTest.mouseClick(
        window.workbench_view.nav_buttons["infer"], Qt.MouseButton.LeftButton
    )

    infer_page = window.workbench_view.infer_page
    QTest.mouseClick(infer_page.run_button, Qt.MouseButton.LeftButton)

    assert infer_worker.config is None
    assert "请选择模型文件" in infer_page.result_summary.text()


