"""Path encoding helpers for flattening site image paths."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from utils.exceptions import ValidationError


@dataclass(frozen=True)
class DecodedPath:
    """Decoded Code/Product/Filename path components."""

    code: str
    product: str
    filename: str
    extension: str


class PathEncoder:
    """Encode and decode Code/Product/Filename values."""

    DEFAULT_SEPARATOR = "__"

    def __init__(self, separator: str | None = None) -> None:
        """Create a path encoder.

        Args:
            separator: Separator used between encoded path parts.

        Raises:
            ValidationError: If separator is empty.
        """
        self.separator = separator or self.DEFAULT_SEPARATOR
        if not self.separator:
            raise ValidationError("路径编码分隔符不能为空")

    def encode(self, code: str, product: str, filename: str) -> str:
        """Encode Code/Product/Filename into one flat filename.

        Args:
            code: Code folder name.
            product: Product folder name.
            filename: Original filename including extension.

        Returns:
            Encoded filename.

        Raises:
            ValidationError: If any path part contains the separator.
        """
        self._validate_part("code", code)
        self._validate_part("product", product)
        self._validate_part("filename", filename)
        return self.separator.join((code, product, filename))

    def decode(self, encoded_name: str) -> DecodedPath | None:
        """Decode a flat filename into path components.

        Args:
            encoded_name: Encoded filename.

        Returns:
            Decoded path components, or None when the name is invalid.
        """
        parts = encoded_name.split(self.separator)
        if len(parts) != 3 or not all(parts):
            return None
        filename = parts[2]
        return DecodedPath(
            code=parts[0],
            product=parts[1],
            filename=filename,
            extension=Path(filename).suffix,
        )

    def to_relative_path(self, encoded_name: str) -> Path | None:
        """Convert an encoded filename to Code/Product/Filename relative path.

        Args:
            encoded_name: Encoded filename.

        Returns:
            Relative path, or None when the name is invalid.
        """
        decoded = self.decode(encoded_name)
        if decoded is None:
            return None
        return Path(decoded.code) / decoded.product / decoded.filename

    def _validate_part(self, field_name: str, value: str) -> None:
        """Validate one path component for encoding."""
        if not value:
            raise ValidationError("路径编码字段不能为空", details=field_name)
        if self.separator in value:
            raise ValidationError(
                "路径编码字段包含保留分隔符",
                details=f"{field_name} contains {self.separator!r}",
            )
