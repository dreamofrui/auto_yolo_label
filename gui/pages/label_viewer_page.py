"""
AutoLabeler 标签检查页面
浏览推理结果并启动 LabelImg 查看标注
"""

import sys
from pathlib import Path
from PySide6.QtWidgets import QGridLayout, QFileDialog, QTreeWidget, QTreeWidgetItem
from qfluentwidgets import (
    PushButton,
    CardWidget,
    LineEdit,
    StrongBodyLabel,
    SubtitleLabel,
    FluentIcon,
    BodyLabel,
    ListWidget,
    InfoBar,
)

from gui.pages.base_page import BasePage
from core.label_inspector import LabelInspector
from utils.labelimg_launcher import LabelImgLauncher, LabelImgLaunchError
from utils.labelimg_config import LabelImgConfig


class LabelViewerPage(BasePage):
    """
    标签检查页面
    浏览推理结果并启动 LabelImg 查看标注
    """

    def __init__(self, parent=None):
        # 在调用 super().__init__ 之前初始化属性
        self.site_input = None
        self.site_browse_btn = None
        self.inference_list = None
        self.product_tree = None
        self.config_btn = None  # New: configure button
        self.open_labelimg_btn = None
        self.open_folder_btn = None
        self.status_label = None

        # 状态
        self.current_site = None
        self.current_inference = None
        self.current_code = None
        self.current_product = None
        self.labelimg_available = False
        self.inspector = None  # 标签检查器实例
        self.config = LabelImgConfig()  # New: config manager

        super().__init__("标签检查", parent)

    def init_ui(self):
        """初始化UI"""
        self.add_title("标签检查")
        self.add_description(
            "浏览推理结果并启动 LabelImg 查看标注。"
            "选择站点文件夹，选择推理运行，然后选择产品查看。"
        )
        self.add_spacing(20)

        # 站点选择
        self._create_site_selection()
        self.add_spacing(16)

        # 主内容区域
        self._create_main_content()
        self.add_spacing(16)

        # 操作按钮
        self._create_action_buttons()

        self.add_stretch()

        # 检查 LabelImg 可用性
        self._check_labelimg()

    def _create_site_selection(self):
        """创建站点选择区域"""
        card = CardWidget()
        layout = QGridLayout(card)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        label = StrongBodyLabel("站点文件夹:")
        layout.addWidget(label, 0, 0)

        self.site_input = LineEdit()
        self.site_input.setPlaceholderText("选择站点文件夹...")
        self.site_input.setReadOnly(True)
        layout.addWidget(self.site_input, 0, 1)

        self.site_browse_btn = PushButton("浏览...", self, FluentIcon.FOLDER)
        self.site_browse_btn.clicked.connect(self._browse_site)
        layout.addWidget(self.site_browse_btn, 0, 2)

        self.content_layout.addWidget(card)

    def _create_main_content(self):
        """创建主内容区域，包含推理列表和产品树"""
        card = CardWidget()
        layout = QGridLayout(card)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # 推理列表（左侧）
        inference_label = StrongBodyLabel("推理记录:")
        layout.addWidget(inference_label, 0, 0)

        self.inference_list = ListWidget()
        self.inference_list.setMaximumWidth(250)
        self.inference_list.itemClicked.connect(self._on_inference_selected)
        layout.addWidget(self.inference_list, 1, 0)

        # 产品树（右侧）
        tree_label = StrongBodyLabel("产品树:")
        layout.addWidget(tree_label, 0, 1)

        self.product_tree = QTreeWidget()
        self.product_tree.setHeaderLabel("产品列表")
        self.product_tree.itemClicked.connect(self._on_product_selected)
        layout.addWidget(self.product_tree, 1, 1)

        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(1, 2)

        self.content_layout.addWidget(card)

    def _create_action_buttons(self):
        """创建操作按钮区域"""
        card = CardWidget()
        layout = QGridLayout(card)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        # Row 0: Action buttons
        self.config_btn = PushButton("配置 LabelImg", self, FluentIcon.SETTING)
        self.config_btn.clicked.connect(self._configure_labelimg)
        layout.addWidget(self.config_btn, 0, 0)

        self.open_labelimg_btn = PushButton("用 LabelImg 打开", self, FluentIcon.VIEW)
        self.open_labelimg_btn.setEnabled(False)
        self.open_labelimg_btn.clicked.connect(self._open_with_labelimg)
        layout.addWidget(self.open_labelimg_btn, 0, 1)

        self.open_folder_btn = PushButton("在文件管理器中打开", self, FluentIcon.FOLDER_ADD)
        self.open_folder_btn.setEnabled(False)
        self.open_folder_btn.clicked.connect(self._open_in_file_manager)
        layout.addWidget(self.open_folder_btn, 0, 2)

        # Row 1: Status label
        self.status_label = BodyLabel("选择站点文件夹开始")
        layout.addWidget(self.status_label, 1, 0, 1, 3)

        self.content_layout.addWidget(card)

    def _check_labelimg(self):
        """检查 LabelImg 是否配置并可用"""
        # Try to load existing config
        if self.config.load():
            python_path, error = self.config.get_effective_python()
            if python_path:
                # Verify labelImg is still available
                available, msg = LabelImgLauncher.check_labelimg_available(python_path)
                if available:
                    self.labelimg_available = True
                    self.status_label.setText(f"已配置: {python_path}")
                else:
                    self.labelimg_available = False
                    self.status_label.setText(f"配置无效: {msg}")
            else:
                self.labelimg_available = False
                self.status_label.setText(f"配置错误: {error}")
        else:
            self.labelimg_available = False
            self.status_label.setText("LabelImg 未配置。点击「配置 LabelImg」按钮进行设置。")

    def _configure_labelimg(self):
        """打开对话框配置 LabelImg Python 路径"""
        # Open file dialog to select Python executable
        if sys.platform == "win32":
            filter_str = "Python 可执行文件 (python.exe);;所有文件 (*.*)"
        else:
            filter_str = "Python 可执行文件 (python python3);;所有文件 (*.*)"

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择安装了 LabelImg 的 Python 解释器",
            "",
            filter_str
        )

        if not file_path:
            return

        # Validate the selected Python
        is_valid, error_msg = self.config.validate_python(file_path)

        if is_valid:
            # Save configuration
            success, save_error = self.config.save(file_path)
            if success:
                self.labelimg_available = True
                self.status_label.setText(f"已配置: {file_path}")
                self.window().show_info("成功", f"LabelImg 配置成功。\nPython: {file_path}")
            else:
                self.window().show_error("保存失败", save_error)
        else:
            self.window().show_error("无效的 Python", error_msg)

    def _browse_site(self):
        """浏览并选择站点文件夹"""
        folder = QFileDialog.getExistingDirectory(
            self,
            "选择站点文件夹",
            "",
            QFileDialog.ShowDirsOnly
        )

        if folder:
            self.current_site = Path(folder)
            self.site_input.setText(folder)
            # 创建标签检查器实例
            self.inspector = LabelInspector(self.current_site)
            self._load_inference_list()

    def _load_inference_list(self):
        """加载当前站点的推理记录"""
        self.inference_list.clear()
        self.product_tree.clear()
        self._reset_selection()

        if not self.inspector:
            return

        # 使用 core 层获取推理记录
        runs = self.inspector.get_inference_runs()

        if not runs:
            self.status_label.setText("未找到推理结果")
            return

        for run in runs:
            if run.config_exists:
                self.inference_list.addItem(run.name)

        if self.inference_list.count() == 0:
            self.status_label.setText("未找到有效的推理运行")
        else:
            self.status_label.setText(f"找到 {self.inference_list.count()} 个推理运行")

    def _on_inference_selected(self, item):
        """处理推理记录选择"""
        self.current_inference = item.text()
        self._load_product_tree()

    def _load_product_tree(self):
        """加载产品树"""
        self.product_tree.clear()
        self._reset_selection()

        if not self.inspector or not self.current_inference:
            return

        # 使用 core 层获取 Code/Product 树
        tree = self.inspector.get_code_product_tree(self.current_inference)

        for code, products in tree.items():
            code_item = QTreeWidgetItem(self.product_tree, [code])

            for product_info in products:
                display_text = f"{product_info.product} ({product_info.label_count})"
                product_item = QTreeWidgetItem(code_item, [display_text])
                product_item.setData(0, 1, product_info.product)  # 存储实际名称

            code_item.setExpanded(True)

    def _on_product_selected(self, item, column):
        """处理产品选择"""
        # 检查是否是产品项（有父节点）
        parent = item.parent()
        if parent is None:
            # 这是 Code 项，不是产品
            self._reset_selection()
            return

        self.current_code = parent.text(0)
        # 从 "ProductName (count)" 格式中提取产品名称
        display_text = item.text(0)
        self.current_product = display_text.split(" (")[0]

        self.open_labelimg_btn.setEnabled(self.labelimg_available)
        self.open_folder_btn.setEnabled(True)
        self.status_label.setText(f"已选择: {self.current_code} / {self.current_product}")

    def _reset_selection(self):
        """重置 Code/Product 选择"""
        self.current_code = None
        self.current_product = None
        self.open_labelimg_btn.setEnabled(False)
        self.open_folder_btn.setEnabled(False)

    def _open_with_labelimg(self):
        """用 LabelImg 打开选中的产品"""
        if not all([self.inspector, self.current_inference, self.current_code, self.current_product]):
            return

        # Get Python path from config
        python_path, error = self.config.get_effective_python()
        if not python_path:
            self.window().show_error("未配置", error)
            self._check_labelimg()  # Refresh status
            return

        # 验证选择
        valid, error_msg = self.inspector.validate_selection(
            self.current_inference, self.current_code, self.current_product
        )
        if not valid:
            self.window().show_error("验证失败", error_msg)
            return

        try:
            LabelImgLauncher.launch(
                python_path=python_path,
                site_dir=self.current_site,
                inference_run=self.current_inference,
                code=self.current_code,
                product=self.current_product
            )
            self.window().show_info("成功", "LabelImg 已成功启动")
        except LabelImgLaunchError as e:
            self.window().show_error("启动失败", str(e))

    def _open_in_file_manager(self):
        """在文件管理器中打开选中的产品文件夹"""
        if not all([self.inspector, self.current_inference, self.current_code, self.current_product]):
            return

        product_path = self.inspector.get_product_path(
            self.current_inference, self.current_code, self.current_product
        )

        if product_path and product_path.exists():
            import subprocess

            if sys.platform == "win32":
                subprocess.run(["explorer", str(product_path)])
            elif sys.platform == "darwin":
                subprocess.run(["open", str(product_path)])
            else:
                subprocess.run(["xdg-open", str(product_path)])
