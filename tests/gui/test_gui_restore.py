"""Scoped tests for the restore tool page."""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtCore import Qt, QPoint
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QCheckBox, QScrollArea
from core.restorer import RestorePreflightResult, RestoreResult
from utils.exceptions import ErrorCode, ErrorInfo
from gui.workbench import AutoLabelerWindow

from conftest import (
    app,
    make_image,
    make_scanned_site,
    make_window,
    set_task_timestamp,
)

def test_restore_page_labels_writeback_controls_clearly() -> None:
    """Restore page exposes real write-back controls instead of vague text."""
    qt_app = app()
    window = make_window()
    window.show()
    qt_app.processEvents()
    QTest.mouseClick(window.login_view.demo_login_button, Qt.MouseButton.LeftButton)
    QTest.mouseClick(
        window.workbench_view.nav_buttons["restore"], Qt.MouseButton.LeftButton
    )

    restore_page = window.workbench_view.restore_page
    assert isinstance(restore_page.overwrite_checkbox, QCheckBox)
    assert isinstance(restore_page.confirm_write_checkbox, QCheckBox)
    assert "已有 XML 冲突" in restore_page.overwrite_checkbox.text()
    assert "允许覆盖" in restore_page.overwrite_checkbox.text()
    assert "写回 XML 到原图同级目录" in restore_page.confirm_write_checkbox.text()
    assert restore_page.confirm_write_checkbox.objectName() == "riskCheckbox"
    assert restore_page.log_box.objectName() == "logBox"


class FakeRestoreWorker:
    """Small fake worker that records Restore configs from the GUI."""

    def __init__(self) -> None:
        self.flow_config = None
        self.independent_config = None
        self.preflight_config = None
        self.preflight_independent_config = None

    def preflight(self, config):
        self.preflight_config = config
        result = RestorePreflightResult(
            mode=f"flow-{config.source_type}",
            can_execute=True,
            total_labels=3,
            matched_images=3,
            xml_to_write=3,
            classes_path=config.site_folder / ".autolabeler" / "classes.txt",
            target_folders=[config.site_folder / "CodeA" / "Product1"],
        )

        class Outcome:
            success = True
            error = None

            def __init__(self, result):
                self.result = result

        return Outcome(result)

    def preflight_independent(self, config):
        self.preflight_independent_config = config
        result = RestorePreflightResult(
            mode="independent",
            can_execute=True,
            total_labels=2,
            matched_images=2,
            xml_to_write=2,
            classes_path=config.classes_file or config.label_root / "classes.txt",
            target_folders=[config.image_root / "Product1"],
        )

        class Outcome:
            success = True
            error = None

            def __init__(self, result):
                self.result = result

        return Outcome(result)

    def run(self, config):
        self.flow_config = config
        result = RestoreResult(total=3, success=3, skipped=0, failed=0)

        class Outcome:
            success = True
            error = None
            task = None

            def __init__(self, result):
                self.result = result

        return Outcome(result)

    def run_independent(self, config):
        self.independent_config = config
        result = RestoreResult(total=2, success=2, skipped=0, failed=0)

        class Outcome:
            success = True
            error = None
            task = None

            def __init__(self, result):
                self.result = result

        return Outcome(result)


