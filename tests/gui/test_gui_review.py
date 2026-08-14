"""Scoped tests for the review tool page."""

from __future__ import annotations

from pathlib import Path

import pytest
from pathlib import Path
import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QHeaderView
from core.label_inspector import InferenceRun, ProductLabel, RunTreeNode
from gui.workbench import AutoLabelerWindow

from conftest import FakeLabelImgWorker
from conftest import (
    app,
    make_image,
    make_scanned_site,
    make_window,
    set_task_timestamp,
)

class FakeInspectorWorker:
    """Small fake inspector worker that returns one run and product node."""

    def __init__(self, site: Path, *, product: str = "Product1") -> None:
        self.site = site
        self.product = product
        self.list_config = None
        self.tree_config = None
        self.labels_config = None

    def list_runs(self, config):
        self.list_config = config
        run = InferenceRun(
            run_id="run_20260520_120000",
            path=config.site_folder
            / ".autolabeler"
            / "inference_results"
            / "run_20260520_120000",
            config_exists=True,
            config={},
            created_at="2026-05-20 12:00:00",
        )

        class Outcome:
            success = True
            error = None
            task = None

            def __init__(self, result):
                self.result = result

        return Outcome([run])

    def get_run_tree(self, config):
        self.tree_config = config
        node = RunTreeNode(
            code="CodeA",
            product=self.product,
            label_count=2,
            empty_count=1,
            path=config.site_folder
            / ".autolabeler"
            / "inference_results"
            / config.run_id
            / "labels"
            / "CodeA"
            / self.product,
        )

        class Outcome:
            success = True
            error = None
            task = None

            def __init__(self, result):
                self.result = result

        return Outcome([node])

    def get_product_labels(self, config):
        self.labels_config = config
        product_dir = config.site_folder / "CodeA" / self.product
        labels_dir = (
            config.site_folder
            / ".autolabeler"
            / "inference_results"
            / config.run_id
            / "labels"
            / "CodeA"
            / self.product
        )
        result = [
            ProductLabel(
                image_name="a.jpg",
                image_path=product_dir / "a.jpg",
                label_path=labels_dir / "a.txt",
                object_count=1,
                missing_label=False,
            ),
            ProductLabel(
                image_name="b.jpg",
                image_path=product_dir / "b.jpg",
                label_path=labels_dir / "b.txt",
                object_count=0,
                missing_label=True,
            ),
        ]

        class Outcome:
            success = True
            error = None
            task = None

            def __init__(self, result):
                self.result = result

        return Outcome(result)


def test_review_page_loads_product_and_launches_labelimg(tmp_path: Path) -> None:
    """Review page prepares Flow prediction review and launches LabelImg."""
    qt_app = app()
    labelimg_worker = FakeLabelImgWorker()
    inspector_worker = FakeInspectorWorker(tmp_path / "site")
    window = make_window(
        labelimg_worker=labelimg_worker,
        inspector_worker=inspector_worker,
    )
    window.show()
    qt_app.processEvents()
    QTest.mouseClick(window.login_view.demo_login_button, Qt.MouseButton.LeftButton)
    QTest.mouseClick(
        window.workbench_view.nav_buttons["review"], Qt.MouseButton.LeftButton
    )

    review_page = window.workbench_view.review_page
    site = tmp_path / "site"
    review_page.site_input.setText(str(site))
    QTest.mouseClick(review_page.load_runs_button, Qt.MouseButton.LeftButton)
    assert review_page.run_combo.count() == 1
    assert review_page.review_empty_state_panel.objectName() == "reviewEmptyState"
    assert "先选择站点" in review_page.review_empty_text.text()
    assert "run_20260520_120000" in review_page.run_combo.itemText(0)
    assert not hasattr(review_page, "run_input")
    assert not hasattr(review_page, "code_input")
    assert not hasattr(review_page, "product_input")

    QTest.mouseClick(review_page.load_tree_button, Qt.MouseButton.LeftButton)
    assert review_page.run_tree.topLevelItemCount() == 1
    code_item = review_page.run_tree.topLevelItem(0)
    assert code_item.text(0) == "CodeA"
    assert code_item.childCount() == 1
    product_item = code_item.child(0)
    assert product_item.text(0) == "Product1"
    review_page.run_tree.setCurrentItem(product_item)

    QTest.mouseClick(review_page.prepare_button, Qt.MouseButton.LeftButton)
    assert "缺少标签 1" in review_page.result_summary.text()
    assert "图片目录" in review_page.review_status_summary.text()
    assert "标签目录" in review_page.review_status_summary.text()
    assert "classes.txt" in review_page.review_status_summary.text()

    QTest.mouseClick(review_page.launch_button, Qt.MouseButton.LeftButton)
    assert labelimg_worker.launch_config is not None
    assert labelimg_worker.launch_config.image_dir == site / "CodeA" / "Product1"
    assert (
        labelimg_worker.launch_config.label_dir
        == site
        / ".autolabeler"
        / "inference_results"
        / "run_20260520_120000"
        / "labels"
        / "CodeA"
        / "Product1"
    )
    assert labelimg_worker.launch_config.classes_file == site / ".autolabeler" / "classes.txt"


