"""
AutoLabeler 训练工作线程
在后台执行训练操作，避免阻塞 UI
"""

from pathlib import Path
import yaml
import logging
from gui.workers.base_worker import BaseWorker
from core.trainer import Trainer, TrainConfig
from PySide6.QtCore import Signal

# 显式导入 ultralytics 确保 PyInstaller 打包相关模块
# 使用延迟导入避免在模块加载时触发依赖检查

logger = logging.getLogger(__name__)


class YOLOLogHandler(logging.Handler):
    """YOLO 日志 Handler，只捕获 WARNING 和 ERROR"""
    def __init__(self, log_callback):
        super().__init__()
        self.log_callback = log_callback

    def emit(self, record):
        try:
            # 只显示 WARNING 和 ERROR 级别的日志
            if record.levelno >= logging.WARNING:
                msg = self.format(record)
                self.log_callback(f"[{record.levelname}] {msg}")
        except Exception:
            pass


class TrainWorker(BaseWorker):
    """
    训练工作线程
    在后台执行训练操作
    """

    # 新增信号
    metrics = Signal(dict)  # 训练指标

    def __init__(self, data_yaml: Path, model_path: Path, output_dir: Path, config: dict, parent=None):
        super().__init__(parent)
        self.data_yaml = data_yaml
        self.model_path = model_path
        self.output_dir = output_dir
        self.config = config
        self.trainer = None
        self.result = None

    def run(self):
        """执行训练"""
        # 添加日志 handler 以捕获 YOLO 输出
        yolo_logger = logging.getLogger('ultralytics')
        yolo_logger.setLevel(logging.INFO)
        yolo_handler = YOLOLogHandler(self.report_log)
        yolo_handler.setFormatter(logging.Formatter('%(message)s'))
        yolo_logger.addHandler(yolo_handler)

        try:
            # 显示绝对路径
            self.report_log(f"开始训练: {self.model_path.absolute()}")
            self.report_log(f"数据配置: {self.data_yaml.absolute()}")
            self.report_log(f"输出目录: {self.output_dir.absolute()}")

            # 读取 data.yaml 获取类别信息
            try:
                with open(self.data_yaml, 'r', encoding='utf-8') as f:
                    data_config = yaml.safe_load(f)

                nc = data_config.get('nc', 0)
                names = data_config.get('names', [])

                # 显示类别信息（从配置中读取）
                self.report_log(f"类别: {nc} 类 - {names}")
                self.report_log("正在启动训练，请稍候...")

            except Exception as e:
                self.report_log(f"警告: 无法读取数据集配置: {str(e)}")
                logger.warning(f"Failed to read data config: {e}")

            # 创建训练配置
            train_config = TrainConfig(
                epochs=self.config.get("epochs", 100),
                batch_size=self.config.get("batch_size", -1),
                image_size=self.config.get("image_size", 640),
                device=self.config.get("device", "auto"),
                patience=self.config.get("patience", 50),
                box=self.config.get("box", 7.5),
                cls=self.config.get("cls", 0.5),
                scale=self.config.get("scale", 0.5),
            )

            # 创建训练器
            self.trainer = Trainer(train_config)

            # 设置进度回调
            def progress_callback(info):
                if self.is_cancelled:
                    return
                # 区分日志消息和进度更新
                if info.current == 0 and info.total == 0:
                    # 这是日志消息
                    self.report_log(info.message)
                elif info.message == "Training completed":
                    # 训练完成，不添加"训练中："前缀
                    self.report_progress(info.current, info.total, "训练完成")
                else:
                    # 这是进度更新
                    self.report_progress(
                        info.current,
                        info.total,
                        f"训练中: {info.message}"
                    )

            self.trainer.set_progress_callback(progress_callback)

            # 定义 epoch 回调
            def epoch_callback(epoch_info):
                if self.is_cancelled:
                    return
                # 发送指标更新信号
                self.metrics.emit(epoch_info)

            # 执行训练
            best_model = self.trainer.train(
                data_yaml=self.data_yaml,
                base_model=self.model_path,
                output_dir=self.output_dir,
                epoch_callback=epoch_callback
            )

            if best_model:
                self.report_log("-" * 50)
                self.report_log(f"训练完成!")
                self.report_log(f"最佳模型: {best_model}")

                # 准备结果
                self.result = {
                    "best_model": str(best_model),
                    "config": self.config,
                }

                self.report_success(self.result)
            else:
                if self.is_cancelled:
                    self.report_error("训练已取消")
                else:
                    self.report_error("训练失败: 未生成模型文件")

        except Exception as e:
            # 记录完整异常信息
            import traceback
            error_msg = str(e)
            error_details = traceback.format_exc()
            self.report_log(f"训练异常: {error_msg}")
            self.report_log(f"详细错误:\n{error_details}")
            self.report_error(f"训练失败: {error_msg}")
            logger.error(f"Training failed: {error_msg}\n{error_details}")
        finally:
            # 清理 handler
            yolo_logger.removeHandler(yolo_handler)

    def cancel(self):
        """取消训练"""
        super().cancel()
        if self.trainer:
            self.trainer.cancel()