def test_restore_page_requires_preflight_and_confirmation(tmp_path: Path) -> None:
    """Restore page blocks writes until preflight and confirmation are complete."""
    qt_app = app()
    restore_worker = FakeRestoreWorker()
    window = make_window(restore_worker=restore_worker)
    window.show()
    qt_app.processEvents()
    QTest.mouseClick(window.login_view.demo_login_button, Qt.MouseButton.LeftButton)
    QTest.mouseClick(
        window.workbench_view.nav_buttons["restore"], Qt.MouseButton.LeftButton
    )

    restore_page = window.workbench_view.restore_page
    restore_page.site_input.setText(str(tmp_path / "site"))
    restore_page.run_input.setText("run_20260520_120000")

    assert not restore_page.confirm_write_checkbox.isEnabled()
    assert not restore_page.run_button.isEnabled()
    assert restore_worker.flow_config is None

    QTest.mouseClick(restore_page.preflight_button, Qt.MouseButton.LeftButton)
    assert restore_worker.preflight_config is not None
    assert "预检通过" in restore_page.result_summary.text()
    assert "匹配质量" in restore_page.preflight_match_summary.text()
    assert "写入影响" in restore_page.preflight_write_summary.text()
    assert "不覆盖已有 XML" in restore_page.preflight_write_summary.text()
    assert "等待写回确认" in restore_page.preflight_write_summary.text()
    assert restore_page.confirm_write_checkbox.isEnabled()
    assert not restore_page.run_button.isEnabled()

    QTest.mouseClick(restore_page.run_button, Qt.MouseButton.LeftButton)
    assert restore_worker.flow_config is None
    assert "预检通过" in restore_page.result_summary.text()

    QTest.mouseClick(
        restore_page.confirm_write_checkbox,
        Qt.MouseButton.LeftButton,
        pos=QPoint(8, restore_page.confirm_write_checkbox.height() // 2),
    )
    assert restore_page.run_button.isEnabled()
    QTest.mouseClick(restore_page.run_button, Qt.MouseButton.LeftButton)

    assert restore_worker.flow_config is not None
    assert restore_worker.flow_config.source_type == "inference"
    assert restore_worker.flow_config.run_id == "run_20260520_120000"
    assert "还原完成" in restore_page.result_summary.text()


def test_restore_page_keeps_write_actions_visible_after_preflight(
    tmp_path: Path,
) -> None:
    """Restore actions stay reachable in the small desktop baseline."""
    qt_app = app()
    restore_worker = FakeRestoreWorker()
    window = make_window(restore_worker=restore_worker)
    window.resize(1024, 680)
    window.show()
    qt_app.processEvents()
    QTest.mouseClick(window.login_view.demo_login_button, Qt.MouseButton.LeftButton)
    QTest.mouseClick(
        window.workbench_view.nav_buttons["restore"], Qt.MouseButton.LeftButton
    )

    restore_page = window.workbench_view.restore_page
    restore_page.site_input.setText(str(tmp_path / "site"))
    restore_page.run_input.setText("run_20260520_120000")
    QTest.mouseClick(restore_page.preflight_button, Qt.MouseButton.LeftButton)
    qt_app.processEvents()

    scroll = restore_page.findChild(QScrollArea, "toolScrollArea")
    assert scroll is not None

    def center_is_in_viewport(widget) -> bool:
        point = widget.mapTo(
            scroll.viewport(),
            QPoint(widget.width() // 2, widget.height() // 2),
        )
        return scroll.viewport().rect().contains(point)

    assert center_is_in_viewport(restore_page.preflight_button)
    assert center_is_in_viewport(restore_page.run_button)


def test_restore_page_builds_dataset_and_independent_configs(tmp_path: Path) -> None:
    """Restore page supports Flow dataset labels and Independent restore configs."""
    qt_app = app()
    restore_worker = FakeRestoreWorker()
    window = make_window(restore_worker=restore_worker)
    window.show()
    qt_app.processEvents()
    QTest.mouseClick(window.login_view.demo_login_button, Qt.MouseButton.LeftButton)
    QTest.mouseClick(
        window.workbench_view.nav_buttons["restore"], Qt.MouseButton.LeftButton
    )

    restore_page = window.workbench_view.restore_page
    restore_page.site_input.setText(str(tmp_path / "site"))
    restore_page.dataset_dir_input.setText(str(tmp_path / "dataset"))
    QTest.mouseClick(restore_page.dataset_mode_button, Qt.MouseButton.LeftButton)
    QTest.mouseClick(restore_page.preflight_button, Qt.MouseButton.LeftButton)
    QTest.mouseClick(
        restore_page.confirm_write_checkbox,
        Qt.MouseButton.LeftButton,
        pos=QPoint(8, restore_page.confirm_write_checkbox.height() // 2),
    )
    QTest.mouseClick(restore_page.run_button, Qt.MouseButton.LeftButton)

    assert restore_worker.flow_config is not None
    assert restore_worker.flow_config.source_type == "database"
    assert restore_worker.flow_config.database_dir == tmp_path / "dataset"

    restore_worker.flow_config = None
    classes_file = tmp_path / "metadata" / "classes.txt"
    restore_page.image_root_input.setText(str(tmp_path / "images"))
    restore_page.label_root_input.setText(str(tmp_path / "labels"))
    QTest.mouseClick(
        restore_page.independent_mode_button, Qt.MouseButton.LeftButton
    )
    assert restore_page.classes_file_input.isVisible()
    restore_page.classes_file_input.setText(str(classes_file))
    QTest.mouseClick(restore_page.preflight_button, Qt.MouseButton.LeftButton)
    QTest.mouseClick(
        restore_page.confirm_write_checkbox,
        Qt.MouseButton.LeftButton,
        pos=QPoint(8, restore_page.confirm_write_checkbox.height() // 2),
    )
    QTest.mouseClick(restore_page.run_button, Qt.MouseButton.LeftButton)

    assert restore_worker.flow_config is None
    assert restore_worker.independent_config is not None
    assert restore_worker.independent_config.image_root == tmp_path / "images"
    assert restore_worker.independent_config.label_root == tmp_path / "labels"
    assert restore_worker.independent_config.classes_file == classes_file


def test_restore_page_rejects_empty_paths_before_building_config() -> None:
    """Restore page blocks blank paths before constructing Path('')."""
    qt_app = app()
    restore_worker = FakeRestoreWorker()
    window = make_window(restore_worker=restore_worker)
    window.show()
    qt_app.processEvents()
    QTest.mouseClick(window.login_view.demo_login_button, Qt.MouseButton.LeftButton)
    QTest.mouseClick(
        window.workbench_view.nav_buttons["restore"], Qt.MouseButton.LeftButton
    )

    restore_page = window.workbench_view.restore_page
    QTest.mouseClick(restore_page.preflight_button, Qt.MouseButton.LeftButton)

    assert restore_worker.preflight_config is None
    assert "请选择站点路径" in restore_page.result_summary.text()


def test_restore_page_shows_actionable_preflight_error_details(tmp_path: Path) -> None:
    """Restore keeps the summary compact and exposes diagnostics in its log."""

    class FailingRestoreWorker(FakeRestoreWorker):
        def preflight_independent(self, config):
            self.preflight_independent_config = config

            class Outcome:
                success = False
                result = None
                error = ErrorInfo(
                    code="VALIDATION_ERROR",
                    message="Invalid YOLO box",
                    details=(
                        f"label_file: {config.label_root / 'Product1' / 'a.txt'}\n"
                        "line: 2\n"
                        "pixel_bounds: xmin=40 ymin=97 xmax=60 ymax=101\n"
                        "violation: ymax=101 exceeds image_height=100"
                    ),
                    retryable=False,
                )

            return Outcome()

    qt_app = app()
    restore_worker = FailingRestoreWorker()
    window = make_window(restore_worker=restore_worker)
    window.resize(1024, 680)
    window.show()
    qt_app.processEvents()
    QTest.mouseClick(window.login_view.demo_login_button, Qt.MouseButton.LeftButton)
    QTest.mouseClick(
        window.workbench_view.nav_buttons["restore"], Qt.MouseButton.LeftButton
    )

    restore_page = window.workbench_view.restore_page
    QTest.mouseClick(
        restore_page.independent_mode_button, Qt.MouseButton.LeftButton
    )
    restore_page.image_root_input.setText(str(tmp_path / "images"))
    restore_page.label_root_input.setText(str(tmp_path / "labels"))
    restore_page.classes_file_input.setText(str(tmp_path / "classes.txt"))
    QTest.mouseClick(restore_page.preflight_button, Qt.MouseButton.LeftButton)

    assert restore_page.result_summary.text() == (
        "预检失败：VALIDATION_ERROR: Invalid YOLO box"
    )
    log_text = restore_page.log_box.toPlainText()
    assert "[failed] 预检失败" in log_text
    assert "code: VALIDATION_ERROR" in log_text
    assert "message: Invalid YOLO box" in log_text
    assert f"label_file: {tmp_path / 'labels' / 'Product1' / 'a.txt'}" in log_text
    assert "line: 2" in log_text
    assert "pixel_bounds: xmin=40 ymin=97 xmax=60 ymax=101" in log_text
    assert "violation: ymax=101 exceeds image_height=100" in log_text
    assert not restore_page.confirm_write_checkbox.isEnabled()
    assert not restore_page.run_button.isEnabled()


def test_restore_page_shows_actionable_restore_error_details(tmp_path: Path) -> None:
    """A failed restore uses the same compact summary and detailed log."""

    class FailingRestoreWorker(FakeRestoreWorker):
        def run_independent(self, config):
            self.independent_config = config

            class Outcome:
                success = False
                result = None
                error = ErrorInfo(
                    code="VALIDATION_ERROR",
                    message="Invalid YOLO box",
                    details=(
                        f"label_file: {config.label_root / 'Product1' / 'a.txt'}\n"
                        "line: 1\n"
                        "violation: ymax=101 exceeds image_height=100"
                    ),
                    retryable=False,
                )

            return Outcome()

    qt_app = app()
    restore_worker = FailingRestoreWorker()
    window = make_window(restore_worker=restore_worker)
    window.show()
    qt_app.processEvents()
    QTest.mouseClick(window.login_view.demo_login_button, Qt.MouseButton.LeftButton)
    QTest.mouseClick(
        window.workbench_view.nav_buttons["restore"], Qt.MouseButton.LeftButton
    )

    restore_page = window.workbench_view.restore_page
    QTest.mouseClick(
        restore_page.independent_mode_button, Qt.MouseButton.LeftButton
    )
    restore_page.image_root_input.setText(str(tmp_path / "images"))
    restore_page.label_root_input.setText(str(tmp_path / "labels"))
    restore_page.classes_file_input.setText(str(tmp_path / "classes.txt"))
    QTest.mouseClick(restore_page.preflight_button, Qt.MouseButton.LeftButton)
    QTest.mouseClick(
        restore_page.confirm_write_checkbox,
        Qt.MouseButton.LeftButton,
        pos=QPoint(8, restore_page.confirm_write_checkbox.height() // 2),
    )
    QTest.mouseClick(restore_page.run_button, Qt.MouseButton.LeftButton)

    assert restore_page.result_summary.text() == (
        "还原失败：VALIDATION_ERROR: Invalid YOLO box"
    )
    log_text = restore_page.log_box.toPlainText()
    assert "[failed] 还原失败" in log_text
    assert "code: VALIDATION_ERROR" in log_text
    assert f"label_file: {tmp_path / 'labels' / 'Product1' / 'a.txt'}" in log_text
    assert "line: 1" in log_text
    assert "violation: ymax=101 exceeds image_height=100" in log_text


