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
