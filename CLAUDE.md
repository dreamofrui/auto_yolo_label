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

**Core Technologies**:
- **Python**: 3.8+ (managed via conda)
- **GUI Framework**: PySide6 (Qt for Python) >= 6.5.0
- **UI Components**: PySide6-Fluent-Widgets >= 1.4.0
- **Deep Learning**: YOLOv8 (ultralytics) >= 8.3.236, PyTorch >= 2.0.0, TorchVision >= 0.15.0
- **Image Processing**: OpenCV >= 4.7.0, Pillow >= 9.0.0

**Supporting Libraries**:
- **Configuration**: PyYAML >= 6.0
- **Progress Tracking**: tqdm >= 4.65.0
- **Testing**: pytest >= 7.0.0
- **Code Quality**: black >= 23.0.0

---

## Setup & Installation

### Prerequisites
- **Conda**: Miniforge3 or Anaconda
- **Python**: 3.8+ (managed via conda)
- **GPU** (optional): CUDA-compatible for faster training/inference

### Initial Setup

1. **Create conda environment**
   ```bash
   cona create -n yolo python=3.10
   conda activate yolo
   ```

2. **Install dependencies**
   ```bash
   # Check and install packages (遵循重要原则：先检查后安装)
   pip show pyinstaller || pip install pyinstaller
   pip install -r requirements.txt
   ```

3. **Verify installation**
   ```bash
   python main.py     # Should launch GUI
   pytest tests/ -v   # Run all tests (115 tests)
   ```

---

## Development Environment

**Python**: `D:\miniforge3\envs\yolo\python.exe`

```bash
# Activate environment
conda activate yolo

# Check installed packages first
pip show <package_name>

# Install packages (先检查是否已安装，未安装再安装)
pip show pyinstaller || pip install pyinstaller

# Run tests
pytest tests/test_scanner.py -v
pytest tests/test_sampler.py -v

# Format code
black .

# Run application
python main.py
```

**重要原则**：安装任何包或库之前，先使用 `pip show <package_name>` 检查是否已安装，未安装时再执行安装。

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
│   └── converter.py        # YOLO txt → VOC xml
├── utils/                   # Utilities
│   ├── path_encoder.py     # Encode/decode paths with __ separator
│   ├── mapping_manager.py  # Thread-safe mapping.json management
│   ├── device.py           # GPU/CPU auto-detection
│   └── exceptions.py       # Custom exceptions
├── gui/                     # PySide6 GUI layer
│   ├── pages/              # Page widgets
│   └── workers/            # QThread workers
├── docs/                    # Documentation (organized)
│   ├── user/               # User guides
│   ├── dev/                # Developer docs
│   └── guides/             # Technical guides
├── tests/                   # Unit tests (9 core tests)
└── config/                  # Configuration
```

---

## File Structure

### Core Modules (`core/`)
- **scanner.py**: Site structure discovery and mapping initialization
- **sampler.py**: Image sampling with pre-label detection (XML/TXT)
- **trainer.py**: YOLOv8 training with auto device/batch detection
- **inferencer.py**: Batch inference with timestamped result storage
- **restorer.py**: Applies inference results to original structure
- **converter.py**: Coordinate conversion (YOLO ↔ VOC)
- **base.py**: Abstract base classes for core components
- **conversion_rule.py**: Custom class mapping rules

### Utilities (`utils/`)
- **mapping_manager.py**: Thread-safe mapping.json management with file locking
- **path_encoder.py**: Encodes paths with `__` separator for special chars
- **device.py**: GPU/CPU auto-detection and batch size calculation
- **exceptions.py**: Custom exception classes
- **image_utils.py**: Image processing utilities
- **site_detector.py**: Site structure detection

### GUI Layer (`gui/`)
- **pages/**: Main interface pages (Home, Scan, Sample, Train, Infer, Restore, Convert)
- **workers/**: QThread workers for background processing
- **widgets/**: Reusable UI components (docs dialog)
- **app.py**: Application entry point
- **main_window.py**: Main window layout

### Configuration (`config/`)
- YOLO model configurations
- Training hyperparameters
- Application settings

### Tests (`tests/`)
- Core unit tests (9 test files, ~124 tests)
- Tests: scanner, sampler, trainer, inferencer, restorer, converter, mapping_manager, path_encoder, device

---

## Architecture

AutoLabeler follows a **3-tier architecture**:

### 1. Presentation Layer (GUI)
- **PySide6-based desktop interface**
- Pages: Home, Scan, Sample, Train, Infer, Restore, Convert
- Workers: QThread-based background processing
- Location: `gui/` directory

### 2. Business Logic Layer (Core)
- **Scanner**: Discovers and catalogs site structure
- **Sampler**: Stratified sampling with pre-label detection
- **Trainer**: YOLOv8 model training
- **Inferencer**: Batch inference with result separation
- **Restorer**: Applies inference results to original structure
- **Converter**: YOLO TXT ↔ VOC XML conversion
- Location: `core/` directory

### 3. Data Layer (Utils)
- **MappingManager**: Thread-safe JSON database
- **PathEncoder**: Handles special characters in paths
- **Device**: Auto-detects GPU/CPU availability
- Location: `utils/` directory

**Data Flow**: Scan → Sample → (Manual Label) → Train → Infer → Restore → (Optional: Convert)

---

## Core Principles

### 1. Package Management
**Always check before installing**: Use `pip show <package_name>` before `pip install` to avoid redundant installations.

### 2. Thread Safety
- **MappingManager**: Uses dual locking (`threading.RLock()` + file lock)
- **Never access `data.images` directly** - always use manager methods
- Cross-platform file locking for concurrent access

### 3. Path Encoding
- Special characters in paths encoded with `__` separator
- Always use `PathEncoder.encode()` / `decode()` for file operations
- Query `MappingManager.get_image_info()` for original `format` field

### 4. Device Auto-Detection
```python
device: str = "auto"    # Auto-detect GPU/CPU
batch_size: int = -1    # Auto-calculate based on device
```

### 5. Testing Strategy
- **Run targeted tests**: Only test modified modules
- **Example**: Modified `inferencer.py` → run `test_inferencer.py`
- **Full suite**: Only before releases

---

## Critical Design Patterns

### Path Encoding
```
Original:  AS_CV_PI_P/H4A238FDF04/IMG_001.jpg
Encoded:   AS_CV_PI_P__H4A238FDF04__IMG_001.jpg
```
**Always query** `MappingManager.get_image_info()` for original `format` field.

### Thread Safety
`MappingManager` uses dual locking: `threading.RLock()` + cross-platform file lock.
**Always use manager methods**, never direct `data.images` access.

### Device Auto-Detection
```python
device: str = "auto"    # Triggers auto-detection
batch_size: int = -1    # -1 means auto-calculate
```

### Mapping Data Structure
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

## Development Workflow

1. **Read docs/dev/requirement.md** for product requirements
2. **Check docs/dev/jishukaifawendang.md** for technical design
3. **Modify code** and test functionality
4. **Update docs/dev/CURRENT_STATE.md** when completing features

---

## Testing Summary

| Module | Tests | Key Areas |
|--------|-------|-----------|
| PathEncoder | 11 | Encode/decode, special chars |
| MappingManager | 14 | Thread safety, file lock |
| Scanner | 15 | Hidden dir skip, statistics |
| Sampler | 22 | Priority sampling, train/val split |
| Restorer | 11 | Label restoration, formats |
| Trainer | 12 | Config, device/batch auto |
| Inferencer | 12 | Batch inference, progress |
| Converter | 19 | Coordinate precision, XML validity |
| Device | 5 | GPU/CPU detection |

**Total**: ~124 tests (9 core modules)

---

## Testing Commands

```bash
# Run specific module tests (推荐：只验证涉及的功能)
pytest tests/test_scanner.py -v
pytest tests/test_sampler.py -v
pytest tests/test_mapping_manager.py -v

