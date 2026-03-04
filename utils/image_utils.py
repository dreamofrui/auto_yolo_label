"""
AutoLabeler 图片工具模块
提供图片尺寸读取、验证等功能
"""

from pathlib import Path
from typing import Tuple, Optional
from PIL import Image
import logging

logger = logging.getLogger(__name__)


def get_image_size(image_path: Path) -> Tuple[int, int, int]:
    """
    获取图片尺寸信息

    Args:
        image_path: 图片文件路径

    Returns:
        (width, height, depth) 元组
        - width: 图片宽度（像素）
        - height: 图片高度（像素）
        - depth: 通道数（通常为 3 表示 RGB）

    Raises:
        FileNotFoundError: 图片不存在
        IOError: 图片无法读取
    """
    if not image_path.exists():
        raise FileNotFoundError(f"图片不存在: {image_path}")

    try:
        with Image.open(image_path) as img:
            width, height = img.size
            # 获取模式以确定通道数
            mode = img.mode
            if mode in ('RGB', 'RGBA'):
                depth = 3 if mode == 'RGB' else 4
            elif mode == 'L':
                depth = 1
            elif mode == 'P':
                # 调色板模式，转换为 RGB 获取通道数
                depth = 3
            else:
                depth = 3  # 默认值

            return width, height, depth
    except Exception as e:
        raise IOError(f"无法读取图片 {image_path}: {str(e)}")


def validate_image(image_path: Path) -> bool:
    """
    验证图片文件是否有效

    Args:
        image_path: 图片文件路径

    Returns:
        True 如果图片有效，False 否则
    """
    try:
        with Image.open(image_path) as img:
            img.verify()
        return True
    except Exception:
        return False


def get_image_format(image_path: Path) -> Optional[str]:
    """
    获取图片格式

    Args:
        image_path: 图片文件路径

    Returns:
        格式字符串（如 "JPEG", "PNG"），无法识别返回 None
    """
    try:
        with Image.open(image_path) as img:
            return img.format
    except Exception:
        return None


class ImageInfo:
    """图片信息缓存类"""

    def __init__(self, path: Path):
        self.path = path
        self._width = None
        self._height = None
        self._depth = None
        self._format = None

    def load(self) -> bool:
        """加载图片信息"""
        try:
            self._width, self._height, self._depth = get_image_size(self.path)
            self._format = get_image_format(self.path)
            return True
        except Exception:
            return False

    @property
    def width(self) -> Optional[int]:
        if self._width is None:
            self.load()
        return self._width

    @property
    def height(self) -> Optional[int]:
        if self._height is None:
            self.load()
        return self._height

    @property
    def depth(self) -> Optional[int]:
        if self._depth is None:
            self.load()
        return self._depth

    @property
    def format(self) -> Optional[str]:
        if self._format is None:
            self.load()
        return self._format
