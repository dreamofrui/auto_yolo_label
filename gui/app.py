"""
AutoLabeler GUI 应用程序
使用 PySide6 + QFluentWidgets 构建
"""

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QTranslator
from PySide6.QtGui import QFont
from pathlib import Path
import sys

from gui.main_window import MainWindow


class AutoLabelerApp(QApplication):
    """
    AutoLabeler 应用程序类
    """

    def __init__(self):
        super().__init__(sys.argv)

        self._init_application()
        self._init_window()

    def _init_application(self):
        """初始化应用程序设置"""
        # 设置应用程序名称
        self.setApplicationName("AutoLabeler")
        self.setApplicationDisplayName("AutoLabeler 智能标注工具")
        self.setOrganizationName("AutoLabeler")

        # 设置应用程序样式
        self.setStyle("Fusion")

        # 设置默认字体
        font = QFont("Microsoft YaHei UI", 9)
        self.setFont(font)

    def _init_window(self):
        """初始化主窗口"""
        self.main_window = MainWindow()
        self.main_window.show()


def main():
    """应用程序入口点"""
    # 启用高 DPI 缩放
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling)
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps)

    # 创建并运行应用
    app = AutoLabelerApp()

    return sys.exit(app.exec())


if __name__ == "__main__":
    main()
