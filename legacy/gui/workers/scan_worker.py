"""
AutoLabeler 扫描工作线程
在后台执行扫描操作，避免阻塞 UI
"""

from pathlib import Path
from gui.workers.base_worker import BaseWorker
from core.scanner import Scanner
from utils.mapping_manager import MappingManager


class ScanWorker(BaseWorker):
    """
    扫描工作线程
    在后台执行扫描操作
    """

    def __init__(self, site_folder: Path, parent=None):
        super().__init__(parent)
        self.site_folder = site_folder
        self.scanner = None
        self.result = None

    def run(self):
        """执行扫描"""
        try:
            self.report_log(f"开始扫描: {self.site_folder}")

            # 创建扫描器
            self.scanner = Scanner()

            # 设置进度回调
            def progress_callback(info):
                if self.is_cancelled:
                    return
                self.report_progress(
                    info.current,
                    info.total,
                    f"扫描中: {info.message}"
                )

            self.scanner.set_progress_callback(progress_callback)

            # 执行扫描
            mapping = self.scanner.scan(self.site_folder)

            # 获取统计信息
            stats = mapping.get_statistics()

            self.report_log(f"扫描完成:")
            self.report_log(f"  - Code 数量: {stats.get('total_codes', 0)}")
            self.report_log(f"  - 产品数量: {stats.get('total_products', 0)}")
            self.report_log(f"  - 图片总数: {stats.get('total_images', 0)}")

            # 准备结果
            self.result = {
                "mapping_path": str(mapping.mapping_path),
                "statistics": stats,
                "classes": mapping.get_class_list()
            }

            self.report_success(self.result)

        except Exception as e:
            self.report_error(f"扫描失败: {str(e)}")
            self.report_log(f"错误详情: {str(e)}")

    def cancel(self):
        """取消扫描"""
        super().cancel()
        if self.scanner:
            self.scanner.cancel()
