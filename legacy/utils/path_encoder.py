"""
AutoLabeler 路径编码器
负责将 Code/Product/Filename 三级路径编码为单一文件名，以及反向解码
"""

from pathlib import Path
from typing import Tuple, Optional
from dataclasses import dataclass


@dataclass
class DecodedPath:
    """解码后的路径信息"""
    code: str
    product: str
    filename: str
    extension: str


class PathEncoder:
    """
    路径编码器
    负责将 Code/Product/Filename 三级路径编码为单一文件名，以及反向解码
    """

    DEFAULT_SEPARATOR = "__"

    def __init__(self, separator: str = None):
        """
        初始化编码器

        Args:
            separator: 路径层级分隔符，默认 "__"
        """
        self.separator = separator or self.DEFAULT_SEPARATOR

    def encode(self, code: str, product: str, filename: str) -> str:
        """
        将路径编码为文件名

        Args:
            code: Code文件夹名
            product: 产品文件夹名
            filename: 原始文件名

        Returns:
            编码后的文件名

        Example:
            encode("AS_CV_PI_P", "H4A238FDF04", "IMG_001.jpg")
            -> "AS_CV_PI_P__H4A238FDF04__IMG_001.jpg"
        """
        name, ext = self._split_extension(filename)
        encoded = f"{code}{self.separator}{product}{self.separator}{name}{ext}"
        return encoded

    def decode(self, encoded_name: str) -> Optional[DecodedPath]:
        """
        解码文件名为路径组件

        Args:
            encoded_name: 编码后的文件名

        Returns:
            DecodedPath 对象，解码失败返回 None

        Example:
            decode("AS_CV_PI_P__H4A238FDF04__IMG_001.jpg")
            -> DecodedPath(code="AS_CV_PI_P", product="H4A238FDF04",
                          filename="IMG_001.jpg", extension=".jpg")
        """
        name, ext = self._split_extension(encoded_name)
        parts = name.split(self.separator)

        if len(parts) < 3:
            return None

        code = parts[0]
        product = parts[1]
        original_name = self.separator.join(parts[2:]) + ext

        return DecodedPath(
            code=code,
            product=product,
            filename=original_name,
            extension=ext
        )

    def to_relative_path(self, encoded_name: str) -> Optional[Path]:
        """
        将编码文件名转换为相对路径

        Returns:
            Path对象: Code/Product/Filename
        """
        decoded = self.decode(encoded_name)
        if not decoded:
            return None
        return Path(decoded.code) / decoded.product / decoded.filename

    def _split_extension(self, filename: str) -> Tuple[str, str]:
        """分离文件名和扩展名"""
        p = Path(filename)
        return p.stem, p.suffix
