"""
AutoLabeler 推理工作线程
在后台执行推理操作，避免阻塞 UI
"""

from pathlib import Path
from gui.workers.base_worker import BaseWorker
from core.inferencer import Inferencer, InferenceConfig
from utils.mapping_manager import MappingManager


class InferenceWorker(BaseWorker):
    """
    推理工作线程
    在后台执行推理操作
    """

    def __init__(self, model_path: Path, site_folder: Path, config: dict, parent=None):
        super().__init__(parent)
        self.model_path = model_path
        self.site_folder = site_folder
        self.config = config
        self.inferencer = None
        self.result = None

    def run(self):
        """执行推理"""
        try:
            # 显示模型绝对路径
            self.report_log(f"开始推理:")
            self.report_log(f"  - 模型: {self.model_path.absolute()}")
            self.report_log(f"  - 站点: {self.site_folder.absolute()}")

            # 检查 mapping.json
            mapping_path = self.site_folder / ".autolabeler" / "mapping.json"
            if not mapping_path.exists():
                self.report_error("找不到 mapping.json，请先执行扫描操作")
                return

            # 加载映射
            mapping = MappingManager(mapping_path)
            mapping.load()

            # 创建推理配置
            inference_config = InferenceConfig(
                confidence=self.config.get("confidence", 0.25),
                iou=self.config.get("iou", 0.45),
                batch_size=self.config.get("batch_size", -1),
                device=self.config.get("device", "auto"),
            )

            # 创建推理器
            self.inferencer = Inferencer(inference_config)

            # 设置进度回调
            def progress_callback(info):
                if self.is_cancelled:
                    return
                self.report_progress(
                    info.current,
                    info.total,
                    f"推理中: {info.message}"
                )

            self.inferencer.set_progress_callback(progress_callback)

            # 执行推理
            processed_count = self.inferencer.infer(
                model_path=self.model_path,
                mapping=mapping,
                site_folder=self.site_folder
            )

            # 显示保存路径
            if self.inferencer.inference_output_dir:
                self.report_log(f"  - 保存位置: {self.inferencer.inference_output_dir.absolute()}")

            # 获取统计信息
            stats = mapping.get_statistics()
            pending_count = len(mapping.get_pending_inference_images())

            self.report_log(f"推理完成:")
            self.report_log(f"  - 处理图片: {processed_count}")

            # 准备结果
            self.result = {
                "mapping_path": str(mapping.mapping_path),
                "inference_output_dir": str(self.inferencer.inference_output_dir) if self.inferencer.inference_output_dir else None,
                "statistics": {
                    "pending": pending_count,
                    "processed": processed_count,
                    "success": processed_count,
                    "failed": 0,
                }
            }

            self.report_success(self.result)

        except Exception as e:
            self.report_error(f"推理失败: {str(e)}")
            self.report_log(f"错误详情: {str(e)}")

    def cancel(self):
        """取消推理"""
        super().cancel()
        if self.inferencer:
            self.inferencer.cancel()