# Run all tests (仅在最终验证时使用)
pytest tests/ -v

# Run tests with coverage
pytest tests/ --cov=. --cov-report=html
```

**测试原则**：修改功能后只运行相关的测试用例，不要每次都运行所有测试套件。例如：
- 修改 `mapping_manager.py` → 只运行 `test_mapping_manager.py`
- 修改 `inferencer.py` → 只运行 `test_inferencer.py`
- 修改多个模块 → 运行相关模块的测试（如 `pytest tests/test_mapping_manager.py tests/test_inferencer.py -v`）

---

## Error Handling

### Custom Exceptions (`utils/exceptions.py`)
- Define project-specific exception classes
- Provide clear error messages for common failure scenarios

### Common Issues

**Windows Console Encoding**:
- Use ASCII-only output for Chinese text in console
- GUI handles Unicode properly

**Small Object Detection**:
- Lower `box` and `cls` loss gains (2.0, 0.3)
- Increase `image_size` to 1280
- See `docs/guides/SMALL_OBJECT_DETECTION.md` for details

**Inference Re-runs**:
- Inference results saved to timestamped directories
- User selects which run to restore
- Inference does NOT mark `inferred=True` (allows re-inference)
- Restorer marks `inferred=True` when applying results

---

## Build & Deployment

### Prerequisites
- PyInstaller installed: `pip show pyinstaller || pip install pyinstaller`
- All dependencies from requirements.txt

### Build Executable
```bash
# Build with PyInstaller
python build.py

# Output location
dist/AutoLabeler.exe
```

### Build Configuration
- **Spec file**: `build_exe.spec`
- **Build script**: `build.py`
- **Icon**: `icon.ico`
- **Mode**: No console window (NullWriter handles stdout/stderr)

### Distribution
- Single executable: `dist/AutoLabeler.exe`
- No external dependencies required (bundled)
- Windows 10+ compatible

---

## Quick References

- Product requirements: `docs/dev/requirement.md`
- Technical spec: `docs/dev/jishukaifawendang.md`
- **Current progress**: `docs/dev/CURRENT_STATE.md`
- User guide: `docs/user/USER_GUIDE.md`
- Technical guides: `docs/guides/`

---

## Feature Enhancements (2025-01-14)

**Pre-labeled Priority Sampling**:
- Sampler detects XML/TXT labels in product folders
- XML auto-converts to YOLO TXT during sampling
- Empty label files deleted automatically
- `ImageInfo.label_source`: `"none"` | `"pre_existing_xml"` | `"pre_existing_txt"`

**Inference Result Separation**:
- Results saved to `.autolabeler/inference_results/run_YYYYMMDD_HHMMSS/`
- Preserves original structure: `run_xxx/CodeA/ProductA/image.txt`
- Generates `inference_config.json` for each run
- All history preserved for comparison
- **Inference does NOT mark `inferred=True`** (allows re-inference)
- **Restorer marks `inferred=True`** when applying results

---

## Feature Enhancements (2025-01-21)

**Homepage Quick Actions**:
- "开始扫描" button: Direct navigation to Scan page
- "使用文档" button: Opens USER_GUIDE.md in a styled dialog
- White background with black text for better readability

**Navigation API**:
- Use `navigationInterface.setCurrentItem(page_name)` to navigate
- Page names: "首页", "扫描", "抽样", "训练", "推理", "还原", "转换"

**Restore Function Improvements**:
- Fixed inference result combo box data binding
- Added ready state check for both Database and Inference modes
- Skip already restored files (check `restored` flag and file existence)

