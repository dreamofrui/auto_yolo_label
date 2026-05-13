"""
AutoLabeler 自定义异常类
提供清晰的错误分类和错误信息
"""


class AutoLabelerError(Exception):
    """基础异常类"""

    def __init__(self, message: str, details: str = ""):
        self.message = message
        self.details = details
        super().__init__(self._format_message())

    def _format_message(self) -> str:
        if self.details:
            return f"{self.message}: {self.details}"
        return self.message


class DeviceError(AutoLabelerError):
    """设备相关错误"""
    pass


class ScanError(AutoLabelerError):
    """扫描相关错误"""
    pass


class SampleError(AutoLabelerError):
    """抽样相关错误"""
    pass


class TrainError(AutoLabelerError):
    """训练相关错误"""
    pass


class InferenceError(AutoLabelerError):
    """推理相关错误"""
    pass


class RestoreError(AutoLabelerError):
    """还原相关错误"""
    pass


class ConvertError(AutoLabelerError):
    """格式转换相关错误"""
    pass


class MappingError(AutoLabelerError):
    """映射文件相关错误"""
    pass


class ValidationError(AutoLabelerError):
    """输入验证错误"""
    pass


class FileOperationError(AutoLabelerError):
    """文件操作错误"""
    pass


class ImageLoadError(AutoLabelerError):
    """图片加载错误"""
    pass
