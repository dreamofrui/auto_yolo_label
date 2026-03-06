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
