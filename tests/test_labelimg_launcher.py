"""Tests for LabelImgLauncher utility class"""

import subprocess
import sys
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
            assert "Cannot execute Python" in msg

    def test_check_unavailable_when_returncode_nonzero(self):
        """Test check returns False when LabelImg command fails (returns non-zero)"""
        with patch('subprocess.run') as mock_run:
            # 模拟 labelImg 未安装但命令执行了的情况 (returncode=1)
            mock_run.return_value = MagicMock(returncode=1)
            available, msg = LabelImgLauncher.check_labelimg_available()
            assert available is False
            assert "LabelImg" in msg


class TestLabelImgLauncherLaunch:
    """Test LabelImg launch functionality"""

    def test_launch_copies_classes_txt(self, tmp_path):
        """Test that launch copies classes.txt to label directory"""
        # Setup
        site_dir = tmp_path / "site"
        site_dir.mkdir()

        # Create .autolabeler directory and classes.txt (as scanner does)
        autolabeler_dir = site_dir / ".autolabeler"
        autolabeler_dir.mkdir()
        classes_file = autolabeler_dir / "classes.txt"
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
                python_path=sys.executable,
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
                python_path=sys.executable,
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

        # Create .autolabeler directory and classes.txt (as scanner does)
        autolabeler_dir = site_dir / ".autolabeler"
        autolabeler_dir.mkdir()
        (autolabeler_dir / "classes.txt").write_text("class1\n")

        # Create empty label directory
        label_dir = site_dir / ".autolabeler" / "inference_results" / "run_001" / "CodeA" / "ProductA"
        label_dir.mkdir(parents=True)
        # No txt files

        with pytest.raises(LabelImgLaunchError) as exc_info:
            LabelImgLauncher.launch(
                python_path=sys.executable,
                site_dir=site_dir,
                inference_run="run_001",
                code="CodeA",
                product="ProductA"
            )

        assert "no annotation files" in str(exc_info.value).lower()


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


class TestLabelImgLauncherExeFallback:
    """Test that launcher falls back to labelImg.exe when python -m fails"""

    def test_launch_uses_labelimg_exe_when_available(self, tmp_path):
        """
        BUG FIX: When Scripts/labelImg.exe exists, launcher should use it directly
        instead of python -m labelImg.
        """
        # Setup site directory
        site_dir = tmp_path / "site"
        site_dir.mkdir()

        # Create .autolabeler directory and classes.txt
        autolabeler_dir = site_dir / ".autolabeler"
        autolabeler_dir.mkdir()
        classes_file = autolabeler_dir / "classes.txt"
        classes_file.write_text("class1\nclass2\n")

        # Create inference result directory
        label_dir = site_dir / ".autolabeler" / "inference_results" / "run_001" / "CodeA" / "ProductA"
        label_dir.mkdir(parents=True)
        (label_dir / "image1.txt").write_text("0 0.5 0.5 0.1 0.1")

        # Create image directory
        image_dir = site_dir / "CodeA" / "ProductA"
        image_dir.mkdir(parents=True)
        (image_dir / "image1.jpg").write_text("fake image")

        # Mock external Python path
        external_python = tmp_path / "env" / "python.exe"
        external_python.parent.mkdir(parents=True, exist_ok=True)
        external_python.touch()

        # Create mock Scripts/labelImg.exe
        labelimg_exe = external_python.parent / "Scripts" / "labelImg.exe"
        labelimg_exe.parent.mkdir(parents=True, exist_ok=True)
        labelimg_exe.touch()

        # Track actual command used
        actual_commands = []

        def mock_popen(cmd, *args, **kwargs):
            """Mock Popen to track which command was used"""
            actual_commands.append(cmd)
            return MagicMock()

        with patch('subprocess.Popen', side_effect=mock_popen):
            result = LabelImgLauncher.launch(
                python_path=str(external_python),
                site_dir=site_dir,
                inference_run="run_001",
                code="CodeA",
                product="ProductA"
            )

        assert result is True
        assert len(actual_commands) == 1

        # Should use labelImg.exe directly
        cmd = actual_commands[0]
        assert "labelImg.exe" in " ".join(cmd), \
            f"Expected command to use labelImg.exe, but got: {' '.join(cmd)}"

    def test_launch_uses_python_m_when_exe_not_exists(self, tmp_path):
        """
        Test that launcher uses python -m labelImg when Scripts/labelImg.exe doesn't exist.
        This ensures backward compatibility.
        """
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

        external_python = tmp_path / "env" / "python.exe"
        external_python.parent.mkdir(parents=True, exist_ok=True)
        external_python.touch()
        # Do NOT create Scripts/labelImg.exe

        actual_commands = []

        def mock_popen(cmd, *args, **kwargs):
            actual_commands.append(cmd)
            return MagicMock()

        with patch('subprocess.Popen', side_effect=mock_popen):
            LabelImgLauncher.launch(
                python_path=str(external_python),
                site_dir=site_dir,
                inference_run="run_001",
                code="CodeA",
                product="ProductA"
            )

        cmd = actual_commands[0]

        # Should fall back to python -m labelImg
        assert "-m" in cmd and "labelImg" in cmd, \
            f"Expected 'python -m labelImg', but got: {' '.join(cmd)}"
