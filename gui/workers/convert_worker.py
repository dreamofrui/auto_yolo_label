"""
AutoLabeler 转换工作线程
在后台执行转换操作，避免阻塞 UI
"""

from pathlib import Path
from gui.workers.base_worker import BaseWorker
from core.converter import Converter
from utils.mapping_manager import MappingManager


class ConvertWorker(BaseWorker):
    """
    转换工作线程
    在后台执行转换操作
    """

    def __init__(self, folder: Path, config: dict, parent=None):
        super().__init__(parent)
        self.folder = folder
        self.config = config
        self.converter = None
        self.result = None

    def run(self):
        """执行转换"""
        try:
            self.report_log(f"开始转换: {self.folder}")

            # 尝试从 mapping.json 加载类别
            classes = None
            mapping_path = self.folder / ".autolabeler" / "mapping.json"
            if mapping_path.exists():
                try:
                    mapping = MappingManager(mapping_path)
                    mapping.load()
                    classes = mapping.get_class_list()
                    self.report_log(f"从 mapping.json 加载了 {len(classes)} 个类别")
                except Exception:
                    pass

            # 如果没有找到类别，使用默认值
            if not classes:
                classes = ["class_0", "class_1", "class_2"]
                self.report_log("使用默认类别列表")

            # 创建转换器
            self.converter = Converter()

            # 设置进度回调
            def progress_callback(info):
                if self.is_cancelled:
                    return
                self.report_progress(
                    info.current,
                    info.total,
                    f"转换中: {info.message}"
                )

            self.converter.set_progress_callback(progress_callback)

            # 执行转换
            convert_result = self.converter.convert_folder(
                folder=self.folder,
                classes=classes,
                recursive=self.config.get("recursive", True)
            )

            self.report_log(f"转换完成:")
            self.report_log(f"  - 总文件数: {convert_result.total}")
            self.report_log(f"  - 成功转换: {convert_result.success}")
            self.report_log(f"  - 跳过: {convert_result.skipped}")
            self.report_log(f"  - 失败: {convert_result.failed}")

            # 准备结果
            self.result = {
                "total": convert_result.total,
                "success": convert_result.success,
                "skipped": convert_result.skipped,
                "failed": convert_result.failed,
            }

            self.report_success(self.result)

        except Exception as e:
            self.report_error(f"转换失败: {str(e)}")
            self.report_log(f"错误详情: {str(e)}")

    def cancel(self):
        """取消转换"""
        super().cancel()
        if self.converter:
            self.converter.cancel()
