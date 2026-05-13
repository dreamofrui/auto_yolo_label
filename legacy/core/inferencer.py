"""
AutoLabeler 推理模块
使用训练好的模型标注剩余图片
支持推理结果分区存储，便于追溯和对比
"""

from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass
from datetime import datetime
import json
import shutil
from .base import BaseModule
from utils.mapping_manager import MappingManager
from utils.exceptions import InferenceError


@dataclass
class InferenceConfig:
    """推理配置"""
    confidence: float = 0.25
    iou: float = 0.7
    batch_size: int = -1        # -1 for auto-detect
    device: str = "auto"        # auto/cpu/0/mps
    save_to_separate_dir: bool = True  # 是否保存到独立目录


class Inferencer(BaseModule):
    """
    推理模块
    使用训练好的模型标注剩余图片
    推理结果保存到独立目录，便于追溯和对比
    """

    def __init__(self, config: InferenceConfig = None):
        super().__init__()
        self.config = config or InferenceConfig()
        self._inference_output_dir: Optional[Path] = None
        self._inference_config_path: Optional[Path] = None

    def _resolve_device(self) -> str:
        """解析设备配置"""
        from utils.device import get_optimal_device

        if self.config.device == "auto":
            return get_optimal_device()
        return self.config.device

    def _resolve_batch_size(self, device: str) -> int:
        """解析 batch size 配置"""
        from utils.device import get_optimal_batch_size

        if self.config.batch_size == -1:
            return get_optimal_batch_size(device)
        return self.config.batch_size

    def infer(
        self,
        model_path: Path,
        mapping: MappingManager,
        site_folder: Path,
        output_base_dir: Optional[Path] = None
    ) -> int:
        """
        执行推理

        Args:
            model_path: 模型文件路径
            mapping: 映射管理器
            site_folder: 站点文件夹
            output_base_dir: 推理结果基础目录，默认为 .autolabeler/inference_results

        Returns:
            成功处理的图片数量
        """
        from ultralytics import YOLO

        self.reset()

        # 解析设备和批次大小
        device = self._resolve_device()
        batch_size = self._resolve_batch_size(device)

        # 设置推理输出目录
        if self.config.save_to_separate_dir:
            if output_base_dir is None:
                output_base_dir = site_folder / ".autolabeler" / "inference_results"

            # 创建以时间戳命名的子目录
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self._inference_output_dir = output_base_dir / f"run_{timestamp}"
            self._inference_output_dir.mkdir(parents=True, exist_ok=True)

            self._inference_config_path = self._inference_output_dir / "inference_config.json"
        else:
            # 兼容旧逻辑：直接保存到原位置
            self._inference_output_dir = None

        # 加载模型并移动到指定设备
        model = YOLO(str(model_path))
        model.to(device)

        # 获取待推理的图片（未被抽样且未推理）
        pending_images = mapping.get_pending_inference_images()
        pending_total = len(pending_images)

        if pending_total == 0:
            self.report_progress(1, 1, "No images to infer")
            return 0

        # 构建图片路径列表
        image_paths = []
        encoded_names = []
        missing_count = 0
        for img in pending_images:
            path = site_folder / img["original_relative"]
            if path.exists():
                image_paths.append(str(path))
                encoded_names.append(img["encoded_name"])
            else:
                missing_count += 1

        # 修正 total 为实际可处理的图片数
        total = len(image_paths)

        # 报告状态
        if total == 0:
            self.report_progress(1, 1, "没有找到可处理的图片（所有图片路径不存在）")
            return 0

        if missing_count > 0:
            self.report_progress(0, total, f"找到 {total} 张图片，{missing_count} 张路径不存在")

        # 统计变量
        processed = 0
        predicted_count = 0
        empty_count = 0

        # 批量推理
        for i in range(0, len(image_paths), batch_size):
            if self.is_cancelled:
                break

            batch_paths = image_paths[i:i+batch_size]
            batch_names = encoded_names[i:i+batch_size]

            # 执行推理
            results = model.predict(
                source=batch_paths,
                conf=self.config.confidence,
                iou=self.config.iou,
                device=device,
                save=False,
                verbose=False
            )

            # 保存标注结果
            for j, result in enumerate(results):
                img_info = mapping.get_image_info(batch_names[j])
                if not img_info:
                    continue

                # 保存标注
                has_prediction = self._save_yolo_txt(
                    result, batch_names[j], img_info, site_folder
                )

                # 统计
                if has_prediction:
                    predicted_count += 1
                else:
                    empty_count += 1

                # 更新映射
                mapping.mark_inferred(batch_names[j])

            processed += len(batch_paths)
            self.report_progress(
                processed, total,
                f"Inference: {processed}/{total}"
            )

        # 保存推理配置
        if self.config.save_to_separate_dir and self._inference_config_path:
            self._save_inference_config(
                model_path, device, batch_size,
                total, predicted_count, empty_count
            )

        mapping.save()
        return processed

    def _save_yolo_txt(
        self,
        result,
        encoded_name: str,
        img_info: dict,
        site_folder: Path
    ) -> bool:
        """
        保存 YOLO 格式标注文件

        Returns:
            是否有预测结果（True=有预测，False=空预测）
        """
        boxes = result.boxes

        # 构建目标路径
        if self.config.save_to_separate_dir and self._inference_output_dir:
            # 保存到独立目录，保持原目录结构
            code = img_info["code"]
            product = img_info["product"]
            original_name = img_info["original_name"]

            dst_dir = self._inference_output_dir / code / product
            dst_dir.mkdir(parents=True, exist_ok=True)

            txt_name = Path(original_name).stem + ".txt"
            txt_path = dst_dir / txt_name
        else:
            # 保存到原位置（兼容旧逻辑）
            img_path = site_folder / img_info["original_relative"]
            txt_path = img_path.with_suffix('.txt')

        # 处理空预测 - 创建空文件
        if boxes is None or len(boxes) == 0:
            # 确保目录存在
            txt_path.parent.mkdir(parents=True, exist_ok=True)
            # 创建空的 txt 文件
            txt_path.touch()
            return False

        # 写入标注
        lines = []
        for box in boxes:
            cls_id = int(box.cls[0])
            # 获取归一化的中心点坐标和宽高
            xywhn = box.xywhn[0].tolist()  # [x_center, y_center, width, height]
            line = f"{cls_id} {xywhn[0]:.6f} {xywhn[1]:.6f} {xywhn[2]:.6f} {xywhn[3]:.6f}"
            lines.append(line)

        # 确保目录存在
        txt_path.parent.mkdir(parents=True, exist_ok=True)

        with open(txt_path, 'w') as f:
            f.write('\n'.join(lines))

        return True

    def _save_inference_config(
        self,
        model_path: Path,
        device: str,
        batch_size: int,
        total: int,
        predicted: int,
        empty: int
    ) -> None:
        """保存推理配置到 JSON 文件"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        run_id = self._inference_output_dir.name

        config_data = {
            "run_id": run_id,
            "timestamp": timestamp,
            "model_path": str(model_path),
            "confidence": self.config.confidence,
            "iou": self.config.iou,
            "device": device,
            "batch_size": batch_size,
            "image_count": total,
            "predicted_count": predicted,
            "empty_prediction_count": empty
        }

        with open(self._inference_config_path, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=2, ensure_ascii=False)

    @property
    def inference_output_dir(self) -> Optional[Path]:
        """获取本次推理的输出目录"""
        return self._inference_output_dir

    def get_inference_history(self, base_dir: Path) -> List[dict]:
        """
        获取推理历史列表

        Args:
            base_dir: 推理结果基础目录（.autolabeler/inference_results）

        Returns:
            推理历史列表，每个元素包含 run_id, timestamp, config 等信息
        """
        history = []

        if not base_dir.exists():
            return history

        for run_dir in sorted(base_dir.glob("run_*"), reverse=True):
            config_path = run_dir / "inference_config.json"
            if config_path.exists():
                try:
                    with open(config_path, 'r', encoding='utf-8') as f:
                        config = json.load(f)
                    history.append({
                        "run_dir": run_dir,
                        "config": config
                    })
                except Exception:
                    # 跳过损坏的配置文件
                    continue

        return history