def test_review_page_uses_compact_run_combo_and_full_product_tree(
    tmp_path: Path,
) -> None:
    """Review page keeps run selection compact and gives product names room."""
    qt_app = app()
    long_product = "H4A270FDF10_EXTENDED_PRODUCT_NAME_SHOULD_REMAIN_VISIBLE"
    inspector_worker = FakeInspectorWorker(tmp_path / "site", product=long_product)
    window = make_window(inspector_worker=inspector_worker)
    window.resize(1024, 680)
    window.show()
    qt_app.processEvents()
    QTest.mouseClick(window.login_view.demo_login_button, Qt.MouseButton.LeftButton)
    QTest.mouseClick(
        window.workbench_view.nav_buttons["review"], Qt.MouseButton.LeftButton
    )

    review_page = window.workbench_view.review_page
    review_page.site_input.setText(str(tmp_path / "site"))
    QTest.mouseClick(review_page.load_runs_button, Qt.MouseButton.LeftButton)

    assert hasattr(review_page, "run_combo")
    assert not hasattr(review_page, "run_list")
    assert review_page.run_combo.count() == 1
    assert review_page.run_combo.currentData() == "run_20260520_120000"

    QTest.mouseClick(review_page.load_tree_button, Qt.MouseButton.LeftButton)
    code_item = review_page.run_tree.topLevelItem(0)
    product_item = code_item.child(0)
    assert product_item.text(0) == long_product
    assert f"CodeA/{long_product}" in product_item.toolTip(0)
    assert "标签：2，空标签：1" in product_item.toolTip(0)
    assert (
        review_page.run_tree.header().sectionResizeMode(0)
        == QHeaderView.ResizeMode.Stretch
    )


def test_review_page_keeps_prepare_actions_before_growing_status_panel(
    tmp_path: Path,
) -> None:
    """Review action buttons stay above the prepared path summary in small windows."""
    qt_app = app()
    inspector_worker = FakeInspectorWorker(tmp_path / "site")
    window = make_window(inspector_worker=inspector_worker)
    window.resize(1024, 680)
    window.show()
    qt_app.processEvents()
    QTest.mouseClick(window.login_view.demo_login_button, Qt.MouseButton.LeftButton)
    QTest.mouseClick(
        window.workbench_view.nav_buttons["review"], Qt.MouseButton.LeftButton
    )

    review_page = window.workbench_view.review_page
    review_page.site_input.setText(str(tmp_path / "site"))
    QTest.mouseClick(review_page.prepare_button, Qt.MouseButton.LeftButton)

    form = review_page.review_form.layout()
    actions_index = form.indexOf(review_page.review_actions_widget)
    status_index = form.indexOf(review_page.review_status_panel)
    actions_row = form.getItemPosition(actions_index)[0]
    status_row = form.getItemPosition(status_index)[0]

    assert actions_row < status_row
    assert review_page.prepare_button.isVisible()
    assert review_page.review_launch_button.isVisible()


