"""
AutoLabeler 主窗口
使用 QFluentWidgets 的 FluentWindow 作为主窗口框架
"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from pathlib import Path
from qfluentwidgets import (
    FluentWindow,
    NavigationItemPosition,
    FluentIcon,
    setTheme,
    Theme,
    InfoBar,
    InfoBarPosition,
)

from gui.pages.base_page import BasePage
from gui.pages.home_page import HomePage
from gui.pages.scan_page import ScanPage
from gui.pages.sample_page import SamplePage
from gui.pages.train_page import TrainPage
from gui.pages.inference_page import InferencePage
from gui.pages.label_viewer_page import LabelViewerPage
from gui.pages.restore_page import RestorePage
from gui.pages.convert_page import ConvertPage
from gui.pages.settings_page import SettingsPage


class MainWindow(FluentWindow):
    """
    AutoLabeler 主窗口
    """

    # 窗口默认配置
    DEFAULT_WIDTH = 1200
    DEFAULT_HEIGHT = 800
    MIN_WIDTH = 960
    MIN_HEIGHT = 640

    def __init__(self):
        super().__init__()

        # 页面映射
        self.pages = {}

        # 初始化窗口
        self._setup_window()

        # 初始化导航
        self._setup_navigation()

        # 初始化页面
        self._setup_pages()

    def _setup_window(self):
        """设置窗口属性"""
        self.setWindowTitle("AutoLabeler - 智能标注工具")
        self.resize(self.DEFAULT_WIDTH, self.DEFAULT_HEIGHT)
        self.setMinimumSize(self.MIN_WIDTH, self.MIN_HEIGHT)

        # 设置主题
        setTheme(Theme.AUTO)

    def _setup_navigation(self):
        """设置导航栏"""
        # 添加导航项目在子类 _setup_pages 中完成
        pass

    def _setup_pages(self):
        """
        设置所有页面
        添加所有功能页面
        """
        # 添加首页
        self._add_page(
            HomePage(self),
            FluentIcon.HOME,
            "首页",
            NavigationItemPosition.TOP
        )

        # 添加扫描页
        self._add_page(
            ScanPage(self),
            FluentIcon.SEARCH,
            "扫描",
            NavigationItemPosition.TOP
        )

        # 添加抽样页
        self._add_page(
            SamplePage(self),
            FluentIcon.FILTER,
            "抽样",
            NavigationItemPosition.TOP
        )

        # 添加训练页
        self._add_page(
            TrainPage(self),
            FluentIcon.IOT,
            "训练",
            NavigationItemPosition.TOP
        )

        # 添加推理页
        self._add_page(
            InferencePage(self),
            FluentIcon.ROBOT,
            "推理",
            NavigationItemPosition.TOP
        )

        # 添加标注检查页
        self._add_page(
            LabelViewerPage(self),
            FluentIcon.VIEW,
            "标注检查",
            NavigationItemPosition.TOP
        )

        # 添加还原页
        self._add_page(
            RestorePage(self),
            FluentIcon.SYNC,
            "还原",
            NavigationItemPosition.TOP
        )

        # 添加转换页
        self._add_page(
            ConvertPage(self),
            FluentIcon.CODE,
            "转换",
            NavigationItemPosition.TOP
        )

        # 添加设置页（底部）
        self._add_page(
            SettingsPage(self),
            FluentIcon.SETTING,
            "设置",
            NavigationItemPosition.BOTTOM
        )

    def _add_page(self, page: BasePage, icon, text: str, position=None):
        """
        添加页面到导航栏

        Args:
            page: 页面对象
            icon: 图标
            text: 页面标题
            position: 导航位置
        """
        # 添加到导航栏
        if position is None:
            position = NavigationItemPosition.TOP

        self.addSubInterface(page, icon, text, position)
        self.pages[text] = page

        # 如果页面有进入/离开回调，连接信号
        if hasattr(page, 'on_enter') or hasattr(page, 'on_leave'):
            self.stackedWidget.currentChanged.connect(
                lambda index: self._on_page_changed(index, page)
            )

    def _on_page_changed(self, index: int, page: BasePage):
        """
        页面变化时调用

        Args:
            index: 新页面索引
            page: 页面对象
        """
        current_widget = self.stackedWidget.currentWidget()
        if current_widget == page:
            if hasattr(page, 'on_enter'):
                page.on_enter()
        else:
            if hasattr(page, 'on_leave'):
                page.on_leave()

    def show_info(self, title: str, content: str, duration=3000):
        """
        显示信息提示

        Args:
            title: 标题
            content: 内容
            duration: 显示时长（毫秒）
        """
        InfoBar.success(
            title=title,
            content=content,
            parent=self,
            position=InfoBarPosition.TOP,
            duration=duration
        )

    def show_warning(self, title: str, content: str, duration=3000):
        """
        显示警告提示

        Args:
            title: 标题
            content: 内容
            duration: 显示时长（毫秒）
        """
        InfoBar.warning(
            title=title,
            content=content,
            parent=self,
            position=InfoBarPosition.TOP,
            duration=duration
        )

    def show_error(self, title: str, content: str, duration=5000):
        """
        显示错误提示

        Args:
            title: 标题
            content: 内容
            duration: 显示时长（毫秒）
        """
        InfoBar.error(
            title=title,
            content=content,
            parent=self,
            position=InfoBarPosition.TOP,
            duration=duration
        )

    def get_page(self, name: str) -> BasePage:
        """
        获取指定名称的页面

        Args:
            name: 页面名称

        Returns:
            页面对象，如果不存在返回 None
        """
        return self.pages.get(name)
