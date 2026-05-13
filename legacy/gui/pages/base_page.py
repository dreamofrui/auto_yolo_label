"""
AutoLabeler 页面基类
所有功能页面的基类，提供通用布局和方法
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout
from qfluentwidgets import ScrollArea, SubtitleLabel, StrongBodyLabel


class BasePage(ScrollArea):
    """
    功能页面基类
    提供通用的布局和方法
    """

    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.title = title
        # 设置对象名称（QFluentWidgets 需要）
        self.setObjectName(title)
        self._setup_ui()

    def _setup_ui(self):
        """设置基本UI"""
        # 设置滚动区域属性
        self.setWidgetResizable(True)
        self.setStyleSheet("background: transparent;")
        self.setViewportMargins(0, 0, 0, 0)

        # 创建内容容器
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(36, 20, 36, 20)
        self.content_layout.setSpacing(16)

        # 设置内容
        self.setWidget(self.content_widget)

        # 初始化页面UI
        self.init_ui()

    def init_ui(self):
        """
        初始化页面UI（子类重写）
        子类应该重写此方法来添加自定义UI组件
        """
        pass

    def on_enter(self):
        """
        进入页面时调用（子类重写）
        """
        pass

    def on_leave(self):
        """
        离开页面时调用（子类重写）
        """
        pass

    def add_title(self, text: str):
        """
        添加标题到页面

        Args:
            text: 标题文本
        """
        title = SubtitleLabel(text)
        self.content_layout.addWidget(title)
        return title

    def add_description(self, text: str):
        """
        添加描述文本到页面

        Args:
            text: 描述文本
        """
        desc = StrongBodyLabel(text)
        desc.setWordWrap(True)
        self.content_layout.addWidget(desc)
        return desc

    def add_spacing(self, spacing: int = 16):
        """
        添加间距

        Args:
            spacing: 间距大小
        """
        self.content_layout.addSpacing(spacing)

    def add_stretch(self, stretch: int = 1):
        """
        添加弹性空间

        Args:
            stretch: 弹性系数
        """
        self.content_layout.addStretch(stretch)

    def clear_layout(self):
        """清空布局"""
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
