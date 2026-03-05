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
