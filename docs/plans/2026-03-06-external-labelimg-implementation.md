# 外部 LabelImg 环境集成实现计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 支持调用外部 Python 环境中的 LabelImg，避免与当前 yolo_new 环境的包冲突。

**Architecture:** 创建 `LabelImgConfig` 类管理配置（项目级 > 全局级优先级），修改 `LabelImgLauncher` 支持外部 Python 路径，更新 GUI 添加配置按钮和状态显示。

**Tech Stack:** Python 3.8+, PySide6, QFluentWidgets, subprocess, json

---

## Task 1: 创建 LabelImgConfig 配置管理类

**Files:**
- Create: `utils/labelimg_config.py`
- Create: `tests/test_labelimg_config.py`

### Step 1: 写失败的测试 - 配置加载

```python
# tests/test_labelimg_config.py
"""Tests for LabelImgConfig class"""

import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from utils.labelimg_config import LabelImgConfig


class TestLabelImgConfigLoad:
    """Test configuration loading"""

    def test_load_returns_false_when_no_config_exists(self, tmp_path, monkeypatch):
        """Test load returns False when no config files exist"""
        # Mock home directory to tmp_path
        monkeypatch.setattr(Path, 'home', lambda: tmp_path)

        config = LabelImgConfig()
        result = config.load()

        assert result is False
        assert config.python_path is None

    def test_load_from_project_config(self, tmp_path, monkeypatch):
        """Test loading from project config (config/labelimg.json)"""
        # Create project config
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        config_file = config_dir / "labelimg.json"
        config_file.write_text(json.dumps({
            "python_path": "D:/python.exe",
            "is_valid": True
        }))

        # Mock home directory
        monkeypatch.setattr(Path, 'home', lambda: tmp_path)

        # Change to tmp_path to simulate project directory
        with patch('pathlib.Path.cwd', return_value=tmp_path):
            config = LabelImgConfig()
            result = config.load()

        assert result is True
        assert config.python_path == "D:/python.exe"

    def test_load_from_global_config_when_project_missing(self, tmp_path, monkeypatch):
        """Test loading from global config (~/.autolabeler/labelimg.json)"""
        # Create global config
        global_config_dir = tmp_path / ".autolabeler"
        global_config_dir.mkdir()
        global_config_file = global_config_dir / "labelimg.json"
        global_config_file.write_text(json.dumps({
            "python_path": "E:/python.exe",
            "is_valid": True
        }))

        # Mock home directory
        monkeypatch.setattr(Path, 'home', lambda: tmp_path)

        # No project config exists
        with patch('pathlib.Path.cwd', return_value=tmp_path / "empty"):
            config = LabelImgConfig()
            result = config.load()

        assert result is True
        assert config.python_path == "E:/python.exe"

    def test_project_config_takes_priority(self, tmp_path, monkeypatch):
        """Test project config takes priority over global config"""
        # Create both configs
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        project_config = config_dir / "labelimg.json"
        project_config.write_text(json.dumps({
            "python_path": "D:/project/python.exe",
            "is_valid": True
        }))

        global_config_dir = tmp_path / ".autolabeler"
        global_config_dir.mkdir()
        global_config = global_config_dir / "labelimg.json"
        global_config.write_text(json.dumps({
            "python_path": "D:/global/python.exe",
            "is_valid": True
        }))

        monkeypatch.setattr(Path, 'home', lambda: tmp_path)

        with patch('pathlib.Path.cwd', return_value=tmp_path):
            config = LabelImgConfig()
            config.load()

        assert config.python_path == "D:/project/python.exe"
```

**Step 2: 运行测试确认失败**

Run: `pytest tests/test_labelimg_config.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'utils.labelimg_config'"

### Step 3: 实现 LabelImgConfig 基础类

```python
# utils/labelimg_config.py
"""LabelImg configuration management"""

import json
from pathlib import Path
from typing import Optional, Tuple
from datetime import datetime


