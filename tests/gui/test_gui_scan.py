"""Scoped tests for the scan tool page."""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QLabel
from core.scanner import ScanResult, ScanStatistics
from gui.workbench import AutoLabelerWindow

from conftest import (
    app,
    make_image,
    make_scanned_site,
    make_window,
    set_task_timestamp,
)

class FakeScanWorker:
    """Small fake worker that records ScanConfig from the GUI."""

    def __init__(self) -> None:
        self.config = None

    def run(self, config):
        self.config = config
        result = ScanResult(
            mapping_path=config.site_folder / ".autolabeler" / "mapping.json",
            classes_path=config.site_folder / ".autolabeler" / "classes.txt",
            statistics=ScanStatistics(
                total_images=8,
                total_codes=2,
                total_products=3,
            ),
            classes=["CodeA", "CodeB"],
            products={"CodeA": {"Product1": 5}, "CodeB": {"Product2": 3}},
        )

        class Outcome:
            success = True
            error = None
            task = None

            def __init__(self, result):
                self.result = result

        return Outcome(result)


def test_scan_page_builds_config_and_renders_result(tmp_path: Path) -> None:
    """Scan page builds ScanConfig and displays mapping/classes outputs."""
    qt_app = app()
    scan_worker = FakeScanWorker()
    window = make_window(scan_worker=scan_worker)
    window.show()
    qt_app.processEvents()
    QTest.mouseClick(window.login_view.demo_login_button, Qt.MouseButton.LeftButton)
    QTest.mouseClick(
        window.workbench_view.nav_buttons["scan"], Qt.MouseButton.LeftButton
    )

    scan_page = window.workbench_view.scan_page
    site = tmp_path / "site"
    scan_page.site_input.setText(str(site))
    QTest.mouseClick(scan_page.run_button, Qt.MouseButton.LeftButton)

    assert scan_worker.config is not None
    assert scan_worker.config.site_folder == site
    assert scan_worker.config.output_dir is None
    assert "扫描完成" in scan_page.result_summary.text()
    assert "mapping.json" in scan_page.result_summary.text()
    assert "classes.txt" in scan_page.result_summary.text()
    assert "mapping.json" in scan_page.log_box.toPlainText()
    assert scan_page.structure_example_panel.objectName() == "scanStructureExample"
    example_text = " ".join(
        label.text()
        for label in scan_page.structure_example_panel.findChildren(QLabel)
    )
    assert "site/" in example_text
    assert "CodeA/" in example_text
    assert "Product1/" in example_text


def test_scan_page_rejects_empty_site_before_building_config() -> None:
    """Scan page blocks blank site path before constructing Path('')."""
    qt_app = app()
    scan_worker = FakeScanWorker()
    window = make_window(scan_worker=scan_worker)
    window.show()
    qt_app.processEvents()
    QTest.mouseClick(window.login_view.demo_login_button, Qt.MouseButton.LeftButton)
    QTest.mouseClick(
        window.workbench_view.nav_buttons["scan"], Qt.MouseButton.LeftButton
    )

    scan_page = window.workbench_view.scan_page
    QTest.mouseClick(scan_page.run_button, Qt.MouseButton.LeftButton)

    assert scan_worker.config is None
    assert "请选择站点路径" in scan_page.result_summary.text()


