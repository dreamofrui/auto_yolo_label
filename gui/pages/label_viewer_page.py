"""
AutoLabeler Label Viewer Page
Browse inference results and launch LabelImg
"""

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
from utils.labelimg_launcher import LabelImgLauncher, LabelImgLaunchError


class LabelViewerPage(BasePage):
    """
    Label Viewer Page
    Browse inference results and launch LabelImg to view annotations
    """

    def __init__(self, parent=None):
        # Initialize attributes before super().__init__
        self.site_input = None
        self.site_browse_btn = None
        self.inference_list = None
        self.product_tree = None
        self.open_labelimg_btn = None
        self.open_folder_btn = None
        self.status_label = None

        # State
        self.current_site = None
        self.current_inference = None
        self.current_code = None
        self.current_product = None
        self.labelimg_available = False

        super().__init__("LabelViewer", parent)

    def init_ui(self):
        """Initialize UI"""
        self.add_title("Label Inspector")
        self.add_description(
            "Browse inference results and launch LabelImg to view annotations. "
            "Select a site folder, choose an inference run, then select a product to view."
        )
        self.add_spacing(20)

        # Site selection
        self._create_site_selection()
        self.add_spacing(16)

        # Main content area
        self._create_main_content()
        self.add_spacing(16)

        # Action buttons
        self._create_action_buttons()

        self.add_stretch()

        # Check LabelImg availability
        self._check_labelimg()

    def _create_site_selection(self):
        """Create site selection area"""
        card = CardWidget()
        layout = QGridLayout(card)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        label = StrongBodyLabel("Site Folder:")
        layout.addWidget(label, 0, 0)

        self.site_input = LineEdit()
        self.site_input.setPlaceholderText("Select site folder...")
        self.site_input.setReadOnly(True)
        layout.addWidget(self.site_input, 0, 1)

        self.site_browse_btn = PushButton("Browse...", self, FluentIcon.FOLDER)
        self.site_browse_btn.clicked.connect(self._browse_site)
        layout.addWidget(self.site_browse_btn, 0, 2)

        self.content_layout.addWidget(card)

    def _create_main_content(self):
        """Create main content area with inference list and product tree"""
        card = CardWidget()
        layout = QGridLayout(card)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # Inference list (left side)
        inference_label = StrongBodyLabel("Inference Records:")
        layout.addWidget(inference_label, 0, 0)

        self.inference_list = ListWidget()
        self.inference_list.setMaximumWidth(250)
        self.inference_list.itemClicked.connect(self._on_inference_selected)
        layout.addWidget(self.inference_list, 1, 0)

        # Product tree (right side)
        tree_label = StrongBodyLabel("Product Tree:")
        layout.addWidget(tree_label, 0, 1)

        self.product_tree = QTreeWidget()
        self.product_tree.setHeaderLabel("Products")
        self.product_tree.itemClicked.connect(self._on_product_selected)
        layout.addWidget(self.product_tree, 1, 1)

        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(1, 2)

        self.content_layout.addWidget(card)

    def _create_action_buttons(self):
        """Create action button area"""
        card = CardWidget()
        layout = QGridLayout(card)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        self.open_labelimg_btn = PushButton("Open with LabelImg", self, FluentIcon.VIEW)
        self.open_labelimg_btn.setEnabled(False)
        self.open_labelimg_btn.clicked.connect(self._open_with_labelimg)
        layout.addWidget(self.open_labelimg_btn, 0, 0)

        self.open_folder_btn = PushButton("Open in File Manager", self, FluentIcon.FOLDER_OPEN)
        self.open_folder_btn.setEnabled(False)
        self.open_folder_btn.clicked.connect(self._open_in_file_manager)
        layout.addWidget(self.open_folder_btn, 0, 1)

        self.status_label = BodyLabel("Select a site folder to begin")
        layout.addWidget(self.status_label, 1, 0, 1, 3)

        self.content_layout.addWidget(card)

    def _check_labelimg(self):
        """Check if LabelImg is available"""
        self.labelimg_available, msg = LabelImgLauncher.check_labelimg_available()
        if not self.labelimg_available:
            self.status_label.setText(f"Warning: {msg}")

    def _browse_site(self):
        """Browse and select site folder"""
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Site Folder",
            "",
            QFileDialog.ShowDirsOnly
        )

        if folder:
            self.current_site = Path(folder)
            self.site_input.setText(folder)
            self._load_inference_list()

    def _load_inference_list(self):
        """Load inference records for current site"""
        self.inference_list.clear()
        self.product_tree.clear()
        self._reset_selection()

        if not self.current_site:
            return

        # Look for inference results directory
        inference_dir = self.current_site / ".autolabeler" / "inference_results"

        if not inference_dir.exists():
            self.status_label.setText("No inference results found")
            return

        # List inference runs (sorted by name, which includes timestamp)
        run_dirs = sorted(
            inference_dir.glob("run_*"),
            key=lambda x: x.name,
            reverse=True
        )

        for run_dir in run_dirs:
            config_path = run_dir / "inference_config.json"
            if config_path.exists():
                # Use run directory name as display text
                self.inference_list.addItem(run_dir.name)

        if self.inference_list.count() == 0:
            self.status_label.setText("No valid inference runs found")
        else:
            self.status_label.setText(f"Found {self.inference_list.count()} inference run(s)")

    def _on_inference_selected(self, item):
        """Handle inference record selection"""
        self.current_inference = item.text()
        self._load_product_tree()

    def _load_product_tree(self):
        """Load product tree for selected inference run"""
        self.product_tree.clear()
        self._reset_selection()

        if not self.current_site or not self.current_inference:
            return

        run_dir = self.current_site / ".autolabeler" / "inference_results" / self.current_inference

        if not run_dir.exists():
            return

        # Scan Code/Product structure
        for code_dir in sorted(run_dir.iterdir()):
            if not code_dir.is_dir():
                continue

            code_item = QTreeWidgetItem(self.product_tree, [code_dir.name])

            for product_dir in sorted(code_dir.iterdir()):
                if not product_dir.is_dir():
                    continue

                # Count txt files (excluding classes.txt)
                txt_count = len([f for f in product_dir.glob("*.txt") if f.name != "classes.txt"])
                product_item = QTreeWidgetItem(code_item, [f"{product_dir.name} ({txt_count})"])
                product_item.setData(0, 1, product_dir.name)  # Store actual name

            code_item.setExpanded(True)

    def _on_product_selected(self, item, column):
        """Handle product selection"""
        # Check if this is a product item (has parent)
        parent = item.parent()
        if parent is None:
            # This is a code item, not a product
            self._reset_selection()
            return

        self.current_code = parent.text(0)
        # Extract product name from "ProductName (count)" format
        display_text = item.text(0)
        self.current_product = display_text.split(" (")[0]

        self.open_labelimg_btn.setEnabled(self.labelimg_available)
        self.open_folder_btn.setEnabled(True)
        self.status_label.setText(f"Selected: {self.current_code} / {self.current_product}")

    def _reset_selection(self):
        """Reset code/product selection"""
        self.current_code = None
        self.current_product = None
        self.open_labelimg_btn.setEnabled(False)
        self.open_folder_btn.setEnabled(False)

    def _open_with_labelimg(self):
        """Open selected product in LabelImg"""
        if not all([self.current_site, self.current_inference, self.current_code, self.current_product]):
            return

        try:
            LabelImgLauncher.launch(
                site_dir=self.current_site,
                inference_run=self.current_inference,
                code=self.current_code,
                product=self.current_product
            )
            self.window().show_info("Success", "LabelImg launched successfully")
        except LabelImgLaunchError as e:
            self.window().show_error("Launch Failed", str(e))

    def _open_in_file_manager(self):
        """Open selected product folder in file manager"""
        if not all([self.current_site, self.current_inference, self.current_code, self.current_product]):
            return

        label_dir = (
            self.current_site / ".autolabeler" / "inference_results" /
            self.current_inference / self.current_code / self.current_product
        )

        if label_dir.exists():
            import subprocess
            import sys

            if sys.platform == "win32":
                subprocess.run(["explorer", str(label_dir)])
            elif sys.platform == "darwin":
                subprocess.run(["open", str(label_dir)])
            else:
                subprocess.run(["xdg-open", str(label_dir)])