class LabelImgConfig:
    """Manage LabelImg external Python environment configuration"""

    # Configuration file paths
    PROJECT_CONFIG_PATH = "config/labelimg.json"
    GLOBAL_CONFIG_DIR = ".autolabeler"
    GLOBAL_CONFIG_FILE = "labelimg.json"

    def __init__(self):
        self._python_path: Optional[str] = None
        self._is_valid: bool = False
        self._last_check: Optional[str] = None
        self._config_source: Optional[str] = None  # Track which config was loaded

    @property
    def python_path(self) -> Optional[str]:
        """Get configured Python path"""
        return self._python_path

    @property
    def is_valid(self) -> bool:
        """Check if configuration is valid"""
        return self._is_valid

    @property
    def config_source(self) -> Optional[str]:
        """Get the source of current configuration"""
        return self._config_source

    def load(self) -> bool:
        """
        Load configuration with priority: project > global

        Returns:
            bool: True if configuration was found and loaded
        """
        # Try project config first
        project_config = Path.cwd() / self.PROJECT_CONFIG_PATH
        if project_config.exists():
            if self._load_from_file(project_config):
                self._config_source = "project"
                return True

        # Try global config
        global_config = Path.home() / self.GLOBAL_CONFIG_DIR / self.GLOBAL_CONFIG_FILE
        if global_config.exists():
            if self._load_from_file(global_config):
                self._config_source = "global"
                return True

        return False

    def _load_from_file(self, file_path: Path) -> bool:
        """Load configuration from a specific file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            self._python_path = data.get('python_path')
            self._is_valid = data.get('is_valid', False)
            self._last_check = data.get('last_check')
            return self._python_path is not None
        except (json.JSONDecodeError, IOError):
            return False
```

**Step 4: 运行测试确认通过**

Run: `pytest tests/test_labelimg_config.py::TestLabelImgConfigLoad -v`
Expected: All tests PASS

**Step 5: 提交**

```bash
git add utils/labelimg_config.py tests/test_labelimg_config.py
git commit -m "feat(utils): add LabelImgConfig with load functionality"
```

---

## Task 2: 实现 LabelImgConfig 保存和验证

**Files:**
- Modify: `utils/labelimg_config.py`
- Modify: `tests/test_labelimg_config.py`

### Step 1: 写失败的测试 - 保存功能

```python
# Add to tests/test_labelimg_config.py

class TestLabelImgConfigSave:
    """Test configuration saving"""

    def test_save_creates_global_config_dir(self, tmp_path, monkeypatch):
        """Test save creates .autolabeler directory if not exists"""
        monkeypatch.setattr(Path, 'home', lambda: tmp_path)

        config = LabelImgConfig()
        result, msg = config.save("D:/python.exe")

        assert result is True
        assert (tmp_path / ".autolabeler").exists()
        assert (tmp_path / ".autolabeler" / "labelimg.json").exists()

    def test_save_writes_valid_json(self, tmp_path, monkeypatch):
        """Test save writes valid JSON with correct fields"""
        monkeypatch.setattr(Path, 'home', lambda: tmp_path)

        config = LabelImgConfig()
        config.save("D:/python.exe")

        config_file = tmp_path / ".autolabeler" / "labelimg.json"
        with open(config_file, 'r') as f:
            data = json.load(f)

        assert data['python_path'] == "D:/python.exe"
        assert 'last_check' in data
        assert 'is_valid' in data
```

### Step 2: 写失败的测试 - Python 验证

```python
# Add to tests/test_labelimg_config.py

class TestLabelImgConfigValidate:
    """Test Python path validation"""

    def test_validate_returns_false_for_nonexistent_path(self, tmp_path):
        """Test validation fails for nonexistent Python path"""
        config = LabelImgConfig()
        fake_path = str(tmp_path / "nonexistent" / "python.exe")

        is_valid, msg = config.validate_python(fake_path)

        assert is_valid is False
        assert "not found" in msg.lower() or "does not exist" in msg.lower()

    def test_validate_returns_false_for_non_executable(self, tmp_path):
        """Test validation fails for non-executable file"""
        fake_python = tmp_path / "python.txt"
        fake_python.write_text("not an executable")

        config = LabelImgConfig()
        is_valid, msg = config.validate_python(str(fake_python))

        assert is_valid is False

    def test_validate_python_calls_labelimg_check(self, tmp_path):
        """Test validate_python checks if labelImg is installed"""
        fake_python = tmp_path / "python.exe"
        fake_python.write_text("fake")

        config = LabelImgConfig()

        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            is_valid, msg = config.validate_python(str(fake_python))

            # Should call python -m labelImg --help
            call_args = mock_run.call_args[0][0]
            assert "labelImg" in call_args
```

**Step 3: 运行测试确认失败**

Run: `pytest tests/test_labelimg_config.py::TestLabelImgConfigSave tests/test_labelimg_config.py::TestLabelImgConfigValidate -v`
Expected: FAIL with "AttributeError: 'LabelImgConfig' object has no attribute 'save'"

### Step 4: 实现保存和验证方法

```python
# Add to utils/labelimg_config.py

import subprocess
import stat


class LabelImgConfig:
    # ... existing code ...

    def save(self, python_path: str) -> Tuple[bool, str]:
        """
        Save configuration to global config directory

        Args:
            python_path: Path to Python interpreter

        Returns:
            Tuple[bool, str]: (success, error_message)
        """
        try:
            # Ensure global config directory exists
            global_config_dir = Path.home() / self.GLOBAL_CONFIG_DIR
            global_config_dir.mkdir(parents=True, exist_ok=True)

            config_file = global_config_dir / self.GLOBAL_CONFIG_FILE

            data = {
                "python_path": python_path,
                "last_check": datetime.now().isoformat(),
                "is_valid": True
            }

            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)

            # Update current instance
            self._python_path = python_path
            self._is_valid = True
            self._last_check = data["last_check"]
            self._config_source = "global"

            return True, ""
        except IOError as e:
            return False, f"Failed to save configuration: {e}"

    def validate_python(self, python_path: str) -> Tuple[bool, str]:
        """
        Validate Python path and check if labelImg is installed

        Args:
            python_path: Path to Python interpreter

        Returns:
            Tuple[bool, str]: (is_valid, error_message)
        """
        path = Path(python_path)

        # Check if path exists
        if not path.exists():
            return False, f"Python path does not exist: {python_path}"

        # Check if it's a file
        if not path.is_file():
            return False, f"Python path is not a file: {python_path}"

        # Check if it's executable (rough check based on extension or permissions)
        if sys.platform == "win32":
            if not python_path.lower().endswith('.exe'):
                return False, f"Not a valid Windows executable: {python_path}"
        else:
            if not (path.stat().st_mode & stat.S_IXUSR):
                return False, f"File is not executable: {python_path}"

        # Check if labelImg is installed
        try:
            result = subprocess.run(
                [python_path, "-m", "labelImg", "--help"],
                capture_output=True,
                timeout=10
            )
            if result.returncode != 0:
                return False, f"labelImg not installed in this environment. Run: {python_path} -m pip install labelImg"
        except FileNotFoundError:
            return False, f"Cannot execute Python: {python_path}"
        except subprocess.TimeoutExpired:
            return False, "labelImg check timed out"
        except Exception as e:
            return False, f"Validation failed: {e}"

        return True, ""

    def get_effective_python(self) -> Tuple[Optional[str], str]:
        """
        Get effective Python path with validation

        Returns:
            Tuple[Optional[str], str]: (python_path or None, error_message)
        """
        if not self._python_path:
            return None, "LabelImg environment not configured. Please click 'Configure LabelImg' button."

        # Quick check if path still exists
        if not Path(self._python_path).exists():
            return None, f"Configured Python path no longer exists: {self._python_path}"

        return self._python_path, ""
```

**Step 5: 添加缺少的导入**

```python
# Add to imports in utils/labelimg_config.py
import sys
```

**Step 6: 运行测试确认通过**

Run: `pytest tests/test_labelimg_config.py -v`
Expected: All tests PASS

**Step 7: 提交**

```bash
git add utils/labelimg_config.py tests/test_labelimg_config.py
git commit -m "feat(utils): add save and validate methods to LabelImgConfig"
```

---

## Task 3: 修改 LabelImgLauncher 支持外部 Python

**Files:**
- Modify: `utils/labelimg_launcher.py`
- Modify: `tests/test_labelimg_launcher.py`

### Step 1: 写失败的测试 - 外部 Python 检查

```python
# Add to tests/test_labelimg_launcher.py

class TestLabelImgLauncherExternalPython:
    """Test LabelImgLauncher with external Python"""

    def test_check_with_external_python(self):
        """Test check_labelimg_available with external Python path"""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            available, msg = LabelImgLauncher.check_labelimg_available("D:/external/python.exe")

            assert available is True
            # Verify it called with the external python
            call_args = mock_run.call_args[0][0]
            assert "D:/external/python.exe" in call_args

    def test_check_fails_with_invalid_python(self):
        """Test check fails when Python path is invalid"""
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = FileNotFoundError()

            available, msg = LabelImgLauncher.check_labelimg_available("D:/invalid/python.exe")

            assert available is False
```

### Step 2: 写失败的测试 - 外部 Python 启动

```python
# Add to tests/test_labelimg_launcher.py

class TestLabelImgLauncherExternalLaunch:
    """Test LabelImgLauncher launch with external Python"""

    def test_launch_uses_external_python(self, tmp_path):
        """Test launch uses provided Python path instead of sys.executable"""
        # Setup
        site_dir = tmp_path / "site"
        site_dir.mkdir()
        (site_dir / ".autolabeler" / "classes.txt").parent.mkdir(parents=True)
        (site_dir / ".autolabeler" / "classes.txt").write_text("class1\n")

        label_dir = site_dir / ".autolabeler" / "inference_results" / "run_001" / "CodeA" / "ProductA"
        label_dir.mkdir(parents=True)
        (label_dir / "image1.txt").write_text("0 0.5 0.5 0.1 0.1")

        image_dir = site_dir / "CodeA" / "ProductA"
        image_dir.mkdir(parents=True)
        (image_dir / "image1.jpg").write_text("fake")

        external_python = "D:/external/python.exe"

        with patch('subprocess.Popen') as mock_popen:
            mock_popen.return_value = MagicMock()

            LabelImgLauncher.launch(
                python_path=external_python,
                site_dir=site_dir,
                inference_run="run_001",
                code="CodeA",
                product="ProductA"
            )

            # Verify it used external Python
            call_args = mock_popen.call_args[0][0]
            assert external_python in call_args
            assert sys.executable not in call_args
```

**Step 3: 运行测试确认失败**

Run: `pytest tests/test_labelimg_launcher.py::TestLabelImgLauncherExternalPython tests/test_labelimg_launcher.py::TestLabelImgLauncherExternalLaunch -v`
Expected: FAIL - check_labelimg_available doesn't accept python_path argument

### Step 4: 修改 LabelImgLauncher 类

```python
# Modify utils/labelimg_launcher.py

class LabelImgLauncher:
    """Launcher for LabelImg annotation tool"""

    @classmethod
    def check_labelimg_available(cls, python_path: str = None) -> Tuple[bool, str]:
        """
        Check if LabelImg is available in specified Python environment

        Args:
            python_path: Path to Python interpreter. If None, uses sys.executable

        Returns:
            Tuple of (is_available, error_message)
        """
        python = python_path or sys.executable

        try:
            result = subprocess.run(
                [python, "-m", "labelImg", "--help"],
                capture_output=True,
                timeout=5
            )
            # Check return code to verify LabelImg actually works
            if result.returncode == 0:
                return True, ""
            else:
                return False, f"LabelImg check failed with return code {result.returncode}. Please ensure LabelImg is properly installed: {python} -m pip install labelImg"
        except FileNotFoundError:
            return False, f"Cannot execute Python: {python}"
        except subprocess.TimeoutExpired:
            return False, "LabelImg check timed out"
        except Exception as e:
            return False, f"LabelImg check failed: {e}"

    @classmethod
    def launch(
        cls,
        python_path: str,
        site_dir: Path,
        inference_run: str,
        code: str,
        product: str
    ) -> bool:
        """
        Launch LabelImg for a specific inference result using external Python

        Args:
            python_path: Path to external Python interpreter
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
        src_classes = site_dir / ".autolabeler" / "classes.txt"
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

        # Launch LabelImg using external Python
        # Command: python -m labelImg IMAGE_PATH [PRE-DEFINED CLASS FILE]
        cmd = [
            python_path,  # Use external Python instead of sys.executable
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

**Step 5: 运行测试确认通过**

Run: `pytest tests/test_labelimg_launcher.py -v`
Expected: All tests PASS

**Step 6: 提交**

```bash
git add utils/labelimg_launcher.py tests/test_labelimg_launcher.py
git commit -m "feat(utils): add external Python support to LabelImgLauncher"
```

---

## Task 4: 更新 GUI 添加配置功能

**Files:**
- Modify: `gui/pages/label_viewer_page.py`

### Step 1: 修改 GUI - 添加配置按钮和状态

```python
# Modify gui/pages/label_viewer_page.py

# Add import at top
from utils.labelimg_config import LabelImgConfig

# Modify __init__ method
class LabelViewerPage(BasePage):
    def __init__(self, parent=None):
        # ... existing attributes ...
        self.config_btn = None  # New: configure button
        self.config = LabelImgConfig()  # New: config manager

        # ... rest of __init__ ...

# Modify _create_action_buttons method
    def _create_action_buttons(self):
        """Create action button area"""
        card = CardWidget()
        layout = QGridLayout(card)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        # Row 0: Action buttons
        self.config_btn = PushButton("Configure LabelImg", self, FluentIcon.SETTING)
        self.config_btn.clicked.connect(self._configure_labelimg)
        layout.addWidget(self.config_btn, 0, 0)

        self.open_labelimg_btn = PushButton("Open with LabelImg", self, FluentIcon.VIEW)
        self.open_labelimg_btn.setEnabled(False)
        self.open_labelimg_btn.clicked.connect(self._open_with_labelimg)
        layout.addWidget(self.open_labelimg_btn, 0, 1)

        self.open_folder_btn = PushButton("Open in File Manager", self, FluentIcon.FOLDER_OPEN)
        self.open_folder_btn.setEnabled(False)
        self.open_folder_btn.clicked.connect(self._open_in_file_manager)
        layout.addWidget(self.open_folder_btn, 0, 2)

        # Row 1: Status label
        self.status_label = BodyLabel("Select a site folder to begin")
        layout.addWidget(self.status_label, 1, 0, 1, 3)

        self.content_layout.addWidget(card)

# Replace _check_labelimg method
    def _check_labelimg(self):
        """Check if LabelImg is configured and available"""
        # Try to load existing config
        if self.config.load():
            python_path, error = self.config.get_effective_python()
            if python_path:
                # Verify labelImg is still available
                available, msg = LabelImgLauncher.check_labelimg_available(python_path)
                if available:
                    self.labelimg_available = True
                    self.status_label.setText(f"Configured: {python_path}")
                else:
                    self.labelimg_available = False
                    self.status_label.setText(f"Configuration invalid: {msg}")
            else:
                self.labelimg_available = False
                self.status_label.setText(f"Configuration error: {error}")
        else:
            self.labelimg_available = False
            self.status_label.setText("LabelImg not configured. Click 'Configure LabelImg' to set up.")

# Add new method _configure_labelimg
    def _configure_labelimg(self):
        """Open dialog to configure LabelImg Python path"""
        from PySide6.QtWidgets import QFileDialog

        # Open file dialog to select Python executable
        if sys.platform == "win32":
            filter_str = "Python Executable (python.exe);;All Files (*.*)"
        else:
            filter_str = "Python Executable (python python3);;All Files (*.*)"

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Python Executable with LabelImg Installed",
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
                self.status_label.setText(f"Configured: {file_path}")
                self.window().show_info("Success", f"LabelImg configured successfully.\nPython: {file_path}")
            else:
                self.window().show_error("Save Failed", save_error)
        else:
            self.window().show_error("Invalid Python", error_msg)

# Modify _open_with_labelimg method
    def _open_with_labelimg(self):
        """Open selected product in LabelImg"""
        if not all([self.current_site, self.current_inference, self.current_code, self.current_product]):
            return

        # Get Python path from config
        python_path, error = self.config.get_effective_python()
        if not python_path:
            self.window().show_error("Not Configured", error)
            self._check_labelimg()  # Refresh status
            return

        try:
            LabelImgLauncher.launch(
                python_path=python_path,
                site_dir=self.current_site,
                inference_run=self.current_inference,
                code=self.current_code,
                product=self.current_product
            )
            self.window().show_info("Success", "LabelImg launched successfully")
        except LabelImgLaunchError as e:
            self.window().show_error("Launch Failed", str(e))
```

**Step 2: 添加缺少的导入**

```python
# Add to imports in gui/pages/label_viewer_page.py
import sys
from utils.labelimg_config import LabelImgConfig
```

**Step 3: 手动测试**

Run: `python main.py`
Test:
1. Navigate to "Label Inspector" page
2. Click "Configure LabelImg" button
3. Select a Python executable with labelImg installed
4. Verify status shows "Configured: [path]"
5. Select site, inference, product
6. Click "Open with LabelImg"
7. Verify LabelImg launches correctly

**Step 4: 提交**

```bash
git add gui/pages/label_viewer_page.py
git commit -m "feat(gui): add LabelImg configuration dialog to LabelViewerPage"
```

---

## Task 5: 更新文档

**Files:**
- Modify: `CLAUDE.md`

### Step 1: 添加功能历史记录

Add to Feature History section:
```markdown
### 2026-03-06
- External LabelImg environment support (avoid package conflicts)
- LabelImgConfig class for configuration management (project > global priority)
- GUI configuration dialog for selecting external Python interpreter
```

### Step 2: 提交

```bash
git add CLAUDE.md
git commit -m "docs: add external LabelImg integration to feature history"
```

---

## Task 6: 集成测试

### Step 1: 完整测试流程

1. **启动应用**: `python main.py`
2. **导航到标签检查页面**
3. **测试未配置状态**:
   - 删除 `~/.autolabeler/labelimg.json`（如果存在）
   - 验证状态显示 "LabelImg not configured"
4. **测试配置功能**:
   - 点击 "Configure LabelImg"
   - 选择无效路径 → 验证错误提示
   - 选择有效 Python（带 labelImg）→ 验证成功保存
5. **测试启动功能**:
   - 选择站点、推理记录、产品
   - 点击 "Open with LabelImg"
   - 验证 LabelImg 正确打开

### Step 2: 修复发现的问题

```bash
git add -A
git commit -m "fix: resolve integration test issues"
```

---

## Summary

| Task | Description | Files |
|------|-------------|-------|
| 1 | 创建 LabelImgConfig 基础类（加载功能） | `utils/labelimg_config.py`, `tests/test_labelimg_config.py` |
| 2 | 实现 LabelImgConfig 保存和验证 | Same files |
| 3 | 修改 LabelImgLauncher 支持外部 Python | `utils/labelimg_launcher.py`, `tests/test_labelimg_launcher.py` |
| 4 | 更新 GUI 添加配置功能 | `gui/pages/label_viewer_page.py` |
| 5 | 更新文档 | `CLAUDE.md` |
| 6 | 集成测试 | Manual |

## Dependencies

```
Task 1 ──▶ Task 2
              │
              ▼
          Task 3 ──▶ Task 4 ──▶ Task 5 ──▶ Task 6
```
