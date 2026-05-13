"""Tests for device detection helpers."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from utils.device import DeviceInfo, get_device_info, get_optimal_batch_size, resolve_device
from utils.exceptions import ValidationError


@dataclass(frozen=True)
class FakeDeviceProperties:
    """Minimal CUDA properties used by the device probe."""

    total_memory: int


@dataclass(frozen=True)
class FakeProbe:
    """Deterministic device probe for tests."""

    cuda_available: bool = False
    cuda_count: int = 0
    cuda_name: str = "NVIDIA Test"
    cuda_memory_mb: int = 0
    mps_available: bool = False

    def is_cuda_available(self) -> bool:
        """Return whether CUDA is available."""
        return self.cuda_available

    def cuda_device_count(self) -> int:
        """Return the number of CUDA devices."""
        return self.cuda_count

    def cuda_device_name(self, index: int) -> str:
        """Return a CUDA device name."""
        assert index == 0
        return self.cuda_name

    def cuda_device_properties(self, index: int) -> FakeDeviceProperties:
        """Return CUDA memory in bytes."""
        assert index == 0
        return FakeDeviceProperties(total_memory=self.cuda_memory_mb * 1024 * 1024)

    def is_mps_available(self) -> bool:
        """Return whether MPS is available."""
        return self.mps_available


def test_get_device_info_returns_cpu_when_no_accelerator() -> None:
    """CPU fallback uses an empty device id and zero memory."""
    info = get_device_info(FakeProbe())

    assert info == DeviceInfo(
        device="cpu",
        device_id="",
        is_available=True,
        name="CPU",
        memory_mb=0,
    )


def test_get_device_info_returns_single_cuda_device() -> None:
    """Single CUDA devices use id 0 and expose GPU memory."""
    info = get_device_info(
        FakeProbe(cuda_available=True, cuda_count=1, cuda_name="RTX 4090", cuda_memory_mb=24576)
    )

    assert info == DeviceInfo(
        device="cuda",
        device_id="0",
        is_available=True,
        name="RTX 4090 x1",
        memory_mb=24576,
    )


def test_get_device_info_returns_all_cuda_device_ids() -> None:
    """Multiple CUDA devices are represented as a comma-separated id list."""
    info = get_device_info(FakeProbe(cuda_available=True, cuda_count=2, cuda_memory_mb=12288))

    assert info.device == "cuda"
    assert info.device_id == "0,1"
    assert info.name == "NVIDIA Test x2"


def test_get_device_info_prefers_mps_after_cuda() -> None:
    """MPS is selected when CUDA is unavailable and MPS is available."""
    info = get_device_info(FakeProbe(mps_available=True))

    assert info == DeviceInfo(
        device="mps",
        device_id="",
        is_available=True,
        name="Apple Silicon GPU",
        memory_mb=0,
    )


def test_resolve_device_auto_maps_to_yolo_device() -> None:
    """Auto resolution returns the YOLO device string for the best device."""
    assert resolve_device("auto", FakeProbe(cuda_available=True, cuda_count=2)) == "0,1"
    assert resolve_device("auto", FakeProbe(mps_available=True)) == "mps"
    assert resolve_device("auto", FakeProbe()) == "cpu"


def test_resolve_device_accepts_explicit_values() -> None:
    """Explicit supported values pass through unchanged."""
    assert resolve_device("cpu", FakeProbe()) == "cpu"
    assert resolve_device("mps", FakeProbe()) == "mps"
    assert resolve_device("0", FakeProbe()) == "0"
    assert resolve_device("0,1", FakeProbe()) == "0,1"


def test_resolve_device_rejects_invalid_values() -> None:
    """Unsupported device strings raise a validation error."""
    with pytest.raises(ValidationError) as exc_info:
        resolve_device("gpu", FakeProbe())

    assert exc_info.value.code.value == "VALIDATION_ERROR"


def test_get_optimal_batch_size_is_conservative() -> None:
    """Batch-size selection is deterministic and conservative."""
    assert get_optimal_batch_size("cpu", probe=FakeProbe()) == 1
    assert get_optimal_batch_size("0", probe=FakeProbe(cuda_available=True, cuda_memory_mb=24576)) == 32
    assert get_optimal_batch_size("0", probe=FakeProbe(cuda_available=True, cuda_memory_mb=12288)) == 16
    assert get_optimal_batch_size("0", probe=FakeProbe(cuda_available=True, cuda_memory_mb=6144)) == 8
    assert get_optimal_batch_size("0", probe=FakeProbe(cuda_available=True, cuda_memory_mb=4096)) == 4
    assert get_optimal_batch_size("mps", probe=FakeProbe(mps_available=True)) == 8
