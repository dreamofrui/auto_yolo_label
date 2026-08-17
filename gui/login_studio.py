"""Wayfinder Login Studio — modern space-first studio design for Issue #21."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import (
    QApplication, QFrame, QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget, QComboBox, QCheckBox
)

from gui.tool_defaults import ToolDefaults

class LoginStudio(QWidget):
    """Modern Wayfinder login studio (Issue #21)."""

    login_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("loginStudio")
        self._defaults = ToolDefaults()  # will be replaced by workbench

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Left: Story (40%)
        story = self._build_story()
        root.addWidget(story, 4)

        # Right: Form (60%)
        form = self._build_form()
        root.addWidget(form, 6)

    def _build_story(self) -> QWidget:
        frame = QFrame()
        frame.setObjectName("story")
        frame.setProperty("surfaceRole", "product")

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(56, 64, 56, 64)
        layout.setSpacing(0)

        brand = QLabel("Auto Labeler")
        brand.setObjectName("brand")

        headline = QLabel("AI 驱动的\n智能标注平台")
        headline.setObjectName("headline")
        headline.setWordWrap(True)

        subheadline = QLabel("使用先进的机器学习技术，自动完成数据标注任务，\n将标注效率提升 10 倍")
        subheadline.setObjectName("subheadline")
        subheadline.setWordWrap(True)

        # Theme switcher
        theme_combo = QComboBox()
        theme_combo.addItems(["Theme A (Dark)", "Theme B (Light)", "Theme C (Studio)"])
        theme_combo.setObjectName("themeSwitcher")
        theme_combo.currentIndexChanged.connect(self._on_theme_changed)

        layout.addWidget(brand)
        layout.addSpacing(90)
        layout.addWidget(headline)
        layout.addSpacing(24)
        layout.addWidget(subheadline)
        layout.addSpacing(64)
        layout.addWidget(theme_combo)
        layout.addStretch(1)

        footer = QLabel("© 2026 Auto Labeler. 企业级 AI 标注解决方案")
        footer.setObjectName("footer")
        layout.addWidget(footer)

        return frame

    def _build_form(self) -> QWidget:
        frame = QFrame()
        frame.setObjectName("form")
        frame.setProperty("surfaceRole", "access")

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(80, 64, 80, 64)
        layout.setSpacing(0)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title = QLabel("登录")
        title.setObjectName("title")

        subtitle = QLabel("欢迎回来，请输入您的凭据继续使用")
        subtitle.setObjectName("subtitle")
        subtitle.setWordWrap(True)

        username_label = QLabel("用户名")
        username_label.setObjectName("label")
        username = QLineEdit()
        username.setPlaceholderText("输入您的用户名")
        username.setObjectName("input")

        password_label = QLabel("密码")
        password_label.setObjectName("label")
        password = QLineEdit()
        password.setPlaceholderText("输入您的密码")
        password.setEchoMode(QLineEdit.EchoMode.Password)
        password.setObjectName("input")

        forgot = QLabel('<a href="#" style="color: #236d69; text-decoration: none;">忘记密码？</a>')
        forgot.setObjectName("forgot")
        forgot.setOpenExternalLinks(False)

        self.login_button = QPushButton("登录")
        self.login_button.setObjectName("primaryButton")
        self.login_button.setProperty("buttonRole", "primaryAccess")
        self.login_button.clicked.connect(self.login_requested.emit)

        options_label = QLabel("企业用户")
        options_label.setObjectName("optionLabel")
        sso = QPushButton("使用 SSO 登录")
        sso.setObjectName("secondaryButton")
        sso.setProperty("buttonRole", "reservedAccess")
        sso.setEnabled(False)

        layout.addWidget(title)
        layout.addSpacing(12)
        layout.addWidget(subtitle)
        layout.addSpacing(48)
        layout.addWidget(username_label)
        layout.addWidget(username)
        layout.addSpacing(24)
        layout.addWidget(password_label)
        layout.addWidget(password)
        layout.addSpacing(10)
        layout.addWidget(forgot, 0, Qt.AlignmentFlag.AlignRight)
        layout.addSpacing(16)
        layout.addWidget(self.login_button)
        layout.addSpacing(32)
        layout.addWidget(options_label)
        layout.addWidget(sso)

        return frame

    def _on_theme_changed(self, index: int) -> None:
        theme = ["Theme A (Dark)", "Theme B (Light)", "Theme C (Studio)"][index]
        QApplication.instance().setProperty("theme", theme)
        # Trigger full app style refresh
        QApplication.instance().style().polish(QApplication.instance())

if __name__ == "__main__":
    app = QApplication([])
    QFontDatabase.addApplicationFont("C:/Windows/Fonts/msyh.ttc")
    window = LoginStudio()
    window.show()
    app.exec()
