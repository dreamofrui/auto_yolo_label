"""LabelImg Launcher utility class"""

import subprocess
import shutil
import sys
from pathlib import Path
from typing import Optional, Tuple, List


class LabelImgLaunchError(Exception):
    """LabelImg launch failed"""
    pass


class LabelImgLauncher:
    """Launcher for LabelImg annotation tool"""

    # Common conda/mamba executable paths
    CONDA_ROOT = Path("D:/miniforge3")
    MAMBA_PATHS = [
        CONDA_ROOT / "Library" / "bin" / "mamba.exe",
        CONDA_ROOT / "Scripts" / "mamba.exe",
    ]
    CONDA_PATHS = [
        CONDA_ROOT / "Scripts" / "conda.exe",
    ]

    @classmethod
    def _find_conda_executable(cls) -> Tuple[Optional[str], str]:
        """
        Find available conda or mamba executable

        Returns:
            Tuple of (executable_path, type) where type is 'mamba' or 'conda'
            Returns (None, '') if not found
        """
        # Try mamba first (faster)
        for mamba_path in cls.MAMBA_PATHS:
            if mamba_path.exists():
                return str(mamba_path), "mamba"

        # Try conda
        for conda_path in cls.CONDA_PATHS:
            if conda_path.exists():
                return str(conda_path), "conda"

        return None, ""

    @classmethod
    def _get_env_name_from_python_path(cls, python_path: str) -> Optional[str]:
        """
        Extract conda environment name from Python path

        Args:
            python_path: Path like "D:/miniforge3/envs/labelimg/python.exe"

        Returns:
            Environment name like "labelimg" or None if not a conda env
        """
        path = Path(python_path)
        # Check if this looks like a conda env path: .../envs/<env_name>/python.exe
        parts = path.parts
        try:
            envs_index = parts.index("envs")
            if envs_index + 1 < len(parts) - 1:  # -1 because last part is python.exe
                return parts[envs_index + 1]
        except ValueError:
            pass
        return None

    @classmethod
    def check_labelimg_available(cls, python_path: Optional[str] = None) -> Tuple[bool, str]:
        """
        Check if LabelImg is available in specified Python environment

        Args:
            python_path: Path to Python interpreter. If None, uses sys.executable

        Returns:
            Tuple of (is_available, error_message)
        """
        python = python_path or sys.executable

        # Try using conda/mamba run first (more reliable)
        conda_exe, conda_type = cls._find_conda_executable()
        env_name = cls._get_env_name_from_python_path(python)

        if conda_exe and env_name:
            try:
                result = subprocess.run(
                    [conda_exe, "run", "-n", env_name, "labelImg", "--help"],
                    capture_output=True,
                    timeout=10
                )
                if result.returncode == 0:
                    return True, ""
            except FileNotFoundError:
                pass
            except subprocess.TimeoutExpired:
                return False, "LabelImg check timed out"
            except Exception as e:
                pass  # Fall through to other methods

        # Try Scripts/labelImg.exe (Windows) or bin/labelImg (Unix)
        python_dir = Path(python).parent
        if sys.platform == "win32":
            labelimg_exe = python_dir / "Scripts" / "labelImg.exe"
        else:
            labelimg_exe = python_dir / "bin" / "labelImg"

        if labelimg_exe.exists():
            try:
                result = subprocess.run(
                    [str(labelimg_exe), "--help"],
                    capture_output=True,
                    timeout=5
                )
                if result.returncode == 0:
                    return True, ""
            except FileNotFoundError:
                return False, f"Cannot execute LabelImg: {labelimg_exe}"
            except subprocess.TimeoutExpired:
                return False, "LabelImg check timed out"
            except Exception as e:
                return False, f"LabelImg check failed: {e}"

        # Fallback to python -m labelImg
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

    @staticmethod
    def _reset_labelimg_config():
        """
        Reset LabelImg configuration file to fix display issues.

        LabelImg's config file can become corrupted and prevent images from displaying.
        This method backs up and removes the config file if it exists.
        """
        config_file = Path.home() / ".labelImgSettings.pkl"

        if config_file.exists():
            backup_file = config_file.with_suffix('.pkl.backup')
            try:
                # Backup existing config
                shutil.copy2(config_file, backup_file)
                # Remove corrupted config
                config_file.unlink()
            except Exception:
                # If reset fails, continue anyway - not critical
                pass

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

        # Reset LabelImg config to avoid display issues from corrupted config
        cls._reset_labelimg_config()

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

        # Build command - use conda/mamba run for proper environment setup
        cmd = cls._build_launch_command(
            python_path, str(image_dir), str(dst_classes), str(label_dir)
        )

        try:
            # Launch LabelImg as a separate process (show window)
            # Note: We intentionally do NOT use DETACHED_PROCESS because we want the window to be visible
            subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True  # Create new process group but keep window visible
            )
            return True
        except Exception as e:
            raise LabelImgLaunchError(f"Failed to launch LabelImg: {e}")

    @classmethod
    def _build_launch_command(
        cls,
        python_path: str,
        image_dir: str,
        classes_file: str,
        label_dir: str
    ) -> List[str]:
        """
        Build the command to launch LabelImg

        Priority:
        1. conda/mamba run (most reliable for GUI apps)
        2. Direct executable
        3. python -m labelImg

        Args:
            python_path: Path to Python interpreter
            image_dir: Directory containing images
            classes_file: Path to classes.txt
            label_dir: Directory for saving labels

        Returns:
            Command list for subprocess
        """
        # Try conda/mamba run first (most reliable for GUI apps)
        conda_exe, conda_type = cls._find_conda_executable()
        env_name = cls._get_env_name_from_python_path(python_path)

        if conda_exe and env_name:
            # Use conda/mamba run - this properly sets up the environment
            # Command: mamba run -n labelimg labelImg <image_dir> <classes_file> <label_dir>
            return [
                conda_exe, "run", "-n", env_name,
                "labelImg",
                image_dir,
                classes_file,
                label_dir
            ]

        # Fallback to direct executable
        python_dir = Path(python_path).parent
        if sys.platform == "win32":
            labelimg_exe = python_dir / "Scripts" / "labelImg.exe"
        else:
            labelimg_exe = python_dir / "bin" / "labelImg"

        if labelimg_exe.exists():
            return [
                str(labelimg_exe),
                image_dir,
                classes_file,
                label_dir
            ]

        # Final fallback to python -m labelImg
        return [
            python_path,
            "-m",
            "labelImg",
            image_dir,
            classes_file,
            label_dir
        ]
