"""
临时测试脚本：验证Qt对不支持CSS属性的处理行为

测试问题：
1. 当QSS样式块中包含 line-height（Qt不支持的属性）时，
   同一块中的 background-color 是否仍然生效？
2. Qt是"忽略单个属性"还是"丢弃整个样式块"？

注意：此测试需要Python 3.11和PySide6
"""

import sys
from pathlib import Path

# 检查Python版本
if sys.version_info < (3, 11) or sys.version_info >= (3, 12):
    print(f"[WARNING] 此测试需要Python 3.11，当前版本: {sys.version}")
    print("[WARNING] 测试可能无法运行，但会尝试继续...")

try:
    from PySide6.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout
    from PySide6.QtCore import Qt
except ImportError as e:
    print(f"[ERROR] 无法导入PySide6: {e}")
    print("[ERROR] 请在Python 3.11环境中运行: pip install PySide6")
    sys.exit(1)


def test_unsupported_property_behavior():
    """测试Qt对不支持属性的处理行为"""

    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    print("=" * 80)
    print("Qt QSS 不支持属性处理行为测试")
    print("=" * 80)

    # 测试1: 包含不支持的 line-height 属性
    print("\n[测试1] 包含 line-height 的样式块")
    print("-" * 80)

    widget1 = QWidget()
    widget1.setObjectName("testWidget1")
    widget1.setFixedSize(200, 100)

    # 应用包含 line-height 的样式
    stylesheet1 = """
    #testWidget1 {
        background-color: #FF0000;
        color: #FFFFFF;
        line-height: 1.5;
        padding: 10px;
    }
    """

    widget1.setStyleSheet(stylesheet1)

    # 检查背景色是否生效
    palette1 = widget1.palette()
    bg_color1 = palette1.color(widget1.backgroundRole())

    print("应用的样式表:")
    print(stylesheet1)
    print(f"\n实际背景色: {bg_color1.name()}")

    if bg_color1.name().upper() == "#FF0000":
        print("[结果] background-color 生效 - Qt忽略了不支持的 line-height")
    else:
        print(f"[结果] background-color 未生效 - 可能整个块被丢弃或样式未应用")
        print(f"       (期望: #FF0000, 实际: {bg_color1.name()})")

    # 测试2: 不包含不支持属性的对照组
    print("\n[测试2] 不包含不支持属性的对照组")
    print("-" * 80)

    widget2 = QWidget()
    widget2.setObjectName("testWidget2")
    widget2.setFixedSize(200, 100)

    stylesheet2 = """
    #testWidget2 {
        background-color: #00FF00;
        color: #FFFFFF;
        padding: 10px;
    }
    """

    widget2.setStyleSheet(stylesheet2)

    palette2 = widget2.palette()
    bg_color2 = palette2.color(widget2.backgroundRole())

    print("应用的样式表:")
    print(stylesheet2)
    print(f"\n实际背景色: {bg_color2.name()}")

    if bg_color2.name().upper() == "#00FF00":
        print("[结果] background-color 生效（对照组正常）")
    else:
        print(f"[结果] 意外：对照组也未生效 (期望: #00FF00, 实际: {bg_color2.name()})")

    # 测试3: 多个不支持属性
    print("\n[测试3] 包含多个不支持属性")
    print("-" * 80)

    widget3 = QWidget()
    widget3.setObjectName("testWidget3")
    widget3.setFixedSize(200, 100)

    stylesheet3 = """
    #testWidget3 {
        background-color: #0000FF;
        line-height: 1.5;
        cursor: not-allowed;
        box-shadow: 0px 2px 4px rgba(0,0,0,0.1);
        color: #FFFFFF;
    }
    """

    widget3.setStyleSheet(stylesheet3)

    palette3 = widget3.palette()
    bg_color3 = palette3.color(widget3.backgroundRole())

    print("应用的样式表:")
    print(stylesheet3)
    print(f"\n实际背景色: {bg_color3.name()}")

    if bg_color3.name().upper() == "#0000FF":
        print("[结果] background-color 生效 - Qt忽略了多个不支持的属性")
    else:
        print(f"[结果] background-color 未生效 (期望: #0000FF, 实际: {bg_color3.name()})")

    # 测试4: 测试全局 QWidget 规则
    print("\n[测试4] 全局 QWidget 样式规则")
    print("-" * 80)

    widget4 = QWidget()
    widget4.setFixedSize(200, 100)

    # 模拟真实的主题管理器样式
    stylesheet4 = """
    QWidget {
        background-color: #0A0E14;
        color: #E6EDF3;
        font-size: 14px;
    }
    """

    widget4.setStyleSheet(stylesheet4)

    palette4 = widget4.palette()
    bg_color4 = palette4.color(widget4.backgroundRole())

    print("应用的样式表:")
    print(stylesheet4)
    print(f"\n实际背景色: {bg_color4.name()}")

    if bg_color4.name().upper() == "#0A0E14":
        print("[结果] 全局 QWidget 背景色生效")
    else:
        print(f"[结果] 全局 QWidget 背景色未生效")
        print(f"       (期望: #0A0E14, 实际: {bg_color4.name()})")
        print("[警告] 这可能是问题的根源！")

    # 测试5: 全局规则 + ID选择器优先级
    print("\n[测试5] 全局规则 vs ID选择器优先级")
    print("-" * 80)

    widget5 = QWidget()
    widget5.setObjectName("loginCard")
    widget5.setFixedSize(200, 100)

    stylesheet5 = """
    QWidget {
        background-color: #0A0E14;
        color: #E6EDF3;
    }

    #loginCard {
        background-color: #1C2128;
        border: 1px solid #30363D;
    }
    """

    widget5.setStyleSheet(stylesheet5)

    palette5 = widget5.palette()
    bg_color5 = palette5.color(widget5.backgroundRole())

    print("应用的样式表:")
    print(stylesheet5)
    print(f"\n实际背景色: {bg_color5.name()}")

    if bg_color5.name().upper() == "#1C2128":
        print("[结果] ID选择器优先级高于全局规则（正确行为）")
    elif bg_color5.name().upper() == "#0A0E14":
        print("[结果] 全局规则生效（ID选择器未覆盖）")
    else:
        print(f"[结果] 意外的颜色值: {bg_color5.name()}")

    print("\n" + "=" * 80)
    print("测试总结")
    print("=" * 80)

    results = {
        "测试1 (line-height)": bg_color1.name().upper() == "#FF0000",
        "测试2 (对照组)": bg_color2.name().upper() == "#00FF00",
        "测试3 (多个不支持属性)": bg_color3.name().upper() == "#0000FF",
        "测试4 (全局QWidget)": bg_color4.name().upper() == "#0A0E14",
        "测试5 (优先级)": bg_color5.name().upper() == "#1C2128",
    }

    for test_name, passed in results.items():
        status = "[PASS]" if passed else "[FAIL]"
        print(f"{status} {test_name}")

    # 得出结论
    print("\n结论:")
    if results["测试1 (line-height)"]:
        print("- Qt会忽略不支持的CSS属性，但保留同一块中的其他有效属性")
        print("- line-height 不是导致背景色失效的原因")
    else:
        print("- Qt可能丢弃包含不支持属性的整个样式块")
        print("- line-height 可能是导致背景色失效的原因")

    if not results["测试4 (全局QWidget)"]:
        print("- 全局 QWidget 样式可能存在特殊行为")
        print("- 这可能是主题系统问题的关键")


if __name__ == "__main__":
    test_unsupported_property_behavior()
