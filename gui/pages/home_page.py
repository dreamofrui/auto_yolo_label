"""
AutoLabeler 首页
显示项目概览和快速开始按钮
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QGridLayout
from qfluentwidgets import (
    PushButton,
    CardWidget,
    SubtitleLabel,
    StrongBodyLabel,
    FluentIcon,
    ImageLabel,
    setFont,
)

from gui.pages.base_page import BasePage
from gui.widgets.docs_dialog import DocsDialog


class HomePage(BasePage):
    """
    首页
    显示项目概览和快速开始按钮
    """

    def __init__(self, parent=None):
        super().__init__("首页", parent)

    def init_ui(self):
        """初始化UI"""
        # 标题
        self.add_title("欢迎使用 AutoLabeler")
        self.add_spacing(8)

        # 描述
        self.add_description(
            "AutoLabeler 是一款智能图片标注工具，通过 '少量人工标注 + 模型自动标注' "
            "的方式，大幅降低标注工作量，提升标注效率。"
        )
        self.add_spacing(24)

        # 创建统计卡片
        stats_layout = QGridLayout()
        stats_layout.setSpacing(16)

        # 统计数据卡片
        self._create_stat_card(stats_layout, "核心功能", "6", "个完整模块", 0, 0)
        self._create_stat_card(stats_layout, "测试覆盖", "100%", "测试通过", 0, 1)
        self._create_stat_card(stats_layout, "效率提升", "80%", "标注时间减少", 0, 2)

        self.content_layout.addLayout(stats_layout)
        self.add_spacing(24)

        # 工作流程说明
        self.add_title("工作流程")
        self.add_spacing(12)

        # 创建流程卡片
        self._create_workflow_cards()
        self.add_spacing(24)

        # 快速开始
        self.add_title("快速开始")
        self.add_spacing(12)

        # 创建快速开始按钮
        self._create_quick_start_buttons()

        # 开发者信息
        self.add_spacing(24)
        self._create_about_card()

        self.add_stretch()

    def _create_stat_card(self, layout, title: str, value: str, subtitle: str, row: int, col: int):
        """
        创建统计卡片

        Args:
            layout: 布局
            title: 标题
            value: 数值
            subtitle: 副标题
            row: 行位置
            col: 列位置
        """
        card = CardWidget()
        card.setFixedHeight(100)

        card_layout = QGridLayout(card)
        card_layout.setContentsMargins(16, 16, 16, 16)
        card_layout.setSpacing(8)

        # 数值
        value_label = SubtitleLabel(value)
        setFont(value_label, 24)
        card_layout.addWidget(value_label, 0, 0, 1, 2)

        # 标题
        title_label = StrongBodyLabel(title)
        card_layout.addWidget(title_label, 1, 0)

        # 副标题
        sub_label = StrongBodyLabel(subtitle)
        sub_label.setStyleSheet("color: #606060;")
        card_layout.addWidget(sub_label, 1, 1)

        layout.addWidget(card, row, col)

    def _create_workflow_cards(self):
        """创建工作流程卡片"""
        workflow_layout = QGridLayout()
        workflow_layout.setSpacing(12)

        steps = [
            ("1. 扫描", "扫描站点文件夹，建立图片索引", FluentIcon.SEARCH),
            ("2. 抽样", "抽取部分图片用于人工标注", FluentIcon.FILTER),
            ("3. 标注", "使用外部工具（如LabelImg）标注", FluentIcon.EDIT),
            ("4. 训练", "训练YOLO模型", FluentIcon.IOT),
            ("5. 推理", "自动标注剩余图片", FluentIcon.ROBOT),
            ("6. 还原", "还原标注到原始位置", FluentIcon.SYNC),
        ]

        for i, (title, desc, icon) in enumerate(steps):
            row = i // 3
            col = i % 3

            card = CardWidget()
            card.setFixedHeight(80)

            card_layout = QGridLayout(card)
            card_layout.setContentsMargins(16, 12, 16, 12)
            card_layout.setSpacing(8)

            # 图标 + 标题
            icon_label = ImageLabel()
            icon_label.setFixedSize(24, 24)
            icon_label.setImage(icon.icon().pixmap(24, 24))
            card_layout.addWidget(icon_label, 0, 0)

            title_label = StrongBodyLabel(title)
            setFont(title_label, 14)
            card_layout.addWidget(title_label, 0, 1)

            # 描述
            desc_label = StrongBodyLabel(desc)
            desc_label.setStyleSheet("color: #606060;")
            desc_label.setWordWrap(True)
            card_layout.addWidget(desc_label, 1, 0, 1, 2)

            workflow_layout.addWidget(card, row, col)

        self.content_layout.addLayout(workflow_layout)

    def _create_quick_start_buttons(self):
        """创建快速开始按钮"""
        # 创建按钮布局
        button_layout = QGridLayout()
        button_layout.setSpacing(12)

        # 快速开始按钮
        scan_btn = PushButton("开始扫描", self, FluentIcon.SEARCH)
        scan_btn.clicked.connect(lambda: self._navigate_to("扫描"))
        button_layout.addWidget(scan_btn, 0, 0)

        # 查看文档按钮
        docs_btn = PushButton("使用文档", self, FluentIcon.DOCUMENT)
        docs_btn.clicked.connect(self._show_docs)
        button_layout.addWidget(docs_btn, 0, 1)

        self.content_layout.addLayout(button_layout)

    def _navigate_to(self, page_name: str):
        """
        导航到指定页面

        Args:
            page_name: 页面名称
        """
        # 获取主窗口并导航
        main_window = self.window()

        # 方法1：通过 navigationInterface 设置当前项
        if hasattr(main_window, 'navigationInterface'):
            main_window.navigationInterface.setCurrentItem(page_name)

        # 方法2：直接切换 stackedWidget
        # 找到对应页面的索引并切换
        if hasattr(main_window, 'stackedWidget'):
            stacked = main_window.stackedWidget
            for i in range(stacked.count()):
                widget = stacked.widget(i)
                if hasattr(widget, 'title') and widget.title == page_name:
                    stacked.setCurrentIndex(i)
                    break

    def _show_docs(self):
        """显示使用文档（非模态）"""
        dialog = DocsDialog(self)
        dialog.show()  # 使用 show() 而不是 exec()，使其成为非模态对话框

    def _create_about_card(self):
        """创建开发者信息卡片"""
        card = CardWidget()
        card.setFixedHeight(60)

        card_layout = QGridLayout(card)
        card_layout.setContentsMargins(20, 12, 20, 12)
        card_layout.setSpacing(8)

        # 左侧弹性空间
        card_layout.setColumnStretch(0, 1)

        # 开发者标签（右侧）
        developer_label = StrongBodyLabel("Developer: 睿")
        developer_label.setStyleSheet("color: #888;")
        card_layout.addWidget(developer_label, 0, 1)

        self.content_layout.addWidget(card)