def test_review_page_launch_auto_prepares_selected_node(tmp_path: Path) -> None:
    """Opening review prepares the selected node automatically if needed."""
    qt_app = app()
    labelimg_worker = FakeLabelImgWorker()
    inspector_worker = FakeInspectorWorker(tmp_path / "site")
    window = make_window(
        labelimg_worker=labelimg_worker,
        inspector_worker=inspector_worker,
    )
    window.show()
    qt_app.processEvents()
    QTest.mouseClick(window.login_view.demo_login_button, Qt.MouseButton.LeftButton)
    QTest.mouseClick(
        window.workbench_view.nav_buttons["review"], Qt.MouseButton.LeftButton
    )

    review_page = window.workbench_view.review_page
    site = tmp_path / "site"
    review_page.site_input.setText(str(site))
    QTest.mouseClick(review_page.load_runs_button, Qt.MouseButton.LeftButton)
    QTest.mouseClick(review_page.load_tree_button, Qt.MouseButton.LeftButton)
    QTest.mouseClick(review_page.launch_button, Qt.MouseButton.LeftButton)

    assert inspector_worker.labels_config is not None
    assert labelimg_worker.launch_config is not None
    assert labelimg_worker.launch_config.image_dir == site / "CodeA" / "Product1"
    assert "已启动 LabelImg" in review_page.result_summary.text()


def test_review_page_prepared_paths_do_not_expand_left_panel(
    tmp_path: Path,
) -> None:
    """Prepared long Windows-style paths stay bounded inside the status panel."""
    qt_app = app()
    long_site = (
        tmp_path
        / "very_long_review_site_root"
        / ("segment_" * 12)
        / ("product_" * 8)
    )
    inspector_worker = FakeInspectorWorker(long_site)
    window = make_window(inspector_worker=inspector_worker)
    window.resize(1024, 680)
    window.show()
    qt_app.processEvents()
    QTest.mouseClick(window.login_view.demo_login_button, Qt.MouseButton.LeftButton)
    QTest.mouseClick(
        window.workbench_view.nav_buttons["review"], Qt.MouseButton.LeftButton
    )

    review_page = window.workbench_view.review_page
    review_page.site_input.setText(str(long_site))
    QTest.mouseClick(review_page.prepare_button, Qt.MouseButton.LeftButton)

    assert review_page.review_status_summary.minimumSizeHint().width() <= (
        review_page.review_status_panel.width()
    )
    assert review_page.review_status_summary.toolTip()
    assert "..." in review_page.review_status_summary.text()


def test_review_page_rejects_empty_site_before_listing_runs() -> None:
    """Review page blocks blank site path before list-runs config construction."""
    qt_app = app()
    labelimg_worker = FakeLabelImgWorker()
    inspector_worker = FakeInspectorWorker(Path("unused"))
    window = make_window(
        labelimg_worker=labelimg_worker,
        inspector_worker=inspector_worker,
    )
    window.show()
    qt_app.processEvents()
    QTest.mouseClick(window.login_view.demo_login_button, Qt.MouseButton.LeftButton)
    QTest.mouseClick(
        window.workbench_view.nav_buttons["review"], Qt.MouseButton.LeftButton
    )

    review_page = window.workbench_view.review_page
    QTest.mouseClick(review_page.load_runs_button, Qt.MouseButton.LeftButton)

    assert inspector_worker.list_config is None
    assert "请选择站点路径" in review_page.result_summary.text()


def test_review_page_invalidates_prepared_launch_when_inputs_change(
    tmp_path: Path,
) -> None:
    """Review page does not launch stale prepared paths after review inputs change."""
    qt_app = app()
    labelimg_worker = FakeLabelImgWorker()
    inspector_worker = FakeInspectorWorker(tmp_path / "site")
    window = make_window(
        labelimg_worker=labelimg_worker,
        inspector_worker=inspector_worker,
    )
    window.show()
    qt_app.processEvents()
    QTest.mouseClick(window.login_view.demo_login_button, Qt.MouseButton.LeftButton)
    QTest.mouseClick(
        window.workbench_view.nav_buttons["review"], Qt.MouseButton.LeftButton
    )

    review_page = window.workbench_view.review_page
    review_page.site_input.setText(str(tmp_path / "site"))
    QTest.mouseClick(review_page.prepare_button, Qt.MouseButton.LeftButton)
    assert "复核准备完成" in review_page.result_summary.text()

    review_page.site_input.setText(str(tmp_path / "site_changed"))
    QTest.mouseClick(review_page.launch_button, Qt.MouseButton.LeftButton)

    assert inspector_worker.labels_config is not None
    assert inspector_worker.labels_config.site_folder == tmp_path / "site_changed"
    assert labelimg_worker.launch_config is not None
    assert (
        labelimg_worker.launch_config.image_dir
        == tmp_path / "site_changed" / "CodeA" / "Product1"
    )

