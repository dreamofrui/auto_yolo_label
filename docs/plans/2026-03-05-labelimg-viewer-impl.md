# LabelImg Viewer Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a "Label Viewer" page that allows users to browse inference results and launch LabelImg to view annotations.

**Architecture:** Create a new page `LabelViewerPage` with a tree-based UI for selecting inference runs and products. A utility class `LabelImgLauncher` handles copying `classes.txt` and launching LabelImg as a subprocess.

**Tech Stack:** Python 3.8+, PySide6, QFluentWidgets, subprocess

---

## Task 1: Create LabelImgLauncher Utility Class

**Files:**
- Create: `utils/labelimg_launcher.py`
- Create: `tests/test_labelimg_launcher.py`

### Step 1: Write the failing test for LabelImg availability check

```python
# tests/test_labelimg_launcher.py
"""Tests for LabelImgLauncher utility class"""

import subprocess
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

from utils.labelimg_launcher import LabelImgLauncher, LabelImgLaunchError


class TestLabelImgLauncherCheck:
    """Test LabelImg availability check"""

    def test_check_available_when_installed(self):
        """Test check returns True when LabelImg is installed"""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            available, msg = LabelImgLauncher.check_labelimg_available()
            assert available is True
            assert msg == ""

    def test_check_unavailable_when_not_installed(self):
        """Test check returns False when LabelImg is not installed"""
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = FileNotFoundError()
            available, msg = LabelImgLauncher.check_labelimg_available()
            assert available is False
            assert "pip install labelImg" in msg
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_labelimg_launcher.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'utils.labelimg_launcher'"

### Step 3: Write LabelImgLauncher class with check method

```python
# utils/labelimg_launcher.py
"""LabelImg Launcher utility class"""

import subprocess
import shutil
import sys
from pathlib import Path
from typing import Tuple


class LabelImgLaunchError(Exception):
    """LabelImg launch failed"""
    pass


class LabelImgLauncher:
    """Launcher for LabelImg annotation tool"""

    @classmethod
    def check_labelimg_available(cls) -> Tuple[bool, str]:
        """
        Check if LabelImg is available

        Returns:
            Tuple of (is_available, error_message)
        """
        try:
            result = subprocess.run(
                [sys.executable, "-m", "labelImg", "--help"],
                capture_output=True,
                timeout=5
            )
            return True, ""
        except FileNotFoundError:
            return False, "LabelImg not installed. Run: pip install labelImg"
        except subprocess.TimeoutExpired:
            return False, "LabelImg check timed out"
        except Exception as e:
            return False, f"LabelImg check failed: {e}"
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_labelimg_launcher.py::TestLabelImgLauncherCheck -v`
Expected: PASS

**Step 5: Commit**

```bash
git add utils/labelimg_launcher.py tests/test_labelimg_launcher.py
git commit -m "feat(utils): add LabelImgLauncher with availability check"
```

---

## Task 2: Add Launch Method to LabelImgLauncher

**Files:**
- Modify: `utils/labelimg_launcher.py`
- Modify: `tests/test_labelimg_launcher.py`

### Step 1: Write failing tests for launch method

```python
# Add to tests/test_labelimg_launcher.py

