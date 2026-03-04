"""
AutoLabeler 智能标注工具
主程序入口

使用方法:
    python main.py
"""

import sys
from pathlib import Path


class NullWriter:
    """Null writer for PyInstaller noconsole mode

    在 PyInstaller 打包的无控制台模式下，sys.stdout 和 sys.stderr 会被设置为 None。
    这会导致 tqdm 等库在尝试写入时报错：'NoneType' object has no attribute 'write'。
    NullWriter 提供了一个安全的输出目标，接受但不处理任何输出。
    """
    def write(self, text):
        pass

    def flush(self):
        pass

    def isatty(self):
        return False


# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

# PyInstaller 无控制台模式：重定向 stdout/stderr
# 仅在打包后环境且输出流为 None 时才替换，避免干扰开发环境或其他重定向逻辑
if getattr(sys, 'frozen', False):
    if sys.stdout is None:
        sys.stdout = NullWriter()
    if sys.stderr is None:
        sys.stderr = NullWriter()


from gui.app import main


if __name__ == "__main__":
    main()
