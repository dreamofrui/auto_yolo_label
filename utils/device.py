"""Device detection helpers for training and inference."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, cast

from utils.exceptions import ValidationError

_BYTES_PER_MIB = 1024 * 1024


@dataclass(frozen=True)
class DeviceInfo:
    """Detected compute device information."""

    device: str
    device_id: str
    is_available: bool
    name: str
    memory_mb: int


class DeviceProperties(Protocol):
    """CUDA device properties used by device detection."""

    total_memory: int


class DeviceProbe(Protocol):
    """Probe interface for hardware detection."""

    def is_cuda_available(self) -> bool:
        """Return whether CUDA is available."""

    def cuda_device_count(self) -> int:
        """Return the number of CUDA devices."""

    def cuda_device_name(self, index: int) -> str:
        """Return the display name for a CUDA device."""

    def cuda_device_properties(self, index: int) -> DeviceProperties:
        """Return properties for a CUDA device."""

    def is_mps_available(self) -> bool:
        """Return whether Apple MPS is available."""


class TorchDeviceProbe:
    """Torch-backed implementation of DeviceProbe."""

    def __init__(self) -> None:
        """Import torch lazily so CPU-only tooling can still import this module."""
        try:
            import torch
        except ImportError:
            self._torch = None
        else:
            self._torch = torch

    def is_cuda_available(self) -> bool:
        """Return whether CUDA is available."""
        return bool(self._torch is not None and self._torch.cuda.is_available())

    def cuda_device_count(self) -> int:
        """Return the number of CUDA devices."""
        if self._torch is None:
            return 0
        return int(self._torch.cuda.device_count())

    def cuda_device_name(self, index: int) -> str:
        """Return the display name for a CUDA device."""
        if self._torch is None:
            return ""
        return str(self._torch.cuda.get_device_name(index))

    def cuda_device_properties(self, index: int) -> DeviceProperties:
        """Return properties for a CUDA device."""
        if self._torch is None:
            raise RuntimeError("torch is not available")
        return cast(DeviceProperties, self._torch.cuda.get_device_properties(index))

    def is_mps_available(self) -> bool:
        """Return whether Apple MPS is available."""
        if self._torch is None:
            return False
        backends = getattr(self._torch, "backends", None)
        mps = getattr(backends, "mps", None)
        return bool(mps is not None and mps.is_available())


def get_device_info(probe: DeviceProbe | None = None) -> DeviceInfo:
    """Detect the best available compute device.

    Args:
        probe: Optional probe for tests or alternate hardware backends.

    Returns:
        Detected device information.
    """
    effective_probe = probe or TorchDeviceProbe()
    if effective_probe.is_cuda_available():
        count = max(effective_probe.cuda_device_count(), 1)
        device_id = ",".join(str(index) for index in range(count))
        properties = effective_probe.cuda_device_properties(0)
        memory_mb = int(properties.total_memory / _BYTES_PER_MIB)
        return DeviceInfo(
            device="cuda",
            device_id=device_id,
            is_available=True,
            name=f"{effective_probe.cuda_device_name(0)} x{count}",
            memory_mb=memory_mb,
        )

    if effective_probe.is_mps_available():
        return DeviceInfo(
            device="mps",
            device_id="",
            is_available=True,
            name="Apple Silicon GPU",
            memory_mb=0,
        )

    return DeviceInfo(
        device="cpu",
        device_id="",
        is_available=True,
        name="CPU",
        memory_mb=0,
    )


def resolve_device(requested: str = "auto", probe: DeviceProbe | None = None) -> str:
    """Resolve a user device value to a YOLO-compatible device string.

    Args:
        requested: Device request: "auto", "cpu", "mps", "0", or "0,1".
        probe: Optional probe for tests or alternate hardware backends.

    Returns:
        YOLO-compatible device string.

    Raises:
        ValidationError: If the requested device string is unsupported.
    """
    normalized = requested.strip().lower()
    if normalized == "auto":
        info = get_device_info(probe)
        if info.device == "cuda":
            return info.device_id
        return info.device
    if normalized in {"cpu", "mps"}:
        return normalized
    if _is_cuda_id_list(normalized):
        return normalized
    raise ValidationError(
        "设备参数无效",
        details=f"device must be auto/cpu/mps or CUDA ids, got {requested!r}",
    )


def get_optimal_batch_size(
    device: str = "auto",
    image_size: int = 640,
    probe: DeviceProbe | None = None,
) -> int:
    """Return a conservative batch-size recommendation.

    Args:
        device: Device request or resolved device string.
        image_size: Input image size. Reserved for future tuning.
        probe: Optional probe for tests or alternate hardware backends.

    Returns:
        Recommended batch size, always at least 1.
    """
    del image_size
    resolved = resolve_device(device, probe)
    if resolved == "cpu":
        return 1
    if resolved == "mps":
        return 8

    info = get_device_info(probe)
    if info.device != "cuda":
        return 1
    if info.memory_mb >= 24_000:
        return 32
    if info.memory_mb >= 12_000:
        return 16
    if info.memory_mb >= 6_000:
        return 8
    return 4


def _is_cuda_id_list(value: str) -> bool:
    """Return whether value is a comma-separated CUDA id list."""
    if not value:
        return False
    return all(part.isdigit() for part in value.split(","))
