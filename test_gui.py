"""
简单的 GUI 测试脚本
验证基本 GUI 功能是否正常
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

# 启用高 DPI 缩放
QApplication.setHighDpiScaleFactorRoundingPolicy(
    Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
)
QApplication.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling)
QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps)

# 测试导入
print("[1/4] Testing imports...")
try:
    from gui.app import AutoLabelerApp
    print("  - AutoLabelerApp: OK")
except Exception as e:
    print(f"  - AutoLabelerApp: FAILED - {e}")
    sys.exit(1)

try:
    from gui.main_window import MainWindow
    print("  - MainWindow: OK")
except Exception as e:
    print(f"  - MainWindow: FAILED - {e}")
    sys.exit(1)

try:
    from gui.pages.home_page import HomePage
    print("  - HomePage: OK")
except Exception as e:
    print(f"  - HomePage: FAILED - {e}")
    sys.exit(1)

try:
    from gui.pages.scan_page import ScanPage
    print("  - ScanPage: OK")
except Exception as e:
    print(f"  - ScanPage: FAILED - {e}")
    sys.exit(1)

# 测试创建应用
print("[2/4] Creating application...")
try:
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    print("  - QApplication: OK")
except Exception as e:
    print(f"  - QApplication: FAILED - {e}")
    sys.exit(1)

# 测试创建主窗口
print("[3/4] Creating main window...")
try:
    window = MainWindow()
    print("  - MainWindow creation: OK")
    print("  - Pages added:", list(window.pages.keys()))
except Exception as e:
    print(f"  - MainWindow creation: FAILED - {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 显示窗口
print("[4/4] Testing window display...")
try:
    window.show()
    print("  - Window show: OK")
except Exception as e:
    print(f"  - Window show: FAILED - {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n=== All GUI tests passed! ===")
print("Close the window to exit...")

# 运行事件循环
sys.exit(app.exec())
