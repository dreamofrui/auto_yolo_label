# -*- mode: python ; coding: utf-8 -*-
"""
AutoLabeler PyInstaller 打包配置文件
用于将 AutoLabeler 打包成单个可执行文件

使用方法:
    pyinstaller build_exe.spec

或使用一键打包脚本:
    python build.py
"""

from PyInstaller.utils.hooks import collect_data_files, collect_submodules
from pathlib import Path
import os

# 项目根目录 - 使用 spec 文件所在目录
# SPECPATH 是 .spec 文件所在的目录
project_root = Path(SPECPATH)

# 收集需要打包的数据文件
datas = []

# 添加 USER_GUIDE.md 文档
user_guide = project_root / 'USER_GUIDE.md'
if user_guide.exists():
    datas.append((str(user_guide), '.'))

# 添加配置目录（如果存在）
config_dir = project_root / 'config'
if config_dir.exists():
    # 收集 config 目录下的所有文件
    for item in config_dir.iterdir():
        if item.is_file():
            datas.append((str(item), 'config'))
        elif item.is_dir():
            datas.append((str(item), 'config/' + item.name))

# 安全收集数据文件（如果模块存在）
try:
    qfluentwidgets_data = collect_data_files('qfluentwidgets')
    if qfluentwidgets_data:
        datas.extend(qfluentwidgets_data)
except Exception:
    pass

try:
    ultralytics_data = collect_data_files('ultralytics')
    if ultralytics_data:
        datas.extend(ultralytics_data)
except Exception:
    pass

# 隐藏导入（PyInstaller 可能无法自动检测的模块）
hiddenimports = [
    # PySide6 相关
    'PySide6.QtCore',
    'PySide6.QtGui',
    'PySide6.QtWidgets',

    # QFluentWidgets 相关
    'qfluentwidgets',
    'qfluentwidgets.components',

    # 深度学习相关
    'ultralytics',
    'ultralytics.models',
    'ultralytics.models.yolo',
    'ultralytics.models.yolo.model',
    'ultralytics.models.yolo.classify',
    'ultralytics.models.yolo.classify.train',
    'ultralytics.models.yolo.classify.predict',
    'ultralytics.models.yolo.classify.val',
    'ultralytics.models.yolo.detect',
    'ultralytics.models.yolo.detect.train',
    'ultralytics.models.yolo.detect.predict',
    'ultralytics.models.yolo.detect.val',
    'ultralytics.nn',
    'ultralytics.nn.modules',
    'ultralytics.nn.tasks',
    'ultralytics.engine',
    'ultralytics.engine.trainer',
    'ultralytics.engine.predictor',
    'ultralytics.engine.validator',
    'ultralytics.engine.model',
    'ultralytics.utils',
    'ultralytics.utils.callbacks',
    'ultralytics.data.utils',
    'ultralytics.cfg',
    'torch',
    'torchvision',
    'cv2',

    # 图像处理
    'PIL',
    'PIL._tkinter_finder',

    # 配置文件
    'yaml',

    # 其他工具
    'tqdm',
    'numpy',
    'pandas',
]

# 安全收集子模块
try:
    qfluent_submodules = collect_submodules('qfluentwidgets')
    if qfluent_submodules:
        hiddenimports.extend(qfluent_submodules)
except Exception:
    pass

try:
    ultralytics_submodules = collect_submodules('ultralytics')
    if ultralytics_submodules:
        hiddenimports.extend(ultralytics_submodules)
except Exception:
    pass

# 二进制文件排除（减小体积）
excludes = [
    # 测试相关
    'pytest',
    'black',

    # Jupyter 相关（如果不需要）
    'IPython',
    'jupyter',

    # 不需要的 torch 组件（如果只用推理）
    # 'torch.distributed',
    # 'torch.testing',
]

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[str(project_root)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='AutoLabeler',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # 不显示控制台窗口
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(project_root / 'icon.ico'),  # 应用图标（绝对路径）
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='AutoLabeler',
)
