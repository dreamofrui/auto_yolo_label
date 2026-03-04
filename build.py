"""
AutoLabeler 一键打包脚本
将 AutoLabeler 打包成 Windows 可执行文件

使用方法:
    python build.py

打包完成后，可执行文件位于: dist/AutoLabeler/AutoLabeler.exe
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path


def print_step(message: str):
    """打印步骤信息"""
    print(f"\n{'='*60}")
    print(f"  {message}")
    print(f"{'='*60}")


def print_info(message: str):
    """打印信息"""
    print(f"[INFO] {message}")


def print_success(message: str):
    """打印成功信息"""
    print(f"[SUCCESS] {message}")


def print_error(message: str):
    """打印错误信息"""
    print(f"[ERROR] {message}", file=sys.stderr)


def check_environment():
    """检查打包环境"""
    print_step("Step 1: 检查打包环境")

    # 检查 PyInstaller（使用模块方式）
    try:
        result = subprocess.run(
            [sys.executable, "-m", "PyInstaller", "--version"],
            capture_output=True,
            text=True,
            check=True
        )
        print_success(f"PyInstaller 版本: {result.stdout.strip()}")
    except FileNotFoundError:
        print_error("未找到 PyInstaller，请先安装:")
        print_error("  pip install pyinstaller")
        return False
    except subprocess.CalledProcessError:
        print_error("PyInstaller 检查失败")
        return False

    # 检查主文件
    if not Path("main.py").exists():
        print_error("未找到 main.py 文件")
        return False

    # 检查配置目录
    if not Path("config").exists():
        print_error("未找到 config 目录")
        return False

    print_success("环境检查通过")
    return True


def clean_build_dirs():
    """清理之前的打包输出"""
    print_step("Step 2: 清理旧的打包文件")

    dirs_to_remove = ['build', 'dist']

    for dir_name in dirs_to_remove:
        dir_path = Path(dir_name)
        if dir_path.exists():
            print_info(f"删除目录: {dir_name}")
            shutil.rmtree(dir_path)

    print_success("清理完成")


def build_exe():
    """执行打包"""
    print_step("Step 3: 开始打包")

    spec_file = Path("build_exe.spec")

    if not spec_file.exists():
        print_error("未找到 build_exe.spec 配置文件")
        return False

    print_info("使用配置文件: build_exe.spec")
    print_info("这可能需要几分钟，请耐心等待...")
    print_info("提示: 首次打包会下载一些依赖文件，可能需要较长时间\n")

    try:
        # 使用 Python 模块方式执行 PyInstaller 打包
        result = subprocess.run(
            [sys.executable, "-m", "PyInstaller", "--clean", str(spec_file)],
            check=True,
            capture_output=False,
        )

        print_success("打包完成")
        return True

    except subprocess.CalledProcessError as e:
        print_error(f"打包失败: {e}")
        return False
    except FileNotFoundError:
        print_error("未找到 pyinstaller")
        return False


def verify_build():
    """验证打包结果"""
    print_step("Step 4: 验证打包结果")

    exe_path = Path("dist/AutoLabeler/AutoLabeler.exe")

    if exe_path.exists():
        file_size = exe_path.stat().st_size / (1024 * 1024)  # MB
        print_success(f"可执行文件已生成: {exe_path}")
        print_info(f"文件大小: {file_size:.2f} MB")

        # 检查配置文件是否复制
        config_dir = Path("dist/AutoLabeler/config")
        if config_dir.exists():
            print_success("配置文件已正确打包")

        return True
    else:
        print_error("可执行文件未生成")
        return False


def print_summary():
    """打印打包总结"""
    print_step("打包完成")

    print("\n" + "─"*60)
    print("  可执行文件位置")
    print("─"*60)
    print(f"\n  {Path.cwd() / 'dist' / 'AutoLabeler' / 'AutoLabeler.exe'}")
    print("\n─"*60)
    print("  使用说明")
    print("─"*60)
    print("""
  1. 整个 dist/AutoLabeler 文件夹可以分发
  2. 双击 AutoLabeler.exe 启动程序
  3. 首次运行可能需要几分钟（初始化 YOLO）
  4. 建议将整个文件夹压缩后分享

  注意事项:
  - 不要只复制 .exe 文件，需要整个文件夹
  - 确保目标机器有足够的磁盘空间（约 500MB-2GB）
  - Windows 10/11 系统可直接运行
    """)


def main():
    """主函数"""
    print("""
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║           AutoLabeler 智能标注工具 - 打包脚本              ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
    """)

    # 检查环境
    if not check_environment():
        print_error("环境检查失败，退出")
        sys.exit(1)

    # 清理旧文件
    clean_build_dirs()

    # 执行打包
    if not build_exe():
        print_error("打包失败，退出")
        sys.exit(1)

    # 验证结果
    if not verify_build():
        print_error("验证失败，退出")
        sys.exit(1)

    # 打印总结
    print_summary()


if __name__ == "__main__":
    main()
