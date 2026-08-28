# styles.qss 已废弃

**废弃日期**: 2026-08-26  
**原因**: 与动态主题系统 (theme_manager.py) 冲突

## 问题说明

`styles.qss` 包含 1368 行硬编码的样式，但从未被项目使用。真正生效的样式来自：
- ~~`workbench.py` 的 `_stylesheet()` 函数（已删除）~~
- `theme_manager.py` 动态生成的 QSS（现在使用）

保留此文件会导致：
- 颜色定义不一致
- 维护成本增加
- 主题切换功能失效

## 新的样式系统

样式现在由以下文件管理：

1. **`gui/design_system.py`** - 设计令牌（颜色、字体、间距等）
   - `DarkThemeColors` / `LightThemeColors` 类
   - 所有颜色常量的**唯一定义来源**

2. **`gui/theme_manager.py`** - 动态生成 QSS，支持主题切换
   - `ThemeManager` 类
   - `_generate_stylesheet()` 方法使用 design_system.py 的令牌
   - 支持深色/浅色主题切换和持久化

3. **应用入口** - 初始化并应用主题
   - `workbench.py` 第1997行：`theme_manager.get_stylesheet()`

## 迁移指南

如果需要添加新样式：

### 1. 添加颜色/字体/间距常量
编辑 `gui/design_system.py`：
```python
@dataclass(frozen=True)
class DarkThemeColors:
    NEW_COLOR: str = "#HEXCODE"
```

### 2. 添加组件样式
编辑 `gui/theme_manager.py` 的 `_generate_stylesheet()` 方法：
```python
stylesheet = f"""
#newComponent {{
    background-color: {colors.NEW_COLOR};
    ...
}}
"""
```

### 3. 使用样式
在组件代码中设置 objectName：
```python
widget = QWidget()
widget.setObjectName("newComponent")
```

## 旧文件位置

备份文件: `gui/styles.qss.deprecated`

**注意**: 如果需要参考旧样式，请查看备份文件，但不要直接使用其中的样式。
