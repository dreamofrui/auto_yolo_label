"""
AutoLabeler 后台工作线程基类
所有耗时操作都应在 Worker 中执行，避免阻塞 UI
"""

from PySide6.QtCore import QThread, Signal, QObject


class BaseWorker(QThread):
    """
    后台工作线程基类
    所有耗时操作都应在 Worker 中执行，避免阻塞 UI
    """

    # 信号定义
    progress = Signal(int, int, str)     # current, total, message
    finished = Signal(bool, object)       # success, result
    error = Signal(str)                   # error message
    log = Signal(str)                     # log message

    def __init__(self, parent=None):
        super().__init__(parent)
        self._is_cancelled = False

    def cancel(self):
        """请求取消操作"""
        self._is_cancelled = True

    @property
    def is_cancelled(self) -> bool:
        """是否已请求取消"""
        return self._is_cancelled

    def report_progress(self, current: int, total: int, message: str = ""):
        """
        报告进度

        Args:
            current: 当前进度
            total: 总数
            message: 进度消息
        """
        self.progress.emit(current, total, message)

    def report_log(self, message: str):
        """
        报告日志消息

        Args:
            message: 日志消息
        """
        self.log.emit(message)

    def report_success(self, result=None):
        """
        报告操作成功

        Args:
            result: 结果对象
        """
        self.finished.emit(True, result)

    def report_error(self, error_message: str):
        """
        报告操作失败

        Args:
            error_message: 错误消息
        """
        self.error.emit(error_message)
        self.finished.emit(False, None)

    def run(self):
        """
        线程执行入口（子类重写）

        子类应该重写此方法实现具体的工作逻辑
        """
        raise NotImplementedError("Subclasses must implement run()")
