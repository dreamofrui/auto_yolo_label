"""
Test EmptyState component from gui/components.py

Verifies compliance with UI_DESIGN_SPEC_v2.md section 2.12.
"""

import pytest
from PySide6.QtWidgets import QApplication, QPushButton, QLabel
from PySide6.QtCore import Qt

from gui.components import EmptyState
from gui.design_system import DARK_THEME, FONT_SIZE


@pytest.fixture(scope="module")
def qapp():
    """Ensure QApplication exists for widget tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


def test_empty_state_default_creation(qapp):
    """Test EmptyState can be created with default parameters."""
    empty_state = EmptyState()

    assert empty_state is not None
    assert empty_state.objectName() == "emptyStateContainer"
    assert empty_state.minimumHeight() == 320


def test_empty_state_custom_content(qapp):
    """Test EmptyState with custom icon, title, and description."""
    empty_state = EmptyState(
        icon="📋",
        title="暂无任务记录",
        description="当您运行扫描、抽样、训练、推理等任务时，任务状态会显示在这里。"
    )

    # Check icon
    assert empty_state._icon_label.text() == "📋"
    assert empty_state._icon_label.objectName() == "emptyStateIcon"
    assert "64px" in empty_state._icon_label.styleSheet()
    assert "0.6" in empty_state._icon_label.styleSheet()  # opacity

    # Check title
    assert empty_state._title_label.text() == "暂无任务记录"
    assert empty_state._title_label.objectName() == "emptyStateTitle"
    assert f"{FONT_SIZE.H3}px" in empty_state._title_label.styleSheet()
    assert DARK_THEME.TEXT_SECONDARY in empty_state._title_label.styleSheet()
    assert "600" in empty_state._title_label.styleSheet()  # font-weight

    # Check description
    assert "当您运行扫描" in empty_state._desc_label.text()
    assert empty_state._desc_label.objectName() == "emptyStateDescription"
    assert f"{FONT_SIZE.BODY}px" in empty_state._desc_label.styleSheet()
    assert DARK_THEME.TEXT_TERTIARY in empty_state._desc_label.styleSheet()
    assert "1.6" in empty_state._desc_label.styleSheet()  # line-height
    assert empty_state._desc_label.maximumWidth() == 480


def test_empty_state_setters(qapp):
    """Test EmptyState setter methods."""
    empty_state = EmptyState()

    empty_state.setIcon("🔍")
    assert empty_state._icon_label.text() == "🔍"

    empty_state.setTitle("New Title")
    assert empty_state._title_label.text() == "New Title"

    empty_state.setDescription("New description")
    assert empty_state._desc_label.text() == "New description"


def test_empty_state_primary_button(qapp):
    """Test adding primary action button."""
    empty_state = EmptyState()

    button = QPushButton("返回首页开始工作")
    empty_state.addPrimaryButton(button)

    # Verify button was added to action layout
    assert empty_state._action_layout.count() == 1


def test_empty_state_add_button_alias(qapp):
    """Test addButton method (alias for addPrimaryButton)."""
    empty_state = EmptyState()

    button = QPushButton("前往推理页")
    empty_state.addButton(button)

    assert empty_state._action_layout.count() == 1


def test_empty_state_secondary_link(qapp):
    """Test adding secondary action link."""
    empty_state = EmptyState()

    link = QLabel("查看使用手册")
    empty_state.addSecondaryLink(link)

    # Verify link was added
    assert empty_state._action_layout.count() == 1

    # Verify link styling
    assert link.objectName() == "emptyStateSecondaryLink"
    assert "13px" in link.styleSheet()
    assert DARK_THEME.BRAND_PRIMARY in link.styleSheet()
    assert link.cursor().shape() == Qt.PointingHandCursor


def test_empty_state_both_actions(qapp):
    """Test adding both primary button and secondary link."""
    empty_state = EmptyState(
        icon="📂",
        title="还没有推理运行记录",
        description="在推理页运行推理任务后，推理结果会列在这里。"
    )

    # Add primary button
    primary_btn = QPushButton("前往推理页")
    empty_state.addPrimaryButton(primary_btn)

    # Add secondary link
    secondary_link = QLabel("了解推理流程")
    empty_state.addSecondaryLink(secondary_link)

    # Verify both were added
    assert empty_state._action_layout.count() == 2


def test_empty_state_all_scenarios(qapp):
    """Test all scenarios from UI_DESIGN_SPEC_v2.md section 2.12."""

    scenarios = [
        ("📋", "暂无任务记录", "当您运行扫描、抽样、训练、推理等任务时"),
        ("📂", "还没有推理运行记录", "在推理页运行推理任务后"),
        ("🌳", "未找到产品分组", "请先在扫描页扫描"),
        ("🔍", "未找到匹配结果", "尝试使用不同的关键词"),
        ("📸", "数据集目录为空", "训练需要标准 YOLO 数据集"),
        ("🗺️", "独立推理不支持复核模式", "复核模式需要 Flow 模式推理结果"),
    ]

    for icon, title, desc_fragment in scenarios:
        empty_state = EmptyState(icon=icon, title=title, description=desc_fragment)

        assert empty_state._icon_label.text() == icon
        assert empty_state._title_label.text() == title
        assert desc_fragment in empty_state._desc_label.text()


def test_empty_state_container_padding(qapp):
    """Test container has correct padding per spec."""
    empty_state = EmptyState()

    # Get layout margins
    layout = empty_state.layout()
    left, top, right, bottom = layout.getContentsMargins()

    # Spec: padding 60px 40px (top/bottom=60, left/right=40)
    assert left == 40
    assert right == 40
    assert top == 60
    assert bottom == 60
