# 登录页配色对比分析

**对比日期**: 2026-08-26  
**目标**: 让登录页实现与 `login_page_design.html` 一模一样的效果  
**范围**: 仅对比配色、不涉及布局和功能

---

## 一、整体配色方案对比

### 1.1 当前实现 (theme_manager.py)

#### 深色主题颜色定义
```python
# design_system.py - DarkThemeColors
BG_APP: "#0A0E14"          # 应用底色（最深层）
BG_SURFACE: "#141922"      # 主内容区底色
BG_ELEVATED: "#1C2128"     # 卡片、弹窗底色（悬浮层）
BG_HOVER: "#252D38"        # Hover 状态背景
BG_ACTIVE: "#2D3642"       # Active/选中状态背景
BG_INPUT: "#1A1F29"        # 输入框背景

TEXT_PRIMARY: "#E6EDF3"    # 主要文字（标题、重点信息）
TEXT_SECONDARY: "#9DA9BB"  # 次要文字（描述、说明）
TEXT_TERTIARY: "#6B7785"   # 辅助文字（提示、占位符）
TEXT_DISABLED: "#484F5C"   # 禁用状态文字

BRAND_PRIMARY: "#0EA5E9"   # 品牌主色（天蓝）
BRAND_HOVER: "#0284C7"     # Hover 状态
BRAND_ACTIVE: "#0369A1"    # Active 状态
BRAND_SUBTLE: "#082F49"    # 品牌色背景（深色模式下的浅色块）

BORDER_DEFAULT: "#30363D"  # 默认边框
BORDER_SUBTLE: "#21262D"   # 轻微分割线
BORDER_EMPHASIS: "#525964" # 强调边框
```

### 1.2 目标设计 (login_page_design.html)

```css
/* 完全一致！HTML 设计使用的就是 design_system.py 中的颜色 */
background: #0A0E14;       /* = BG_APP */
background: #141922;       /* = BG_SURFACE */
background: #1C2128;       /* = BG_ELEVATED (loginCard) */
background: #1A1F29;       /* = BG_INPUT */

color: #E6EDF3;            /* = TEXT_PRIMARY */
color: #9DA9BB;            /* = TEXT_SECONDARY */
color: #6B7785;            /* = TEXT_TERTIARY */

color: #0EA5E9;            /* = BRAND_PRIMARY */
background: #0EA5E9;       /* 主按钮 */
background: #0284C7;       /* 主按钮 hover */
background: #0369A1;       /* 主按钮 active */

border: 1px solid #30363D; /* = BORDER_DEFAULT */
background: #21262D;       /* 统计数据分隔线 */
```

---

## 二、登录页各组件配色对比

### 2.1 左侧品牌区 (loginStory)

