"""
AutoLabeler 训练模块
封装 YOLO 模型训练流程
"""

from pathlib import Path
from typing import Callable, Optional, Dict, Any
from dataclasses import dataclass
import logging
from .base import BaseModule
from utils.device import get_optimal_device, get_optimal_batch_size, get_device_info

logger = logging.getLogger(__name__)


@dataclass
class TrainConfig:
    """训练配置"""
    epochs: int = 100
    batch_size: int = -1        # -1 表示自动检测
    image_size: int = 640
    device: str = "auto"        # "auto" / "cpu" / "0" / "0,1" / "mps"
    patience: int = 50
    workers: int = 8
    optimizer: str = "AdamW"
    lr0: float = 0.01
    box: float = 7.5            # box loss gain (小目标检测可降低此值)
    cls: float = 0.5            # cls loss gain (小目标检测建议降低)
    dfl: float = 1.5            # distribution focal loss gain
    scale: float = 0.5          # image scale (+/- gain), 更小的值适合小目标
    cache: str = "ram"          # "ram" / "disk" / False - 数据缓存模式


class Trainer(BaseModule):
    """
    训练模块
    封装 YOLO 训练流程
    """

    def __init__(self, config: TrainConfig = None):
        super().__init__()
        self.config = config or TrainConfig()
        self.model = None
        self._device_info = None

    def _resolve_device(self) -> str:
        """
        解析最终使用的设备

        Returns:
            设备字符串
        """
        if self.config.device == "auto":
            return get_optimal_device()
        return self.config.device

    def _resolve_batch_size(self, device: str) -> int:
        """
        解析最终使用的 batch size

        Args:
            device: 设备字符串

        Returns:
            batch size 数值
        """
        if self.config.batch_size == -1:
            return get_optimal_batch_size(device, self.config.image_size)
        return self.config.batch_size

    def train(
        self,
        data_yaml: Path,
        base_model: Path,
        output_dir: Path,
        epoch_callback: Optional[Callable[[Dict], None]] = None
    ) -> Optional[Path]:
        """
        执行训练

        Args:
            data_yaml: 数据配置文件路径
            base_model: 基础模型路径 (yolo11m.pt)
            output_dir: 输出目录
            epoch_callback: 每个epoch结束时的回调

        Returns:
            best.pt 模型路径，训练取消或失败返回 None
        """
        from ultralytics import YOLO

        self.reset()

        # 检测设备信息
        self._device_info = get_device_info()
        device = self._resolve_device()
        batch_size = self._resolve_batch_size(device)

        # 报告设备信息
        self.report_progress(0, 1,
            f"Using device: {self._device_info.name}, "
            f"Batch Size: {batch_size}"
        )

        # 加载模型
        self.model = YOLO(str(base_model))

        # 用于跟踪上一个 epoch，避免重复报告
        last_reported_epoch = [-1]  # 使用列表使其在闭包中可变

        # 构建回调
        def on_fit_epoch_end(trainer):
            """使用 on_fit_epoch_end 而非 on_train_epoch_end，避免重复调用"""
            if self.is_cancelled:
                raise KeyboardInterrupt("Training cancelled by user")

            epoch = trainer.epoch
            epochs = trainer.epochs

            # 只在 epoch 变化时报告
            if epoch != last_reported_epoch[0]:
                last_reported_epoch[0] = epoch

                # 获取指标
                metrics_dict = {}
                if hasattr(trainer, 'metrics') and trainer.metrics is not None:
                    metrics = trainer.metrics
                    # 提取关键指标
                    if hasattr(metrics, 'box') and metrics.box is not None:
                        metrics_dict['mAP50'] = float(getattr(metrics.box, 'map50', 0.0))
                        metrics_dict['mAP50-95'] = float(getattr(metrics.box, 'map', 0.0))
                        # 添加日志输出
                        logger.info(f"Epoch {epoch+1}/{epochs}: mAP50={metrics_dict['mAP50']:.3f}, mAP50-95={metrics_dict['mAP50-95']:.3f}")
                    else:
                        logger.info(f"Epoch {epoch+1}/{epochs}: box metrics not available yet")
                        # 发送空的指标以确保 GUI 至少更新 epoch
                        metrics_dict['mAP50'] = 0.0
                        metrics_dict['mAP50-95'] = 0.0
                else:
                    logger.info(f"Epoch {epoch+1}/{epochs}: metrics not available yet")
                    # 发送空的指标以确保 GUI 至少更新 epoch
                    metrics_dict['mAP50'] = 0.0
                    metrics_dict['mAP50-95'] = 0.0

                self.report_progress(
                    epoch + 1, epochs,
                    f"Epoch {epoch+1}/{epochs} - "
                    f"mAP50: {metrics_dict.get('mAP50', 0):.3f}"
                )

                if epoch_callback:
                    epoch_callback({
                        "epoch": epoch + 1,
                        "total_epochs": epochs,
                        "metrics": metrics_dict
                    })

        # 添加回调
        self.model.add_callback("on_fit_epoch_end", on_fit_epoch_end)

        # 执行训练
        try:
            results = self.model.train(
                data=str(data_yaml),
                epochs=self.config.epochs,
                batch=batch_size,
                imgsz=self.config.image_size,
                device=device,
                patience=self.config.patience,
                workers=self.config.workers,
                optimizer=self.config.optimizer,
                lr0=self.config.lr0,
                box=self.config.box,
                cls=self.config.cls,
                dfl=self.config.dfl,
                scale=self.config.scale,
                project=str(output_dir),
                name="train",
                exist_ok=True,
                verbose=True,
                cache=self.config.cache,  # 数据缓存模式
            )

            best_model = output_dir / "train" / "weights" / "best.pt"
            if best_model.exists():
                self.report_progress(1, 1, "Training completed")
                return best_model
            return None

        except KeyboardInterrupt:
            self.report_progress(0, 1, "Training cancelled")
            return None
        except Exception as e:
            # 记录完整异常信息到日志
            import traceback
            error_details = f"Training failed: {str(e)}\n{traceback.format_exc()}"
            self.report_progress(0, 1, error_details)
            logger.error(f"Training exception: {error_details}")
            raise
