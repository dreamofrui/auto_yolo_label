"""
AutoLabeler 还原工作线程
在后台执行还原操作，避免阻塞 UI
支持从 database/labels/ 和 inference_results/ 还原
"""

from pathlib import Path
from gui.workers.base_worker import BaseWorker
from core.restorer import Restorer, RestoreResult
from utils.mapping_manager import MappingManager


class RestoreWorker(BaseWorker):
    """
    还原工作线程
    在后台执行还原操作
    支持两种来源：database 或 inference
    """

    def __init__(self, source_type: str, source_path: Path, site_folder: Path, parent=None):
        """
        Args:
            source_type: 来源类型 "database" 或 "inference"
            source_path: 源路径（database 目录或推理结果目录）
            site_folder: 站点文件夹
        """
        super().__init__(parent)
        self.source_type = source_type
        self.source_path = source_path
        self.site_folder = site_folder
        self.restorer = None
        self.result = None

    def run(self):
        """执行还原"""
        try:
            self.report_log(f"开始还原:")
            self.report_log(f"  - 站点: {self.site_folder.absolute()}")
            if self.source_type == "inference":
                self.report_log(f"  - 来源: 推理结果 ({self.source_path.name})")
            else:
                self.report_log(f"  - 来源: Database 目录")

            # 检查 mapping.json
            mapping_path = self.site_folder / ".autolabeler" / "mapping.json"
            if not mapping_path.exists():
                self.report_error("找不到 mapping.json，请先执行扫描操作")
                return

            # 加载映射
            mapping = MappingManager(mapping_path)
            mapping.load()

            # 创建还原器
            self.restorer = Restorer()

            # 设置进度回调
            def progress_callback(info):
                if self.is_cancelled:
                    return
                self.report_progress(
                    info.current,
                    info.total,
                    f"还原中: {info.message}"
                )

            self.restorer.set_progress_callback(progress_callback)

            # 根据来源类型执行还原
            if self.source_type == "inference":
                restore_result = self.restorer.restore_from_inference(
                    mapping=mapping,
                    inference_run_dir=self.source_path,
                    site_folder=self.site_folder
                )
            else:
                restore_result = self.restorer.restore(
                    mapping=mapping,
                    database_dir=self.source_path,
                    site_folder=self.site_folder
                )

            self.report_log(f"还原完成:")
            self.report_log(f"  - 总文件数: {restore_result.total}")
            self.report_log(f"  - 成功还原: {restore_result.success}")
            self.report_log(f"  - 跳过: {restore_result.skipped}")
            self.report_log(f"  - 失败: {restore_result.failed}")

            # 准备结果
            self.result = {
                "total": restore_result.total,
                "success": restore_result.success,
                "skipped": restore_result.skipped,
                "failed": restore_result.failed,
            }

            self.report_success(self.result)

        except Exception as e:
            self.report_error(f"还原失败: {str(e)}")
            self.report_log(f"错误详情: {str(e)}")

    def cancel(self):
        """取消还原"""
        super().cancel()
        if self.restorer:
            self.restorer.cancel()
