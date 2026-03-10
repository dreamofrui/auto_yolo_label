# AutoLabeler 环境配置指南

本文档详细说明如何在全新环境中配置 AutoLabeler 项目。

---

## 目录

1. [前置要求](#1-前置要求)
2. [安装 Miniforge](#2-安装-miniforge)
3. [创建 Conda 环境](#3-创建-conda-环境)
4. [配置 LabelImg 环境](#4-配置-labelimg-环境)
5. [修改项目配置](#5-修改项目配置)
6. [验证安装](#6-验证安装)
7. [常见问题](#7-常见问题)

---

## 1. 前置要求

- Windows 10+
- 约 10GB 磁盘空间
- 网络连接（用于下载依赖）

---

## 2. 安装 Miniforge

### 2.1 下载

从 GitHub Releases 下载 Miniforge3：
```
https://github.com/conda-forge/miniforge/releases
```

选择 `Miniforge3-Windows-x86_64.exe` 下载。

### 2.2 安装

1. 运行安装程序
2. 选择安装路径（推荐：`D:\miniforge3`）
3. 建议选择 "Add Miniforge3 to my PATH"（可选）

---

## 3. 创建 Conda 环境

### 3.1 打开 PowerShell

### 3.2 获取 Mamba 权限（首次使用必须执行）

```powershell
mamba.exe shell hook -s powershell | Out-String | Invoke-Expression
```

### 3.3 创建项目运行环境

```powershell
# 创建 yolo_new 环境
mamba create -n yolo_new python=3.11 -y

# 激活环境
mamba activate yolo_new

# 安装项目依赖
cd D:\code\vscode_code\auto_yolo_label
pip install -r requirements.txt
```

---

## 4. 配置 LabelImg 环境

LabelImg 需要独立环境，避免与项目依赖冲突。

### 4.1 创建环境

```powershell
# 创建 labelimg 环境
mamba create -n labelimg python=3.10 -y

# 激活环境
mamba activate labelimg

# 安装 LabelImg 和 PyQt5
pip install labelImg PyQt5
```

### 4.2 验证安装

```powershell
# 测试 LabelImg 是否可用
labelImg --help
```

如果显示帮助信息，说明安装成功。

---

## 5. 修改项目配置

根据您的实际安装路径，修改以下文件：

### 5.1 修改 `utils/labelimg_launcher.py`

**文件位置**：`utils/labelimg_launcher.py`

**修改行号**：第 19 行

```python
# 修改前
CONDA_ROOT = Path("D:/miniforge3")

# 修改后（改成您的 miniforge 安装路径）
CONDA_ROOT = Path("您的miniforge安装路径")
```

**示例**：
```python
# 如果安装到 C:\miniforge3
CONDA_ROOT = Path("C:/miniforge3")

# 如果安装到 D:\miniforge3
CONDA_ROOT = Path("D:/miniforge3")
```

### 5.2 修改 `utils/labelimg_config.py`

**文件位置**：`utils/labelimg_config.py`

**修改行号**：第 21 行

```python
# 修改前
DEFAULT_PYTHON_PATH = "D:/miniforge3/envs/labelimg/python.exe"

# 修改后（改成您的 labelimg 环境 python 路径）
DEFAULT_PYTHON_PATH = "您的路径/miniforge3/envs/labelimg/python.exe"
```

### 5.3 配置文件说明

配置优先级（从高到低）：

| 优先级 | 配置位置 | 路径 |
|--------|----------|------|
| 1 (最高) | 项目配置 | `项目目录/config/labelimg.json` |
| 2 (中等) | 全局配置 | `%USERPROFILE%\.autolabeler\labelimg.json` |
| 3 (最低) | 代码默认值 | `utils/labelimg_config.py` 中的 `DEFAULT_PYTHON_PATH` |

#### 可选：创建全局配置文件

```powershell
# 创建配置目录
mkdir $env:USERPROFILE\.autolabeler

# 创建配置文件
notepad $env:USERPROFILE\.autolabeler\labelimg.json
```

**配置文件内容**：
```json
{
  "python_path": "D:/miniforge3/envs/labelimg/python.exe",
  "last_check": "2026-03-10T10:00:00",
  "is_valid": true
}
```

---

## 6. 验证安装

### 6.1 运行项目

```powershell
mamba activate yolo_new
cd D:\code\vscode_code\auto_yolo_label
python main.py
```

### 6.2 运行测试

```powershell
mamba activate yolo_new
cd D:\code\vscode_code\auto_yolo_label
pytest tests/ -v
```

### 6.3 测试 LabelImg 启动

1. 运行项目 `python main.py`
2. 进入"标签检查"页面
3. 选择一个推理结果
4. 点击"用 LabelImg 打开"
5. 确认 LabelImg 正确打开并加载图片

---

## 7. 常见问题

### Q1: LabelImg 打开但无法加载图片

**原因**：直接调用 `labelImg.exe` 缺少 conda 环境设置

**解决**：确保使用最新代码，新版本通过 `mamba run` 启动 LabelImg

### Q2: 找不到 mamba 命令

**解决**：
```powershell
mamba.exe shell hook -s powershell | Out-String | Invoke-Expression
```

### Q3: LabelImg 环境验证失败

**解决**：
```powershell
mamba activate labelimg
pip install --upgrade labelImg PyQt5
labelImg --help
```

### Q4: 运行时提示缺少依赖

**解决**：
```powershell
mamba activate yolo_new
pip install -r requirements.txt
```

### Q5: 如何打包为 exe

```powershell
mamba activate yolo_new
pip show pyinstaller || pip install pyinstaller
python build.py
```

输出：`dist/AutoLabeler.exe`

---

## 快速命令汇总

```powershell
# === 初始化 Mamba（每次新开终端需要执行） ===
mamba.exe shell hook -s powershell | Out-String | Invoke-Expression

# === 创建环境 ===
mamba create -n yolo_new python=3.11 -y
mamba create -n labelimg python=3.10 -y

# === 配置 yolo_new 环境 ===
mamba activate yolo_new
pip install -r requirements.txt

# === 配置 labelimg 环境 ===
mamba activate labelimg
pip install labelImg PyQt5

# === 运行项目 ===
mamba activate yolo_new
python main.py

# === 运行测试 ===
mamba activate yolo_new
pytest tests/ -v
```

---

## 需要修改的文件清单

| 文件 | 行号 | 修改内容 |
|------|------|----------|
| `utils/labelimg_launcher.py` | 19 | `CONDA_ROOT = Path("您的miniforge路径")` |
| `utils/labelimg_config.py` | 21 | `DEFAULT_PYTHON_PATH = "您的labelimg环境python路径"` |

---

*文档版本: 2026-03-10*
