"""Tests for path encoding helpers."""

from __future__ import annotations

from pathlib import Path

import pytest

from utils.exceptions import ValidationError
from utils.path_encoder import DecodedPath, PathEncoder


def test_encode_flattens_code_product_and_filename() -> None:
    """The default separator is a double underscore."""
    encoder = PathEncoder()

    encoded = encoder.encode("AS_CV_PI_P", "H4A238FDF04", "IMG_001.jpg")

    assert encoded == "AS_CV_PI_P__H4A238FDF04__IMG_001.jpg"


def test_decode_returns_path_components() -> None:
    """Encoded names can be decoded into their path components."""
    encoder = PathEncoder()

    decoded = encoder.decode("AS_CV_PI_P__H4A238FDF04__IMG_001.jpg")

    assert decoded == DecodedPath(
        code="AS_CV_PI_P",
        product="H4A238FDF04",
        filename="IMG_001.jpg",
        extension=".jpg",
    )


def test_to_relative_path_returns_code_product_filename_path() -> None:
    """Encoded names can be converted to relative source paths."""
    encoder = PathEncoder()

    relative = encoder.to_relative_path("AS_CV_PI_P__H4A238FDF04__IMG_001.jpg")

    assert relative == Path("AS_CV_PI_P") / "H4A238FDF04" / "IMG_001.jpg"


def test_decode_invalid_encoded_name_returns_none() -> None:
    """Names without exactly three components are not decoded."""
    encoder = PathEncoder()

    assert encoder.decode("IMG_001.jpg") is None
    assert encoder.decode("Code__Product__Name__TooMany.jpg") is None


def test_encode_rejects_separator_conflicts() -> None:
    """Path parts cannot contain the separator because decoding would be ambiguous."""
    encoder = PathEncoder()

    with pytest.raises(ValidationError):
        encoder.encode("Code", "Product", "IMG__001.jpg")


def test_custom_separator_is_supported() -> None:
    """A custom separator can be used for compatibility tests."""
    encoder = PathEncoder(separator="--")

    encoded = encoder.encode("Code", "Product", "Image.jpg")

    assert encoded == "Code--Product--Image.jpg"
    assert encoder.decode(encoded) == DecodedPath(
        code="Code",
        product="Product",
        filename="Image.jpg",
        extension=".jpg",
    )