class TestLabelImgLauncherLaunch:
    """Test LabelImg launch functionality"""

    def test_launch_copies_classes_txt(self, tmp_path):
        """Test that launch copies classes.txt to label directory"""
        # Setup
        site_dir = tmp_path / "site"
        site_dir.mkdir()

        # Create classes.txt in site root
        classes_file = site_dir / "classes.txt"
        classes_file.write_text("class1\nclass2\n")

        # Create inference result directory
        label_dir = site_dir / ".autolabeler" / "inference_results" / "run_001" / "CodeA" / "ProductA"
        label_dir.mkdir(parents=True)

        # Create a dummy txt file
        (label_dir / "image1.txt").write_text("0 0.5 0.5 0.1 0.1")

        # Create image directory
        image_dir = site_dir / "CodeA" / "ProductA"
        image_dir.mkdir(parents=True)
        (image_dir / "image1.jpg").write_text("fake image")

        with patch('subprocess.Popen') as mock_popen:
            mock_popen.return_value = MagicMock()
            result = LabelImgLauncher.launch(
                site_dir=site_dir,
                inference_run="run_001",
                code="CodeA",
                product="ProductA"
            )

        assert result is True
        assert (label_dir / "classes.txt").exists()
        assert (label_dir / "classes.txt").read_text() == "class1\nclass2\n"

    def test_launch_fails_without_classes_txt(self, tmp_path):
        """Test that launch fails when classes.txt doesn't exist"""
        site_dir = tmp_path / "site"
        site_dir.mkdir()

        # No classes.txt created

        with pytest.raises(LabelImgLaunchError) as exc_info:
            LabelImgLauncher.launch(
                site_dir=site_dir,
                inference_run="run_001",
                code="CodeA",
                product="ProductA"
            )

        assert "classes.txt" in str(exc_info.value)

    def test_launch_fails_with_empty_label_dir(self, tmp_path):
        """Test that launch fails when label directory is empty"""
        site_dir = tmp_path / "site"
        site_dir.mkdir()

        # Create classes.txt
        (site_dir / "classes.txt").write_text("class1\n")

        # Create empty label directory
        label_dir = site_dir / ".autolabeler" / "inference_results" / "run_001" / "CodeA" / "ProductA"
        label_dir.mkdir(parents=True)
        # No txt files

        with pytest.raises(LabelImgLaunchError) as exc_info:
            LabelImgLauncher.launch(
                site_dir=site_dir,
                inference_run="run_001",
                code="CodeA",
                product="ProductA"
            )

        assert "no annotation files" in str(exc_info.value).lower()
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_labelimg_launcher.py::TestLabelImgLauncherLaunch -v`
Expected: FAIL with "AttributeError: type object 'LabelImgLauncher' has no attribute 'launch'"

### Step 3: Implement launch method

```python
# Add to utils/labelimg_launcher.py

    @classmethod
    def launch(
        cls,
        site_dir: Path,
        inference_run: str,
        code: str,
        product: str
    ) -> bool:
        """
        Launch LabelImg for a specific inference result

        Args:
            site_dir: Site root directory
            inference_run: Inference run name (e.g., "run_20250305_143022")
            code: Code folder name
            product: Product folder name

        Returns:
            True if launch successful

        Raises:
            LabelImgLaunchError: If launch fails
        """
        site_dir = Path(site_dir)

        # Build paths
        label_dir = site_dir / ".autolabeler" / "inference_results" / inference_run / code / product
        image_dir = site_dir / code / product
        src_classes = site_dir / "classes.txt"
        dst_classes = label_dir / "classes.txt"

        # Validate classes.txt exists
        if not src_classes.exists():
            raise LabelImgLaunchError(
                "classes.txt not found in site directory. "
                "Please run Scan first to generate classes.txt"
            )

        # Validate label directory exists and has files
        if not label_dir.exists():
            raise LabelImgLaunchError(
                f"Label directory not found: {label_dir}"
            )

        txt_files = list(label_dir.glob("*.txt"))
        # Filter out classes.txt if it already exists
        annotation_files = [f for f in txt_files if f.name != "classes.txt"]
        if not annotation_files:
            raise LabelImgLaunchError(
                f"No annotation files found in {label_dir}"
            )

        # Copy classes.txt to label directory
        shutil.copy(src_classes, dst_classes)

        # Launch LabelImg
        # Command: python -m labelImg IMAGE_PATH [PRE-DEFINED CLASS FILE]
        cmd = [
            sys.executable,
            "-m",
            "labelImg",
            str(image_dir),
            str(dst_classes)
        ]

        try:
            # Use detached process to run independently
            subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.DETACHED_PROCESS if sys.platform == "win32" else 0,
                start_new_session=True
            )
            return True
        except Exception as e:
            raise LabelImgLaunchError(f"Failed to launch LabelImg: {e}")
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_labelimg_launcher.py -v`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add utils/labelimg_launcher.py tests/test_labelimg_launcher.py
git commit -m "feat(utils): add launch method to LabelImgLauncher"
```

---

## Task 3: Create LabelViewerPage UI Framework

**Files:**
- Create: `gui/pages/label_viewer_page.py`

### Step 1: Create page with basic UI structure

```python
# gui/pages/label_viewer_page.py
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
```

**Step 2: Commit**

```bash
git add gui/pages/label_viewer_page.py
git commit -m "feat(gui): add LabelViewerPage UI framework"
```

---

## Task 4: Register LabelViewerPage in Navigation

**Files:**
- Modify: `gui/main_window.py`

### Step 1: Add import and register page

Add to imports at line 27:
```python
from gui.pages.label_viewer_page import LabelViewerPage
```

Add after InferencePage registration (after line 113):
```python
        # Add label viewer page
        self._add_page(
            LabelViewerPage(self),
            FluentIcon.VIEW,
            "Label Inspector",
            NavigationItemPosition.TOP
        )
```

### Step 2: Verify application starts

Run: `python main.py`
Expected: Application starts, "Label Inspector" appears in navigation

### Step 3: Commit

```bash
git add gui/main_window.py
git commit -m "feat(gui): register LabelViewerPage in navigation"
```

---

## Task 5: Integration Testing

### Step 1: Manual test checklist

1. Start application: `python main.py`
2. Navigate to "Label Inspector" page
3. Select a site folder with inference results
4. Verify inference records appear in list
5. Click an inference record
6. Verify product tree populates
7. Select a product
8. Verify "Open with LabelImg" button enables
9. Click "Open with LabelImg"
10. Verify LabelImg opens with correct folder

### Step 2: Commit any fixes

```bash
git add -A
git commit -m "fix: resolve integration issues"
```

---

## Task 6: Update Documentation

**Files:**
- Modify: `CLAUDE.md`

### Step 1: Add feature to history

Add to Feature History section:
```markdown
### 2026-03-05
- Label Inspector page for viewing inference results
- LabelImg integration with auto-copy classes.txt
- Inference result browser with Code/Product tree structure
```

### Step 2: Commit

```bash
git add CLAUDE.md
git commit -m "docs: add Label Inspector feature to history"
```

---

## Summary

| Task | Description | Files |
|------|-------------|-------|
| 1 | Create LabelImgLauncher with check method | `utils/labelimg_launcher.py`, `tests/test_labelimg_launcher.py` |
| 2 | Add launch method to LabelImgLauncher | Same files |
| 3 | Create LabelViewerPage UI | `gui/pages/label_viewer_page.py` |
| 4 | Register page in navigation | `gui/main_window.py` |
| 5 | Integration testing | Manual |
| 6 | Update documentation | `CLAUDE.md` |

## Dependencies

```
Task 1 ──▶ Task 2
              │
              ▼
          Task 3 ──▶ Task 4 ──▶ Task 5 ──▶ Task 6
```
