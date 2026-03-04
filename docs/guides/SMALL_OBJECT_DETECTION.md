# 小目标检测配置指南

## 问题背景

YOLO 模型在训练时会过滤掉太小的标注框。这是因为：
- YOLO 在数据加载阶段创建 `.cache` 文件
- 过滤阈值约为图像尺寸的 2%（640x640 图像约 13 像素）
- 小目标难以检测，容易在训练中被忽略

## 解决方案

### 方案 1: 增大训练图像尺寸（最有效）

将图像尺寸从 640 增加到 1280，使小目标相对变大：

```python
from core.trainer import Trainer, TrainConfig

config = TrainConfig(
    image_size=1280,  # 640 -> 1280
    epochs=50,
)
```

**优点**：简单直接，效果最明显
**缺点**：训练时间增加 2-4 倍，显存需求增加

### 方案 2: 使用小目标优化参数

```python
config = TrainConfig(
    # 小目标检测优化参数
    box=2.0,          # box loss gain (默认 7.5，小目标降低到 1.5-3.0)
    cls=0.3,          # cls loss gain (默认 0.5，保持或降低)
    dfl=1.5,          # distribution focal loss (默认 1.5)
    scale=0.5,        # 检测框缩放 (0.5 = 1/2 默认，更敏感)
)
```

**参数说明**：
- `box`: 降低 box loss 权重，防止小目标 loss 被大目标掩盖
- `cls`: 降低分类 loss 权重，更关注定位精度
- `scale`: 减小锚框尺寸，更适应小目标

### 方案 3: 修复过小的标注框

使用 `tools/fix_small_boxes.py` 将小于阈值的框放大：

```bash
cd tools

# 将小于 32px (0.05 @ 640px) 的框放大 3 倍
python fix_small_boxes.py ../database/labels/train 0.05 3.0
python fix_small_boxes.py ../database/labels/vals 0.05 3.0
```

### 方案 4: 增加训练轮次

小目标需要更多轮次才能收敛：

```python
config = TrainConfig(
    epochs=100,  # 小目标检测建议 50-150 轮
    patience=50,
)
```

### 方案 5: 增加训练数据量

小目标检测需要更多样本：
- **最少**：每类 50 张图像
- **推荐**：每类 100-500 张图像
- **理想**：每类 1000+ 张图像

## 完整配置示例

### 配置 A: 保守方案（显存有限）

```python
config = TrainConfig(
    image_size=640,
    epochs=80,
    box=2.5,
    cls=0.5,
)
```

### 配置 B: 激进方案（最佳效果）

```python
config = TrainConfig(
    image_size=1280,
    epochs=120,
    box=2.0,
    cls=0.3,
    scale=0.5,
)
```

### 配置 C: 极小目标（< 16px）

```python
config = TrainConfig(
    image_size=1280,
    epochs=150,
    box=1.5,
    cls=0.3,
    dfl=1.0,
    scale=0.3,
)
```

## 诊断工具

### 检查标注框大小分布

```bash
cd tools
python debug_training_data.py ../database/data.yaml
```

详细说明见 [tools/README.md](tools/README.md)

## 训练建议

1. **先修复小标注框**：确保最小框 >= 32px
2. **从配置 A 开始**：验证训练正常
3. **逐步增加参数**：观察 mAP50 变化
4. **监控训练指标**：box loss 应该稳定下降
5. **验证预测结果**：即使 mAP50=0，模型也应该产生预测（conf=0.001）

## 常见问题

### Q: mAP50 仍然是 0？
A: 检查以下几点：
- 标注框是否 >= 32px
- 训练数据量是否 >= 每类 50 张
- 训练轮次是否 >= 50
- 使用 `conf=0.001` 检查是否有预测

### Q: 训练很慢？
A: 可以尝试：
- 降低 `image_size` 到 640
- 降低 `batch_size` 到 8 或 4
- 使用更小的模型 (yolo11n.pt)

### Q: 显存不足？
A: 可以尝试：
- 降低 `image_size` 到 640 或 512
- 降低 `batch_size`
- 使用 CPU 训练（慢但稳定）

## 相关文件

- `core/trainer.py` - 训练模块（已更新小目标参数）
- `tools/fix_small_boxes.py` - 标注框修复工具
- `tools/debug_training_data.py` - 数据诊断工具
- `tools/README.md` - 工具集使用说明
- `tests/test_training_integration.py` - 训练集成测试
- `tests/test_small_object_config.py` - 配置对比测试
