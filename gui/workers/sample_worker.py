"""
AutoLabeler 抽样工作线程
在后台执行抽样操作，避免阻塞 UI
"""

from pathlib import Path
from gui.workers.base_worker import BaseWorker
from core.sampler import Sampler, SampleConfig
from utils.mapping_manager import MappingManager


class SampleWorker(BaseWorker):
    """
    抽样工作线程
    在后台执行抽样操作
    """

    def __init__(self, site_folder: Path, output_dir: Path, config: dict, parent=None):
        super().__init__(parent)
        self.site_folder = site_folder
        self.output_dir = output_dir
        self.config = config
        self.sampler = None
        self.result = None

    def run(self):
        """执行抽样"""
        try:
            self.report_log(f"开始抽样: {self.site_folder}")

            # 检查 mapping.json
            mapping_path = self.site_folder / ".autolabeler" / "mapping.json"
            if not mapping_path.exists():
                self.report_error("找不到 mapping.json，请先执行扫描操作")
                return

            # 加载映射
            mapping = MappingManager(mapping_path)
            mapping.load()

            # 创建抽样配置
            sample_config = SampleConfig(
                mode=self.config.get("mode", "count"),
                count=self.config.get("count", 40),
                ratio=self.config.get("ratio", 0.3),
                full_threshold=self.config.get("full_threshold", 35),
                train_ratio=self.config.get("train_ratio", 0.9),
            )

            # 创建抽样器
            self.sampler = Sampler(sample_config)

            # 设置进度回调
            def progress_callback(info):
                if self.is_cancelled:
                    return
                self.report_progress(
                    info.current,
                    info.total,
                    f"抽样中: {info.message}"
                )

            self.sampler.set_progress_callback(progress_callback)

            # 执行抽样
            self.sampler.sample(mapping, self.site_folder, self.output_dir)

            # 获取统计信息
            stats = mapping.get_statistics()
            sampled = mapping.get_sampled_images()

            train_count = sum(1 for img in sampled if img.get("split") == "train")
            val_count = sum(1 for img in sampled if img.get("split") == "vals")

            self.report_log(f"抽样完成:")
            self.report_log(f"  - 抽取样本: {stats.get('sampled_count', 0)}")
            self.report_log(f"  - 训练集: {train_count}")
            self.report_log(f"  - 验证集: {val_count}")

            # 准备结果
            self.result = {
                "mapping_path": str(mapping.mapping_path),
                "statistics": {
                    "total_products": stats.get("total_products", 0),
                    "sampled_count": stats.get("sampled_count", 0),
                    "train_count": train_count,
                    "val_count": val_count,
                }
            }

            self.report_success(self.result)

        except Exception as e:
            self.report_error(f"抽样失败: {str(e)}")
            self.report_log(f"错误详情: {str(e)}")

    def cancel(self):
        """取消抽样"""
        super().cancel()
        if self.sampler:
            self.sampler.cancel()