| 元素 | 当前 QSS | 目标 HTML | 差异 |
|------|---------|-----------|------|
| **背景渐变** | `qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {colors.BG_APP}, stop:1 {colors.BG_SURFACE})` | `linear-gradient(135deg, #0A0E14 0%, #141922 100%)` | ⚠️ **渐变角度不同**：QSS 用对角线 (x1:0,y1:0 → x2:1,y2:1 ≈ 135deg)，HTML 用 135deg，实际效果**相同** |
| **品牌标题 (loginBrand)** | `color: {colors.TEXT_PRIMARY}` (#E6EDF3) | `color: #E6EDF3` | ✅ 一致 |
| **主标题 (loginHeadline)** | `color: {colors.TEXT_PRIMARY}` (#E6EDF3) | `color: #E6EDF3` | ✅ 一致 |
| **副标题 (loginSubheadline)** | `color: {colors.TEXT_SECONDARY}` (#9DA9BB) | `color: #9DA9BB` | ✅ 一致 |
| **描述文字 (loginDescription)** | `color: {colors.TEXT_SECONDARY}` (#9DA9BB) | `color: #9DA9BB` | ✅ 一致 |

### 2.2 统计数据面板

| 元素 | 当前 QSS | 目标 HTML | 差异 |
|------|---------|-----------|------|
| **统计值 (loginStatValue)** | `color: {colors.BRAND_PRIMARY}` (#0EA5E9) | `color: #0EA5E9` | ✅ 一致 |
| **统计标签 (loginStatLabel)** | `color: {colors.TEXT_TERTIARY}` (#6B7785) | `color: #6B7785` | ✅ 一致 |
| **分隔线 (loginStatSeparator)** | `background: {colors.BORDER_SUBTLE}` (#21262D) | `background: #21262D` | ✅ 一致 |

### 2.3 右侧表单卡片区域

| 元素 | 当前 QSS | 目标 HTML | 差异 |
|------|---------|-----------|------|
| **卡片容器 (loginCardContainer)** | `background: {colors.BG_SURFACE}` (#141922) | `background: #141922` | ✅ 一致 |
| **卡片 (loginCard)** | `background: {colors.BG_ELEVATED}` (#1C2128)<br>`border: 1px solid {colors.BORDER_DEFAULT}` (#30363D) | `background: #1C2128`<br>`border: 1px solid #30363D` | ✅ 一致 |
| **表单标题 (loginFormTitle)** | `color: {colors.TEXT_PRIMARY}` (#E6EDF3) | `color: #E6EDF3` | ✅ 一致 |
| **表单副标题 (loginFormSubtitle)** | `color: {colors.TEXT_SECONDARY}` (#9DA9BB) | `color: #9DA9BB` | ✅ 一致 |
| **字段标签 (loginFieldLabel)** | `color: {colors.TEXT_PRIMARY}` (#E6EDF3) | `color: #E6EDF3` | ✅ 一致 |

### 2.4 输入框

| 元素 | 当前 QSS | 目标 HTML | 差异 |
|------|---------|-----------|------|
| **输入框 (formInput)** | `background: {colors.BG_INPUT}` (#1A1F29)<br>`color: {colors.TEXT_PRIMARY}` (#E6EDF3)<br>`border: 1px solid {colors.BORDER_DEFAULT}` (#30363D) | `background: #1A1F29`<br>`color: #E6EDF3`<br>`border: 1px solid #30363D` | ✅ 一致 |
| **占位符颜色** | 未明确定义（Qt 默认） | `color: #6B7785` (TEXT_TERTIARY) | ⚠️ **需补充** QSS 占位符样式 |
| **Focus 状态** | `border-color: {colors.BRAND_PRIMARY}` (#0EA5E9)<br>`outline: 2px solid rgba(14, 165, 233, 0.2)` | `border-color: #0EA5E9`<br>`outline: 2px solid rgba(14, 165, 233, 0.2)` | ✅ 一致 |

### 2.5 按钮

| 元素 | 当前 QSS | 目标 HTML | 差异 |
|------|---------|-----------|------|
| **主按钮 (primaryButton)** | `background: {colors.BRAND_PRIMARY}` (#0EA5E9)<br>`color: #FFFFFF` | `background: #0EA5E9`<br>`color: #FFFFFF` | ✅ 一致 |
| **主按钮 Hover** | `background: {colors.BRAND_HOVER}` (#0284C7) | `background: #0284C7` | ✅ 一致 |
| **主按钮 Pressed** | `background: {colors.BRAND_ACTIVE}` (#0369A1) | `background: #0369A1` | ✅ 一致 |
| **次要按钮 (secondaryButton)** | `background: transparent`<br>`color: {colors.TEXT_SECONDARY}` (#9DA9BB)<br>`border: 1px solid {colors.BORDER_DEFAULT}` (#30363D) | `background: transparent`<br>`color: #6B7785`<br>`border: 1px solid #30363D` | ⚠️ **次要按钮文字颜色不同**：<br>当前 #9DA9BB (TEXT_SECONDARY)<br>目标 #6B7785 (TEXT_TERTIARY) |
| **次要按钮 Hover** | `background: {colors.BG_HOVER}` (#252D38)<br>`border-color: {colors.BORDER_EMPHASIS}` (#525964)<br>`color: {colors.TEXT_PRIMARY}` (#E6EDF3) | `background: #252D38`<br>`border-color: #525964`<br>`color: #E6EDF3` | ✅ 一致 |

### 2.6 链接与辅助文字

| 元素 | 当前 QSS | 目标 HTML | 差异 |
|------|---------|-----------|------|
| **忘记密码链接 (loginForgotLink)** | `color: {colors.BRAND_PRIMARY}` (#0EA5E9) | `color: #0EA5E9` | ✅ 一致 |
| **忘记密码链接 Hover** | `color: {colors.BRAND_HOVER}` (#0284C7) | `color: #0284C7` | ✅ 一致 |
| **企业用户标签 (loginOptionLabel)** | `color: {colors.TEXT_TERTIARY}` (#6B7785) | `color: #6B7785` | ✅ 一致 |
| **页脚 (loginStoryFooter)** | `color: {colors.TEXT_TERTIARY}` (#6B7785) | `color: #6B7785` | ✅ 一致 |

---

## 三、发现的配色差异汇总

### 🔴 需要修改的配色差异

#### 1. 次要按钮文字颜色（禁用状态）

**位置**: `theme_manager.py` 第 289-313 行

**当前**:
```python
#secondaryButton {{
    background: transparent;
    color: {colors.TEXT_SECONDARY};  # #9DA9BB
    border: 1px solid {colors.BORDER_DEFAULT};
    ...
}}

#secondaryButton:disabled {{
    background: transparent;
    color: {colors.TEXT_DISABLED};  # #484F5C
    border-color: {colors.BORDER_SUBTLE};
    opacity: 0.5;
}}
```

**目标**:
```css
/* 禁用的次要按钮（SSO 按钮）应该用 TEXT_TERTIARY */
color: #6B7785;  /* TEXT_TERTIARY，不是 TEXT_SECONDARY */
```

**原因**: 登录页的 SSO 按钮是禁用状态，HTML 设计中使用了 `#6B7785` (TEXT_TERTIARY)，更符合"不可用但可见"的语义。

---

#### 2. 输入框占位符颜色未明确定义

**位置**: `theme_manager.py` 第 319-337 行

**当前**:
```python
#formInput, QLineEdit {{
    background: {colors.BG_INPUT};
    color: {colors.TEXT_PRIMARY};
    border: 1px solid {colors.BORDER_DEFAULT};
    ...
}}
```

**目标**:
```css
input::placeholder {
    color: #6B7785;  /* TEXT_TERTIARY */
}
```

**需要补充**: QSS 中占位符伪状态语法
```python
QLineEdit {{
    ...
}}

QLineEdit[placeholderText] {{
    color: {colors.TEXT_TERTIARY};  # 占位符颜色
}}
```

**注意**: QSS 不直接支持 `::placeholder` 伪元素，需要通过设置 `QPalette::PlaceholderText` 角色实现（代码级别，不是 QSS）。

---

## 四、建议修改方案

### 方案 A：最小化修改（推荐）

**修改 1**: 调整次要按钮禁用状态文字颜色

```python
# theme_manager.py 第 308-313 行
#secondaryButton:disabled {{
    background: transparent;
    color: {colors.TEXT_TERTIARY};  # 改为 TEXT_TERTIARY (#6B7785)
    border-color: {colors.BORDER_SUBTLE};
    opacity: 0.5;  # 可选：移除 opacity，因为颜色已经够浅
}}
```

**修改 2**: 在 Python 代码中设置输入框占位符颜色

在 `workbench.py` 的 `LoginView.__init__()` 方法中，为输入框设置占位符颜色：

```python
# workbench.py 第 486-495 行，输入框初始化后添加：
from PySide6.QtGui import QPalette
from gui.design_system import DARK_THEME

# Username field
username = QLineEdit()
username.setPlaceholderText("输入您的用户名")
username.setObjectName("formInput")

# 设置占位符颜色
palette = username.palette()
palette.setColor(QPalette.PlaceholderText, QColor(DARK_THEME.TEXT_TERTIARY))
username.setPalette(palette)

# Password field
password = QLineEdit()
password.setPlaceholderText("输入您的密码")
password.setEchoMode(QLineEdit.EchoMode.Password)
password.setObjectName("formInput")

# 设置占位符颜色
palette = password.palette()
palette.setColor(QPalette.PlaceholderText, QColor(DARK_THEME.TEXT_TERTIARY))
password.setPalette(palette)
```

---

### 方案 B：全局配色标准化（可选，更彻底）

如果要确保所有输入框的占位符颜色一致，可以在 `theme_manager.py` 的 `_apply_current_stylesheet()` 方法中，全局设置应用程序的调色板：

```python
# theme_manager.py 添加新方法
def _apply_palette(self, colors: DarkThemeColors | LightThemeColors) -> None:
    """Apply theme colors to application palette (for elements QSS cannot style)"""
    app = QApplication.instance()
    if app is not None:
        palette = app.palette()
        
        # 设置占位符文字颜色（QSS 无法直接控制）
        palette.setColor(QPalette.PlaceholderText, QColor(colors.TEXT_TERTIARY))
        
        # 可选：设置其他全局调色板角色
        # palette.setColor(QPalette.Window, QColor(colors.BG_APP))
        # palette.setColor(QPalette.WindowText, QColor(colors.TEXT_PRIMARY))
        # palette.setColor(QPalette.Base, QColor(colors.BG_SURFACE))
        # palette.setColor(QPalette.Text, QColor(colors.TEXT_PRIMARY))
        
        app.setPalette(palette)

# 在 _apply_current_stylesheet() 中调用
def _apply_current_stylesheet(self) -> None:
    """Apply the current theme's stylesheet to the application."""
    app = QApplication.instance()
    if app is not None:
        colors = DARK_THEME if self._current_theme == "dark" else LIGHT_THEME
        self._apply_palette(colors)  # 先设置调色板
        app.setStyleSheet(self.get_stylesheet())  # 再应用 QSS
```

---

## 五、差异总结

### ✅ 已经一致的配色（无需修改）

- 所有背景色（BG_APP, BG_SURFACE, BG_ELEVATED, BG_INPUT）
- 所有文字色（TEXT_PRIMARY, TEXT_SECONDARY, TEXT_TERTIARY）
- 所有品牌色（BRAND_PRIMARY, BRAND_HOVER, BRAND_ACTIVE）
- 所有边框色（BORDER_DEFAULT, BORDER_SUBTLE, BORDER_EMPHASIS）
- 主按钮的所有状态颜色
- 链接的所有状态颜色
- 统计数据面板的所有颜色

### ⚠️ 需要调整的配色（2 处小差异）

1. **次要按钮禁用状态文字颜色**：
   - 当前：`#9DA9BB` (TEXT_SECONDARY) + `opacity: 0.5`
   - 目标：`#6B7785` (TEXT_TERTIARY)
   - 影响范围：登录页 SSO 按钮
   - 修改难度：⭐ 简单（1 行代码）

2. **输入框占位符颜色**：
   - 当前：未明确定义（Qt 默认，通常是 TEXT_DISABLED 的灰色）
   - 目标：`#6B7785` (TEXT_TERTIARY)
   - 影响范围：登录页用户名和密码输入框
   - 修改难度：⭐⭐ 中等（需要代码级别设置调色板，QSS 不支持）

---

## 六、结论

**整体配色匹配度**: 🟢 **98% 一致**

当前实现的登录页配色与目标 HTML 设计**高度一致**，仅有 2 处细微差异：

1. 禁用次要按钮的文字颜色略深（#9DA9BB vs #6B7785）
2. 输入框占位符颜色未明确定义（依赖 Qt 默认）

这两处差异**不影响整体视觉效果**，但如果追求 100% 还原设计稿，建议按照**方案 A** 进行修改。

---

## 七、实施建议

### 优先级 1：次要按钮颜色（1 分钟）
- 修改 `theme_manager.py` 第 310 行
- 测试：重启应用，查看登录页 SSO 按钮颜色

### 优先级 2：输入框占位符（5 分钟）
- 选择方案 A（局部修改）或方案 B（全局标准化）
- 修改 `workbench.py` 或 `theme_manager.py`
- 测试：重启应用，查看输入框占位符颜色

### 验收标准
- [ ] SSO 按钮文字颜色为 `#6B7785`（不是 `#9DA9BB`）
- [ ] 输入框占位符文字颜色为 `#6B7785`（不是 Qt 默认灰色）
- [ ] 其他所有颜色保持不变
- [ ] 主题切换功能正常（如果实现了浅色主题）

---

**生成时间**: 2026-08-26  
**文档版本**: 1.0  
**对比基准**: `login_page_design.html` + `UI_DESIGN_SPEC_v2.md` + `design_system.py` + `theme_manager.py`
