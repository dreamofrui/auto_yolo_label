"""
AutoLabeler 模块基类
定义所有核心模块的通用接口
"""

from abc import ABC
from typing import Callable, Optional
from dataclasses import dataclass


@dataclass
class ProgressInfo:
    """进度信息"""
    current: int           # 当前进度
    total: int             # 总数
    message: str           # 进度消息
    percentage: float      # 百分比 0-100


class BaseModule(ABC):
    """核心模块基类"""

    def __init__(self):
        self._progress_callback: Optional[Callable[[ProgressInfo], None]] = None
        self._is_cancelled: bool = False

    def set_progress_callback(self, callback: Callable[[ProgressInfo], None]):
        """设置进度回调函数"""
        self._progress_callback = callback

    def report_progress(self, current: int, total: int, message: str = ""):
        """报告进度"""
        if self._progress_callback:
            info = ProgressInfo(
                current=current,
                total=total,
                message=message,
                percentage=round(current / total * 100, 2) if total > 0 else 0
            )
            self._progress_callback(info)

    def cancel(self):
        """取消操作"""
        self._is_cancelled = True

    def reset(self):
        """重置状态"""
        self._is_cancelled = False

    @property
    def is_cancelled(self) -> bool:
        return self._is_cancelled
