"""
AutoLabeler 设备检测与管理模块
自动检测 GPU/CPU 并返回最优设备配置
"""

import torch
from dataclasses import dataclass
from typing import Optional


@dataclass
class DeviceInfo:
    """设备信息"""
    device: str                # "cpu" 或 "cuda"
    device_id: Optional[str]   # GPU ID，如 "0" 或 "0,1"
    is_available: bool         # 是否可用
    name: str                  # 设备名称
    memory: Optional[int]      # 显存大小（MB）


def get_device_info() -> DeviceInfo:
    """
    自动检测并返回最优设备信息

    Returns:
        DeviceInfo: 设备信息对象
    """
    if torch.cuda.is_available():
        gpu_count = torch.cuda.device_count()
        gpu_name = torch.cuda.get_device_name(0)
        gpu_memory = torch.cuda.get_device_properties(0).total_memory / (1024 * 1024)

        # 多GPU使用所有显卡
        device_id = ",".join(str(i) for i in range(gpu_count)) if gpu_count > 1 else "0"

        return DeviceInfo(
            device="cuda",
            device_id=device_id,
            is_available=True,
            name=f"{gpu_name} x{gpu_count}",
            memory=int(gpu_memory)
        )
    else:
        # 检查是否有 Apple Silicon (MPS)
        if hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            return DeviceInfo(
                device="mps",
                device_id=None,
                is_available=True,
                name="Apple Silicon GPU",
                memory=None
            )

        return DeviceInfo(
            device="cpu",
            device_id=None,
            is_available=True,
            name="CPU",
            memory=None
        )


def get_optimal_device() -> str:
    """
    获取最优设备字符串（用于传给 YOLO）

    Returns:
        设备字符串，如 "0" 或 "cpu"
    """
    info = get_device_info()
    if info.device == "cuda":
        return info.device_id or "0"
    elif info.device == "mps":
        return "mps"
    else:
        return "cpu"


def get_optimal_batch_size(device: str = None, image_size: int = 640) -> int:
    """
    根据设备自动计算最优 batch size

    Args:
        device: 设备类型，None 则自动检测
        image_size: 图片尺寸

    Returns:
        推荐的 batch size
    """
    info = get_device_info()

    if info.device == "cpu":
        return 8
    elif info.device == "cuda":
        # 根据显存估算
        if info.memory and info.memory >= 24000:  # 24GB+
            return 32
        elif info.memory and info.memory >= 12000:  # 12GB+
            return 16
        elif info.memory and info.memory >= 6000:   # 6GB+
            return 8
        else:
            return 4
    else:  # MPS or other
        return 16
