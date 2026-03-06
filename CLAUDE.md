# CLAUDE.md

## Project Overview

**AutoLabeler** - Desktop intelligent annotation tool for computer vision.

**Workflow**: Scan → Sample → Manual Label → Train → Infer → Restore → (optional) Convert to VOC

**Core Value**:
- Only requires manual labeling of 10-20% of samples
- Model automatically labels remaining images
- Standardized workflow reduces errors

---

## Tech Stack

| Category | Technology |
|----------|------------|
| Language | Python 3.8+ (conda managed) |
| GUI | PySide6 >= 6.5.0, PySide6-Fluent-Widgets >= 1.4.0 |
| Deep Learning | YOLOv8 (ultralytics) >= 8.3.236, PyTorch >= 2.0.0 |
| Image Processing | OpenCV >= 4.7.0, Pillow >= 9.0.0 |
| Supporting | PyYAML, tqdm, pytest, black |

---

## Setup & Installation

```bash
# 1. Create conda environment
conda create -n yolo_new python=3.11
conda activate yolo_new

# 2. Install dependencies (check first, then install)
pip show pyinstaller || pip install pyinstaller
pip install -r requirements.txt

# 3. Verify installation
python main.py     # Launch GUI
pytest tests/ -v   # Run all tests

# 4. 开发要求
说话前叫一声“睿少”，如果使用claude code 插件 superpowers 的某个技能进行开发，告知用户在使用什么技能。
```

---

## Project Structure

```
auto_yolo_label/
├── core/                    # Core business logic
│   ├── scanner.py          # Scan site folders
│   ├── sampler.py          # Sample images
│   ├── trainer.py          # YOLO training
│   ├── inferencer.py       # Batch inference
│   ├── restorer.py         # Restore labels
│   ├── converter.py        # YOLO txt ↔ VOC xml
│   ├── base.py             # Abstract base classes
│   └── conversion_rule.py  # Custom class mapping
├── utils/                   # Utilities
│   ├── mapping_manager.py  # Thread-safe mapping.json
│   ├── path_encoder.py     # Encode/decode paths
│   ├── device.py           # GPU/CPU auto-detection
│   ├── exceptions.py       # Custom exceptions
│   └── image_utils.py      # Image processing
├── gui/                     # PySide6 GUI layer
│   ├── pages/              # Page widgets
│   ├── workers/            # QThread workers
│   └── widgets/            # Reusable components
├── tests/                   # Unit tests (~124 tests)
├── docs/                    # Documentation
│   ├── user/               # User guides
│   ├── dev/                # Developer docs
│   └── guides/             # Technical guides
└── config/                  # Configuration
```

---

## Architecture

**3-Tier Architecture**:

| Layer | Components | Location |
|-------|------------|----------|
| Presentation | PySide6 GUI, Pages, QThread Workers | `gui/` |
| Business Logic | Scanner, Sampler, Trainer, Inferencer, Restorer, Converter | `core/` |
| Data | MappingManager, PathEncoder, Device | `utils/` |

**Data Flow**: Scan → Sample → (Manual Label) → Train → Infer → Restore → (Optional: Convert)

---

## Core Principles

### 1. Package Management
```bash
# Always check before installing
pip show <package_name> || pip install <package_name>
```

### 2. Thread Safety
- `MappingManager` uses dual locking (`RLock` + file lock)
- **Never access `data.images` directly** - always use manager methods

### 3. Path Encoding
```
Original:  AS_CV_PI_P/H4A238FDF04/IMG_001.jpg
Encoded:   AS_CV_PI_P__H4A238FDF04__IMG_001.jpg
```
- Use `PathEncoder.encode()` / `decode()` for file operations
- Query `MappingManager.get_image_info()` for original format

### 4. Device Auto-Detection
```python
device: str = "auto"    # Auto-detect GPU/CPU
batch_size: int = -1    # Auto-calculate based on device
```

### 5. Testing Strategy
- **Targeted tests**: Only test modified modules
- **Example**: Modified `inferencer.py` → `pytest tests/test_inferencer.py -v`
- **Full suite**: Only before releases

---

## Common Commands

```bash
# Development
mamba.exe shell hook -s powershell | Out-String | Invoke-Expression
mamba activate yolo_new
D:/mniforge3/envs/yolo_new/python.exe main.py              # Run application
black .                      # Format code

# Testing (targeted)
pytest tests/test_scanner.py -v
pytest tests/test_sampler.py -v
pytest tests/test_inferencer.py -v

# Build
D:/mniforge3/envs/yolo_new/python.exe build.py             # Create dist/AutoLabeler.exe
```

---

## Mapping Data Structure

```json
{
  "images": {
    "Code__Product__Filename.jpg": {
      "original_relative": "Code/Product/Filename.jpg",
      "code": "Code",
      "product": "Product",
      "format": ".jpg",
      "sampled": false,
      "inferred": false,
      "restored": false
    }
  }
}
```

---

## Error Handling

**Custom Exceptions**: See `utils/exceptions.py`

**Common Issues**:
- **Windows Console**: Use ASCII-only for Chinese text in console
- **Small Object Detection**: Lower loss gains (box=2.0, cls=0.3), increase image_size to 1280
- **Inference Re-runs**: Results in timestamped dirs, inference does NOT mark `inferred=True`

---

## Build & Deployment

```bash
# Prerequisites
pip show pyinstaller || pip install pyinstaller

# Build
D:/mniforge3/envs/yolo_new/python.exe build.py

# Output
dist/AutoLabeler.exe  # Single executable, Windows 10+ compatible
```

---

## Quick References

| Resource | Path |
|----------|------|
| Product Requirements | `docs/dev/requirement.md` |
| Technical Spec | `docs/dev/jishukaifawendang.md` |
| Current Progress | `docs/dev/CURRENT_STATE.md` |
| User Guide | `docs/user/USER_GUIDE.md` |
| Technical Guides | `docs/guides/` |

---

## Feature History

### 2025-01-21
- Homepage quick actions (开始扫描, 使用文档 buttons)
- Navigation API: `navigationInterface.setCurrentItem(page_name)`
- Restore function improvements for inference mode

### 2025-01-14
- Pre-labeled priority sampling (XML/TXT detection)
- Inference result separation (timestamped directories)
- `ImageInfo.label_source`: `"none"` | `"pre_existing_xml"` | `"pre_existing_txt"`

### 2025-03-05
- Empty prediction now creates empty `.txt` files (for LabelImg compatibility)
- Label Inspector page for viewing inference results
- LabelImg integration with auto-copy classes.txt
- Inference result browser with Code/Product tree structure

### 2026-03-06
- External LabelImg environment support (avoid package conflicts with yolo_new)
- `LabelImgConfig` class for configuration management (project > global priority)
- GUI configuration dialog for selecting external Python interpreter
- Configuration stored in `~/.autolabeler/labelimg.json`
