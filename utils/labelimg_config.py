"""LabelImg configuration management"""

import json
import sys
import stat
import subprocess
from pathlib import Path
from typing import Optional, Tuple
from datetime import datetime


class LabelImgConfig:
    """Manage LabelImg external Python environment configuration"""

    # Configuration file paths
    PROJECT_CONFIG_PATH = "config/labelimg.json"
    GLOBAL_CONFIG_DIR = ".autolabeler"
    GLOBAL_CONFIG_FILE = "labelimg.json"

    # Default Python path for LabelImg environment
    DEFAULT_PYTHON_PATH = "D:/miniforge3/envs/labelimg/python.exe"

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
        Load configuration with priority: project > global > default

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

        # Try default path
        if Path(self.DEFAULT_PYTHON_PATH).exists():
            self._python_path = self.DEFAULT_PYTHON_PATH
            self._config_source = "default"
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
        # If already loaded from config, use it
        if self._python_path:
            # Quick check if path still exists
            if not Path(self._python_path).exists():
                return None, f"Configured Python path no longer exists: {self._python_path}"
            return self._python_path, ""

        # Try default path as fallback
        if Path(self.DEFAULT_PYTHON_PATH).exists():
            return self.DEFAULT_PYTHON_PATH, ""

        return None, "LabelImg environment not configured. Please click 'Configure LabelImg' button."
