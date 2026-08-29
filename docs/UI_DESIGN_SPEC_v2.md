# AutoLabeler UI 设计规格文档 v2.1 (性能优化版)

> **目标**：将功能验证型 GUI 重构为高端专业企业 SaaS 产品界面  
> **对标**：Labelbox + Linear + Vercel Dashboard  
> **用户**：制造业质检团队（50人部门，技术领导 + 专业人员 + 业务人员）  
> **约束**：PySide6 桌面应用，1920x1080 为主，支持笔记本分辨率，预留中英双语  
> **更新日期**：2026-08-24  
> **优化版本**：v2.1 - 前端性能优化版

---

## 本版本优化重点

### 🎯 设计规范修正
1. **修复导航选中状态视觉跳动**（border-left 导致的布局偏移）
2. **简化响应式断点**（5个 → 3个，降低维护成本）
3. **补充缺失的设计规格**（任务中心、空状态、长文本、Loading、动画参数）
4. **明确组件使用场景**（卡片内边距、进度条高度）

### ⚡ 性能优化方案
1. **阴影系统优化**：边框模拟 + 选择性真实阴影，避免大量 QGraphicsDropShadowEffect
2. **动画策略优化**：明确动画参数，减少不必要的过渡效果
3. **渲染优化**：合理使用硬件加速，避免过度重绘
4. **深色主题移除**：v2.1 版本已移除深色主题支持，简化代码维护

---

## 目录

- [第一部分：视觉设计系统](#第一部分视觉设计系统)
  - [1.1 色彩规范](#11-色彩规范)
  - [1.2 字体系统](#12-字体系统)
  - [1.3 间距系统](#13-间距系统)
  - [1.4 圆角系统](#14-圆角系统)
  - [1.5 阴影系统（性能优化）](#15-阴影系统性能优化)
  - [1.6 组件规范](#16-组件规范)
  - [1.7 动画规范（新增）](#17-动画规范新增)
- [第二部分：页面设计规格](#第二部分页面设计规格)
  - [2.1 应用外壳](#21-应用外壳app-shell)
  - [2.2 登录页](#22-登录页login-page)
  - [2.3 主页](#23-主页homepage)
  - [2.4 任务中心（补充完整）](#24-任务中心补充完整)
  - [2.5 扫描页](#25-扫描页scan-page)
  - [2.6 抽样页](#26-抽样页sample-page)
  - [2.7 标注页 & 复核页（补充完整）](#27-标注页--复核页补充完整)
  - [2.8 训练页](#28-训练页train-page)
  - [2.9 推理页](#29-推理页infer-page)
  - [2.10 还原页](#210-还原页restore-page)
  - [2.11 转换页](#211-转换页convert-page)
  - [2.12 空状态设计（新增）](#212-空状态设计新增)
  - [2.13 Loading 状态设计（新增）](#213-loading-状态设计新增)
  - [2.14 错误状态设计（补充完整）](#214-错误状态设计补充完整)
- [第三部分：交互规范](#第三部分交互规范)
  - [3.1 确认流程设计](#31-确认流程设计)
  - [3.2 进度反馈设计](#32-进度反馈设计)
  - [3.3 错误提示设计](#33-错误提示设计)
  - [3.4 成功反馈设计](#34-成功反馈设计)
  - [3.5 响应式适配（简化版）](#35-响应式适配简化版)
  - [3.6 多语言预留](#36-多语言预留)
  - [3.7 长文本显示策略（新增）](#37-长文本显示策略新增)
- [第四部分：实施建议](#第四部分实施建议)
  - [4.1 实施优先级（调整版）](#41-实施优先级调整版)
  - [4.2 技术实现路径（性能优化）](#42-技术实现路径性能优化)
  - [4.3 验证检查点（补充完整）](#43-验证检查点补充完整)
  - [4.4 资源需求](#44-资源需求)
  - [4.5 风险与应对（补充完整）](#45-风险与应对补充完整)

---

## 设计背景

### 核心问题
1. **视觉专业度不足** → 影响销售，客户认为"不值这个价"
2. **交互反馈不明显** → 用户找不到确认按钮、看不清操作状态
3. **新人学习曲线陡** → 30 分钟能上手，但初期需要重复问

### 设计目标
1. **对外形象**：高端、专业、可靠（对标 Labelbox 的工具感）
2. **对内效率**：操作清晰、反馈明确、降低新人出错率
3. **技术约束**：PySide6 桌面应用、1920x1080 为主、浅色主题、预留多语言
4. **性能目标**：流畅 60fps、页面加载 < 500ms

### 设计优先级
1. **视觉重构** > 交互优化 > 新增功能
2. **登录页 + 主页** > 8 个功能页
3. **所有页面都需打磨**（一人使用所有子功能）
4. **性能优化贯穿始终**（不牺牲视觉质量）

---

## 第一部分：视觉设计系统

### 0.1 术语说明

> **重要**：本文档使用 CSS 术语描述布局和样式以便于理解，实际实现需转换为 PySide6 等价写法。

#### CSS 与 PySide6 术语对照

| CSS 术语 | PySide6 实现 | 说明 |
|---------|-------------|------|
| `display: grid` | `QGridLayout` | 网格布局 |
| `display: flex` | `QHBoxLayout` / `QVBoxLayout` | 弹性盒子布局 |
| `gap: 12px` | `layout.setSpacing(12)` | 元素间距 |
| `padding: 10px 20px` | `setContentsMargins(20, 10, 20, 10)` | 内边距（Qt 顺序：left, top, right, bottom） |
| `margin: 16px` | `setMargin(16)` | 外边距 |
| `background-color` | `setStyleSheet("background-color: ...")` | 背景色 |
| `border-radius` | QSS `border-radius` | 圆角 |
| `transition` | `QPropertyAnimation` | 过渡动画 |
| `@keyframes` | `QPropertyAnimation` + `QEasingCurve` | 关键帧动画 |

**注意**：文档中的 CSS 代码块仅为示意，实际开发时请参考 `gui/components.py` 和 `gui/theme_manager.py` 中的实现。

### 1.1 色彩规范

#### 浅色主题 — Light Professional

> **说明**：本项目采用浅色主题作为唯一主题。深色主题已在 v2.1 版本中移除。

**背景色系**
```
--bg-app: #F8FAFC          // 应用底色
--bg-surface: #FFFFFF      // 主内容区底色
--bg-elevated: #FFFFFF     // 卡片、弹窗（白色+阴影）
--bg-hover: #F1F5F9        // Hover 状态
--bg-active: #E2E8F0       // Active/选中状态
--bg-input: #FFFFFF        // 输入框背景
```

**文字色系**
```
--text-primary: #0F172A    // 主要文字
--text-secondary: #475569  // 次要文字
--text-tertiary: #94A3B8   // 辅助文字
--text-disabled: #CBD5E1   // 禁用状态
```

**品牌色**
```
--brand-primary: #0EA5E9
--brand-hover: #0284C7
--brand-active: #0369A1
--brand-subtle: #E0F2FE    // 浅色背景块
```

**语义色系**
```
--success: #10B981
--success-bg: #D1FAE5
--success-border: #34D399

--warning: #F59E0B
--warning-bg: #FEF3C7
--warning-border: #FBBF24

--error: #EF4444
--error-bg: #FEE2E2
--error-border: #F87171

--info: #3B82F6
--info-bg: #DBEAFE
--info-border: #60A5FA
```

**边框与分割线**
```
--border-default: #E2E8F0
--border-subtle: #F1F5F9
--border-emphasis: #CBD5E1
```

---

### 1.2 字体系统

#### 字体族
```python
# 优先级顺序（Windows 为主）
FONT_FAMILY = [
    "Microsoft YaHei UI",      # 微软雅黑 UI（Windows 推荐）
    "Microsoft YaHei",         # 微软雅黑（实际存在）
    "PingFang SC",             # 苹方（macOS）
    "SF Pro Display",          # San Francisco（macOS 系统字体）
    "Segoe UI",                # Windows 系统字体
    "-apple-system",
    "BlinkMacSystemFont",
    "sans-serif"
]

# 等宽字体（用于代码、路径）
FONT_FAMILY_MONO = [
    "Consolas",
    "Monaco",
    "SF Mono",
    "Courier New",
    "monospace"
]
```

#### 字体尺寸与层级

```python
# 标题层级
FONT_SIZE_H1 = 28      # 页面主标题
FONT_SIZE_H2 = 22      # 区块标题
FONT_SIZE_H3 = 18      # 卡片标题
FONT_SIZE_H4 = 16      # 小节标题

# 正文层级
FONT_SIZE_BODY_L = 15  # 大号正文（重点说明）
FONT_SIZE_BODY = 14    # 标准正文（表单标签、按钮）
FONT_SIZE_BODY_S = 13  # 小号正文（描述文字）
FONT_SIZE_CAPTION = 12 # 辅助文字（提示、标签）

# 行高
LINE_HEIGHT_TIGHT = 1.2   # 标题
LINE_HEIGHT_NORMAL = 1.5  # 正文
LINE_HEIGHT_RELAXED = 1.7 # 说明文字

# 字重
FONT_WEIGHT_REGULAR = 400
FONT_WEIGHT_MEDIUM = 500   # 强调、按钮
FONT_WEIGHT_SEMIBOLD = 600 # 标题
FONT_WEIGHT_BOLD = 700     # 特别强调
```

---

### 1.3 间距系统

**8px 基础网格**

```python
SPACE_1 = 4    # 极小间距（图标与文字）
SPACE_2 = 8    # 小间距（紧密元素）
SPACE_3 = 12   # 标准间距（相关元素）
SPACE_4 = 16   # 中等间距（组内元素）
SPACE_5 = 24   # 大间距（组与组之间）
SPACE_6 = 32   # 特大间距（区块分隔）
SPACE_8 = 48   # 超大间距（页面区域）
SPACE_10 = 64  # 页面级间距
```

**组件内边距规范**

```python
# 按钮内边距
BUTTON_PADDING_SM = (6, 12)    # 小按钮
BUTTON_PADDING_MD = (10, 20)   # 标准按钮
BUTTON_PADDING_LG = (14, 28)   # 大按钮

# 卡片内边距
CARD_PADDING = 24              # 标准卡片
CARD_PADDING_COMPACT = 16      # 紧凑卡片
CARD_PADDING_SPACIOUS = 32     # 宽松卡片

# 页面边距
PAGE_PADDING = 32              # 页面主区域
SIDEBAR_PADDING = 20           # 侧边栏
```

**卡片内边距使用场景**（新增）
```python
# 24px（标准卡片）
- 主页模块卡片
- 任务中心任务卡片
- 预检结果卡片

# 16px（紧凑卡片）
- 设置页参数组卡片
- 手册页内容卡片
- 状态标签容器

# 32px（宽松卡片）
- 登录页表单卡片
- 完成面板大卡片
- Hero 区域
```

---

### 1.4 圆角系统

```python
RADIUS_SM = 4      # 小元素（标签、徽章）
RADIUS_MD = 6      # 按钮、输入框
RADIUS_LG = 8      # 卡片
RADIUS_XL = 12     # 弹窗、大卡片
RADIUS_2XL = 16    # 模态框
RADIUS_FULL = 9999 # 圆形元素
```

---

### 1.5 阴影系统（性能优化）

> **性能优化策略**：
> - **优先使用边框模拟阴影**（性能最佳）
> - **仅在必要处使用真实阴影**（QGraphicsDropShadowEffect）
> - **Hover 状态动态启用阴影**（静态状态不启用）

**方案 A：边框模拟阴影（推荐，高性能）**
```python
# 轻微阴影
border: 1px solid #E2E8F0
border-bottom: 2px solid #CBD5E1

# 中等阴影
border: 1px solid #CBD5E1
border-bottom: 3px solid #94A3B8

# 强调阴影
border: 1px solid #94A3B8
border-bottom: 4px solid #64748B
```

**方案 B：真实阴影（选择性使用）**
```python
SHADOW_SM_REAL = QGraphicsDropShadowEffect()
SHADOW_SM_REAL.setBlurRadius(4)
SHADOW_SM_REAL.setColor(QColor(0, 0, 0, 13))  # 5% 不透明度
SHADOW_SM_REAL.setOffset(0, 2)

SHADOW_MD_REAL = QGraphicsDropShadowEffect()
SHADOW_MD_REAL.setBlurRadius(8)
SHADOW_MD_REAL.setColor(QColor(0, 0, 0, 26))  # 10% 不透明度
SHADOW_MD_REAL.setOffset(0, 4)
```

---

### 1.6 组件规范

> **说明**：以下组件规范基于浅色主题。深色主题已在 v2.1 版本中移除。

#### 按钮（Button）

**主要按钮（Primary）**
```python
background: #0EA5E9
color: #FFFFFF
border: none
border-radius: 6px
padding: 10px 20px
font-size: 14px
font-weight: 500
cursor: pointer

# Hover
background: #0284C7
# 性能优化：用边框模拟阴影
border-bottom: 2px solid #0369A1

# Active
background: #0369A1
transform: translateY(1px)  # 按下效果配合边框
border-bottom: 1px solid #0369A1  # 同步调整

# Disabled
background: #E2E8F0
color: #94A3B8
cursor: not-allowed
border-bottom: none
```

**次要按钮（Secondary）**
```python
background: transparent
color: #475569
border: 1px solid #E2E8F0
border-radius: 6px
padding: 10px 20px

# Hover
background: #F1F5F9
border-color: #CBD5E1
color: #0F172A

# Active
background: #E2E8F0
```

**危险按钮（Danger）**
```python
background: #EF4444
color: #FFFFFF

# Hover
background: #DC2626
border-bottom: 2px solid #B91C1C  # 边框模拟阴影
```

#### 输入框（Input）

```python
background: #FFFFFF
color: #0F172A
border: 1px solid #E2E8F0
border-radius: 6px
padding: 10px 12px
font-size: 14px

# Focus
border-color: #0EA5E9
# 性能优化：用 outline 模拟外发光
outline: 2px solid rgba(14, 165, 233, 0.2)
outline-offset: 0px

# Error
border-color: #EF4444
outline: 2px solid rgba(239, 68, 68, 0.2)

# Disabled
background: #F8FAFC
color: #94A3B8
cursor: not-allowed
```

#### 下拉框（Select/ComboBox）

```python
# 与输入框保持一致的样式
# 下拉箭头颜色：#475569
# 下拉面板背景：#FFFFFF
# 选项 Hover：#F1F5F9
# 选中项背景：#E0F2FE
# 选中项文字：#0EA5E9
```

#### 卡片（Card）

```python
background: #FFFFFF
border: 1px solid #E2E8F0
border-radius: 8px
padding: 24px
# 性能优化：静态卡片用边框模拟阴影
border-bottom: 2px solid #CBD5E1

# Hover（可交互卡片）
border-color: #CBD5E1
border-bottom: 3px solid #94A3B8  # 加强阴影
transform: translateY(-2px)
# 过渡动画（性能优化：只过渡 transform 和 border）
transition: transform 0.2s ease, border-color 0.2s ease
```

#### 进度条（Progress Bar）

**小进度条（8px）- 用于紧凑场景**
```python
# 容器
background: #F1F5F9
height: 8px
border-radius: 4px
overflow: hidden

# 进度填充
background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                            stop:0 #0EA5E9, stop:1 #0284C7)
height: 100%
# 性能优化：宽度变化用 QPropertyAnimation，避免 CSS transition
```

**使用场景**：
- 任务中心任务卡片
- 训练页 epoch 进度（紧凑模式）

**大进度条（24px）- 用于主要展示**
```python
# 容器
background: #F1F5F9
height: 24px
border-radius: 6px
padding: 0 12px
display: flex
align-items: center
overflow: hidden

# 进度填充
background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                            stop:0 #0EA5E9, stop:1 #0284C7)
height: 100%

# 文字
font-size: 14px
color: #0F172A
line-height: 24px
text-align: center
```

**使用场景**：
- 推理页主进度面板
- 训练页完成百分比显示
- 转换页转换进度

#### 标签/徽章（Badge/Tag）

```python
# 默认标签
background: #F1F5F9
color: #475569
padding: 4px 10px
border-radius: 4px
font-size: 12px
font-weight: 500

# 状态标签
# 运行中：background: #D1FAE5, color: #10B981
# 已完成：background: #DBEAFE, color: #3B82F6
# 失败：background: #FEE2E2, color: #EF4444
# 等待中：background: #FEF3C7, color: #F59E0B
```

---

### 1.7 动画规范（新增）

> **性能优化原则**：
> - 优先使用 `transform` 和 `opacity`（GPU 加速）
> - 避免动画 `width`、`height`、`padding`（触发重排）
> - 使用 `QPropertyAnimation` 而非 QSS transition（性能更好）

#### 卡片 Hover 动画

```python
# 参数
duration = 200  # 毫秒
easing_curve = QEasingCurve.Type.OutCubic
translate_y = -4  # 像素
border_transition = 200  # 毫秒

# 实现示例
animation = QPropertyAnimation(card, b"pos")
animation.setDuration(200)
animation.setStartValue(original_pos)
animation.setEndValue(QPoint(original_pos.x(), original_pos.y() - 4))
animation.setEasingCurve(QEasingCurve.Type.OutCubic)
animation.start()
```

#### 进度条更新动画

```python
# 参数
duration = 300  # 毫秒
easing_curve = QEasingCurve.Type.Linear
update_interval = 500  # 每 500ms 更新一次进度值

# 实现示例
animation = QPropertyAnimation(progress_bar, b"value")
animation.setDuration(300)
animation.setStartValue(old_value)
animation.setEndValue(new_value)
animation.setEasingCurve(QEasingCurve.Type.Linear)
animation.start()
```

#### 按钮按下动画

```python
# 参数
duration = 100  # 毫秒
translate_y = 1  # 像素

# QSS 实现（轻量级，可用）
QPushButton:pressed {
    transform: translateY(1px);  # 配合边框高度变化
}
```

#### 主题切换动画

```python
# 参数（性能优化：选择性过渡）
duration = 300  # 毫秒
transitioned_properties = [
    "background-color",
    "border-color",
    "color"
]
non_transitioned_properties = [
    "border-radius",  # 不过渡，避免重排
    "padding",        # 不过渡，避免重排
    "margin",         # 不过渡，避免重排
    "width",          # 不过渡，避免重排
    "height"          # 不过渡，避免重排
]

# QSS 实现
* {
    transition: background-color 0.3s ease,
                border-color 0.3s ease,
                color 0.3s ease;
}

# 排除动画元素
.progress-bar, .spinner, .pulse-animation {
    transition: none !important;
}
```

#### 页面加载淡入动画（可选）

```python
# 参数
duration = 200  # 毫秒
start_opacity = 0.0
end_opacity = 1.0

# 实现示例
animation = QPropertyAnimation(page, b"windowOpacity")
animation.setDuration(200)
animation.setStartValue(0.0)
animation.setEndValue(1.0)
animation.start()
```

**动画使用决策树**（新增）
```
需要动画效果？
├─ 用户交互反馈（Hover/Click）？
│  ├─ 是 → 短动画（100-200ms）
│  └─ 否 → 继续判断
├─ 状态变化（进度更新）？
│  ├─ 是 → 中等动画（300ms）
│  └─ 否 → 继续判断
└─ 页面切换/主题切换？
   ├─ 是 → 选择性动画（只动画颜色，300ms）
   └─ 否 → 不使用动画
```

#### 动画降级方案（Accessibility）

```python
# 设置项：禁用动画（用于性能弱设备或用户偏好）
DISABLE_ANIMATIONS = False  # 可配置

# 降级规则
if DISABLE_ANIMATIONS:
    # 1. 卡片 Hover：只改变颜色，不使用 transform
    # 2. 进度条：直接跳到目标值，不使用 QPropertyAnimation
    # 3. 主题切换：立即应用新主题，不使用 transition
    # 4. 按钮按下：只改变背景色，不使用 translateY
    pass

# 实现示例
def apply_hover_effect(card: QWidget, enabled: bool):
    if DISABLE_ANIMATIONS:
        # 降级：只改变样式，不使用动画
        card.setStyleSheet("background: #252D38;" if enabled else "")
    else:
        # 完整动画
        animation = QPropertyAnimation(card, b"pos")
        animation.setDuration(200)
        # ...
```

**动画性能监控**（可选实施）

```python
# 用于开发阶段检测动画性能瓶颈
# 监控帧率，低于 30fps 时自动禁用部分动画

import time

class AnimationMonitor:
    def __init__(self):
        self.frame_times = []
    
    def record_frame(self):
        self.frame_times.append(time.time())
        if len(self.frame_times) > 60:
            self.frame_times.pop(0)
    
    def get_fps(self) -> float:
        if len(self.frame_times) < 2:
            return 60.0
        elapsed = self.frame_times[-1] - self.frame_times[0]
        return len(self.frame_times) / elapsed if elapsed > 0 else 60.0
    
    def should_disable_animations(self) -> bool:
        return self.get_fps() < 30.0
```

---

## 第二部分：页面设计规格

### 2.1 应用外壳（App Shell）

#### 整体布局结构

```
┌─────────────────────────────────────────────────────────┐
│  [侧边导航 240px]  │  [主内容区 flex-1]                  │
│                    │                                      │
│  Logo + 品牌       │  ┌─────────────────────────────┐   │
│  ─────────────     │  │  当前页面内容               │   │
│  🏠 首页           │  │                             │   │
│  📋 任务中心       │  │                             │   │
│  ─────────────     │  │                             │   │
│  主流程            │  │                             │   │
│  01 扫描           │  │                             │   │
│  02 抽样           │  │                             │   │
│  03 标注           │  │                             │   │
│  04 训练           │  │                             │   │
│  05 推理           │  │                             │   │
│  06 复核           │  │                             │   │
│  07 还原           │  │                             │   │
│  08 转换           │  │                             │   │
│  ─────────────     │  │                             │   │
│  📖 使用手册       │  │                             │   │
│  ⚙️ 设置           │  └─────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

#### 侧边导航设计改进

**当前问题**：
- 宽度 180px 太窄，中文模块名称拥挤
- 选中状态不够明显
- 模块编号与名称视觉层级不清晰
- **border-left 导致选中时视觉跳动**（性能优化修复）

**改进方案**：

```python
# 导航容器
width: 240px  # 从当前约 180px 增加到 240px
background: #0A0E14  # 最深背景色
border-right: 1px solid #21262D
padding: 20px 0

# Logo 区域（顶部）
padding: 0 20px 24px
border-bottom: 1px solid #21262D

## Logo 标记
background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                            stop:0 #0EA5E9, stop:1 #0284C7)
width: 40px
height: 40px
border-radius: 8px
display: flex
align-items: center
justify-content: center
font-size: 18px
font-weight: 700
color: #FFFFFF

## 品牌文字
font-size: 16px
font-weight: 600
color: #E6EDF3
line-height: 1.3
margin-left: 12px

# 导航分组标题
padding: 20px 20px 8px
font-size: 11px
font-weight: 600
color: #6B7785
text-transform: uppercase
letter-spacing: 0.5px

# 导航按钮（未选中）
padding: 10px 20px 10px 17px  # ⚡ 左侧预留 3px 空间
margin: 2px 12px
border-radius: 6px
background: transparent
border-left: 3px solid transparent  # ⚡ 修复：透明边框占位
color: #9DA9BB
font-size: 14px
font-weight: 500
cursor: pointer
transition: background-color 0.15s ease, 
            border-color 0.15s ease,
            color 0.15s ease

# Hover 状态
background: #141922
color: #E6EDF3
border-left: 3px solid transparent  # ⚡ 保持透明，避免跳动

# 选中状态（当前页面）
background: #082F49  # 品牌色深色背景
color: #0EA5E9      # 品牌色文字
border-left: 3px solid #0EA5E9  # ⚡ 左侧强调条（不会跳动）
font-weight: 600

# 流程模块特殊设计（带编号）
display: flex
align-items: center

## 编号徽章
width: 24px
height: 24px
border-radius: 4px
background: #1C2128
color: #6B7785
font-size: 12px
font-weight: 600
display: flex
align-items: center
justify-content: center
margin-right: 10px
transition: background-color 0.15s ease, color 0.15s ease

## 选中时编号徽章
background: #0EA5E9
color: #FFFFFF
```

**视觉效果对比**：

| 当前设计 | 改进设计 | 性能优化 |
|---------|---------|----------|
| 窄小拥挤（180px） | 宽敞舒适（240px） | ✅ |
| 选中状态不明显 | 蓝色背景 + 左侧强调条 | ✅ |
| **选中时视觉跳动** | **预留透明边框，无跳动** | ⚡ **修复** |
| 编号与文字混在一起 | 编号用独立徽章，视觉分离 | ✅ |
| Emoji 图标不专业 | 可选：替换为 icon font 或保留简化 | ✅ |

---

### 2.2 登录页（Login Page）

> ⚠️ **当前版本未实现** - 此页面为设计规范，实际产品中尚未开发

> **设计原则**：企业级视觉 + 功能诚实（不伪装未实现的安全特性）

#### 布局结构

```
┌──────────────────────────────────────────────────────────────┐
│  [左侧品牌区 40%]           │  [右侧表单区 60%]             │
│                             │                                 │
│  Auto Labeler               │       ┌─────────────────┐      │
│                             │       │  登录           │      │
│  AI 驱动的智能标注平台       │       │  欢迎回来...    │      │
│  使用先进的机器学习技术...   │       │                 │      │
│                             │       │  用户名         │      │
│  ┌────┐ ┌────┐ ┌────┐      │       │  [_________]    │      │
│  │95% │ │10x │ │50K+│      │       │                 │      │
│  │标注│ │效率│ │处理│      │       │  密码           │      │
│  │准确│ │提升│ │图像│      │       │  [_________]    │      │
│  └────┘ └────┘ └────┘      │       │                 │      │
│                             │       │  忘记密码？     │      │
│  © 2026 Auto Labeler...     │       │  [登录按钮]     │      │
│                             │       │                 │      │
│                             │       │  企业用户       │      │
│                             │       │  [使用 SSO 登录]│      │
│                             │       └─────────────────┘      │
└──────────────────────────────────────────────────────────────┘
```

#### 组件规格

**左侧品牌区**
```python
# 容器
width: 40%
background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                            stop:0 #0A0E14, stop:1 #141922)  # 深色渐变
padding: 56px 56px 64px

# 品牌标题
font-size: 32px
font-weight: 700
color: #E6EDF3
margin-bottom: 90px

# 主标题
font-size: 36px
font-weight: 700
color: #E6EDF3
line-height: 1.3
margin-bottom: 24px

# 副标题
font-size: 16px
font-weight: 400
color: #9DA9BB
line-height: 1.7
margin-bottom: 64px

# 统计数据卡片（三个横排）
display: flex
gap: 56px

## 单个统计卡
text-align: center

## 数值
font-size: 40px
font-weight: 700
color: #0EA5E9  # 品牌色
margin-bottom: 6px

## 标签
font-size: 14px
color: #6B7785

# 底部版权
font-size: 13px
color: #6B7785
position: absolute
bottom: 64px
```

**右侧表单区**
```python
# 容器
width: 60%
background: #141922
padding: 80px
display: flex
align-items: center
justify-content: center

# 表单卡片
background: #1C2128
border: 1px solid #30363D
border-radius: 12px
padding: 48px
width: 440px
max-width: 100%
# 阴影：使用真实阴影（单一静态卡片，可接受）
box-shadow: 0 8px 16px rgba(0, 0, 0, 0.4)

# 表单标题
font-size: 28px
font-weight: 700
color: #E6EDF3
margin-bottom: 12px

# 表单副标题
font-size: 14px
color: #9DA9BB
margin-bottom: 48px

# 字段标签
font-size: 14px
font-weight: 500
color: #E6EDF3
margin-bottom: 8px

# 输入框
background: #1A1F29
border: 1px solid #30363D
border-radius: 6px
padding: 12px 14px
font-size: 14px
color: #E6EDF3
margin-bottom: 24px

# 输入框 Focus
border-color: #0EA5E9
outline: 2px solid rgba(14, 165, 233, 0.2)

# 忘记密码链接
font-size: 13px
color: #0EA5E9
text-decoration: none
margin-bottom: 16px
align-self: flex-end

# 主按钮（登录）
background: #0EA5E9
color: #FFFFFF
border: none
border-radius: 6px
padding: 14px 28px
font-size: 15px
font-weight: 600
width: 100%
margin-bottom: 32px
cursor: pointer

# 主按钮 Hover
background: #0284C7
border-bottom: 2px solid #0369A1  # 边框模拟阴影

# 企业用户标签
font-size: 12px
color: #6B7785
text-transform: uppercase
letter-spacing: 0.5px
margin-bottom: 12px

# SSO 按钮（禁用状态）
background: transparent
border: 1px solid #30363D
color: #6B7785
border-radius: 6px
padding: 12px 24px
font-size: 14px
width: 100%
cursor: not-allowed
opacity: 0.5
```

#### 注意事项

1. **测试契约组件**：现有实现包含隐藏的 `loginWorkflowPanel` 和 `loginBoundaryPanel`（用于测试），设计实施时保留这些组件但保持不可见
2. **SSO 入口**：按钮显示但禁用，提示"企业 SSO 将在后续版本提供"
3. **无安全伪装**：不实现密码强度检查、验证码等未后端实现的安全特性
4. **响应式**：小于 1366px 时左侧品牌区缩小到 35%，统计卡片垂直排列

---

### 2.3 主页（Homepage）

> **设计原则**：单屏产品入口 + 8 个模块卡片 + 可选 AI 预览

#### 布局结构

```
┌──────────────────────────────────────────────────────────────────┐
│  [主内容区]                                │ [AI 预览 260-318px] │
│  ┌─────────────────────────────────────┐  │ ┌─────────────────┐ │
│  │  AutoLabeler Workbench              │  │ │ AI 操作助手     │ │
│  │  从少量标注到批量预测复核            │  │ │ PREVIEW         │ │
│  │  扫描、抽样、标注...                │  │ │                 │ │
│  │  [开始 Flow 流程] [使用手册]        │  │ │ 用一句话把任务  │ │
│  └─────────────────────────────────────┘  │ │ 交给工作台      │ │
│                                            │ │                 │ │
│  ┌────┬────┬────┬────┐                    │ │ [抽样][推理]    │ │
│  │ 01 │ 02 │ 03 │ 04 │                    │ │ [复核][还原]    │ │
│  │扫描│抽样│标注│训练│                    │ │                 │ │
│  │...│...│...│...│                    │ │ 对话线程...     │ │
│  ├────┼────┼────┼────┤                    │ │                 │ │
│  │ 05 │ 06 │ 07 │ 08 │                    │ │ [预览功能暂不   │ │
│  │推理│复核│还原│转换│                    │ │  可输入]        │ │
│  │...│...│...│...│                    │ └─────────────────┘ │
│  └────┴────┴────┴────┘                                         │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │  系统优势          CORE                                  │  │
│  │  ┌──────────┬──────────┬──────────┬──────────┐         │  │
│  │  │ 01 可追溯│ 02 省人工│ 03 防误操│ 04 可独立│         │  │
│  │  │ mapping │ 先标代表 │ 移动覆盖 │ 每个工具 │         │  │
│  │  │ 串起...  │ 样本...  │ 前预检   │ 说明...  │         │  │
│  │  └──────────┴──────────┴──────────┴──────────┘         │  │
│  │                                         开发者：rui      │  │
│  └─────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
```

#### Hero 区域规格

```python
# 容器
background: #141922
border: 1px solid #21262D
border-bottom: 2px solid #1A1F29  # 边框模拟阴影
border-radius: 8px
padding: 26px 26px 20px
margin-bottom: 12px

# Eyebrow 标签
font-size: 12px
font-weight: 600
color: #6B7785
text-transform: uppercase
letter-spacing: 0.5px
margin-bottom: 10px

# 主标题
font-size: 28px
font-weight: 700
color: #E6EDF3
line-height: 1.2
margin-bottom: 10px

# 描述文字
font-size: 14px
color: #9DA9BB
line-height: 1.5
margin-bottom: 16px

# 操作按钮组
display: flex
gap: 8px

## 主按钮
background: #0EA5E9
color: #FFFFFF
padding: 10px 20px
border-radius: 6px
font-size: 14px
font-weight: 500

## 次要按钮
background: transparent
border: 1px solid #30363D
color: #9DA9BB
padding: 10px 20px
border-radius: 6px
font-size: 14px
```

#### 模块卡片规格（8 个）

```python
# 网格布局
display: grid
grid-template-columns: repeat(4, 1fr)
grid-template-rows: repeat(2, 1fr)
gap: 9px
margin-bottom: 12px

# 单个卡片
background: #141922
border: 1px solid #21262D
border-bottom: 2px solid #1A1F29  # 静态：边框模拟阴影
border-radius: 8px
padding: 10px 12px
min-height: 108px
cursor: pointer
display: flex
flex-direction: column
align-items: center
justify-content: center
text-align: center
transition: transform 0.2s ease, border-color 0.2s ease

# 卡片 Hover
border-color: #30363D
border-bottom: 3px solid #21262D  # 加强阴影
transform: translateY(-2px)

# 卡片标题（编号 + 模块名）
font-size: 15px
font-weight: 600
color: #E6EDF3
margin-bottom: 7px

# 卡片描述
font-size: 12px
color: #9DA9BB
line-height: 1.4
```

#### AI 预览面板规格

> ⚠️ **实现状态待确认** - AI 预览面板可能未完全实现，需验证功能

```python
# 容器
background: #141922
border: 1px solid #21262D
border-radius: 8px
padding: 15px 15px 14px
width: 260px
min-width: 260px
max-width: 318px

# 响应式隐藏
# 窗口宽度 < 1120px 时隐藏

# 头部
display: flex
justify-content: space-between
align-items: center
margin-bottom: 10px

## AI 标题
font-size: 15px
font-weight: 600
color: #E6EDF3

## PREVIEW 标签
background: #78350F
color: #F59E0B
font-size: 10px
font-weight: 600
padding: 3px 8px
border-radius: 4px
text-transform: uppercase

# 副标题
font-size: 13px
font-weight: 500
color: #E6EDF3
margin-bottom: 10px

# 描述文字
font-size: 12px
color: #9DA9BB
line-height: 1.5
margin-bottom: 10px

# 功能标签（4 个 Chip）
display: flex
gap: 6px
margin-bottom: 10px

## 单个 Chip
background: #252D38
color: #9DA9BB
font-size: 12px
padding: 4px 10px
border-radius: 4px

# 对话线程
background: #1C2128
border-radius: 6px
padding: 8px
margin-bottom: 10px
flex-grow: 1
overflow-y: auto

## 用户气泡
background: #082F49
color: #E6EDF3
font-size: 12px
padding: 8px 10px
border-radius: 6px
margin-bottom: 8px

## 机器人气泡
background: #252D38
color: #9DA9BB
font-size: 12px
padding: 8px 10px
border-radius: 6px
margin-bottom: 8px

# 输入框区域
background: #1C2128
border: 1px solid #30363D
border-radius: 6px
padding: 9px 8px
display: flex
gap: 8px
align-items: center

## 输入提示
font-size: 12px
color: #6B7785
flex-grow: 1

## 发送按钮（禁用）
background: #30363D
color: #6B7785
font-size: 12px
padding: 6px 12px
border-radius: 4px
cursor: not-allowed
```

#### 系统优势面板规格

```python
# 容器
background: #141922
border: 1px solid #21262D
border-radius: 8px
padding: 16px 16px 8px

# 头部
display: flex
justify-content: space-between
align-items: center
margin-bottom: 8px

## 标题
font-size: 15px
font-weight: 600
color: #E6EDF3

## CORE 标签
background: #0EA5E9
color: #FFFFFF
font-size: 10px
font-weight: 700
padding: 3px 8px
border-radius: 4px
text-transform: uppercase

# 优势条带（4 个优势项）
display: flex
gap: 0
margin-bottom: 8px

## 单个优势项
background: #1C2128
border: 1px solid #21262D
padding: 12px 12px 8px
flex: 1

## 优势项头部
display: flex
align-items: center
gap: 8px
margin-bottom: 5px

### 编号徽章
width: 24px
height: 24px
background: #252D38
color: #6B7785
font-size: 11px
font-weight: 600
border-radius: 4px
display: flex
align-items: center
justify-content: center

### 标题
font-size: 13px
font-weight: 600
color: #E6EDF3

## 优势项正文
font-size: 12px
color: #9DA9BB
line-height: 1.4

# 分隔线（优势项之间）
width: 1px
background: #21262D

# 开发者标签
font-size: 12px
color: #6B7785
text-align: right
padding-top: 8px
```

#### 响应式行为

```python
# >= 1920px（默认）
- AI 预览可见（260-318px）
- 模块卡片 4x2 网格
- 优势条带横向排列

# 1366-1919px
- AI 预览可见（260px 固定）
- 模块卡片 4x2 网格
- 优势条带横向排列

# < 1366px
- AI 预览隐藏
- 模块卡片 4x2 网格（可能拥挤）
- 优势条带横向排列（文字缩略）

# < 1120px（AI 预览隐藏阈值）
- AI 预览立即隐藏
- 主内容区占满
```

---

### 2.4 任务中心（Task Center）

> **设计原则**：轻量级任务中心 + 运行中/失败任务优先 + 明确删除确认

#### 布局结构

```
┌────────────────────────────────────────────────────────────┐
│  Global tasks                                              │
│  任务中心                                                  │
│  查看运行中和最近任务                                      │
│  显示自动化标注流程状态、最近产出和需要处理的问题。        │
│                                                            │
│  ┌────────────────────────────────────────────────────┐   │
│  │  [运行中 2]  [失败 1]  [已完成 5]  [全部 8]       │   │
│  └────────────────────────────────────────────────────┘   │
│                                                            │
│  [刷新] [返回任务中心主页]                                │
│                                                            │
│  ┌────────────────────────────────────────────────────┐   │
│  │ 📊 抽样                        运行中               │   │
│  │ Flow 模式抽样 A9950 产品                            │   │
│  │ 开始时间：2026-08-24 14:23:45                       │   │
│  │ ████████████░░░░░░░░ 60% (3/5)                      │   │
│  │                            [查看详情] [停止任务]    │   │
│  └────────────────────────────────────────────────────┘   │
│                                                            │
│  ┌────────────────────────────────────────────────────┐   │
│  │ 🧠 训练                        失败                 │   │
│  │ 训练 YOLO 模型 - dataset_v3                         │   │
│  │ 开始时间：2026-08-24 13:15:22                       │   │
│  │ 错误：数据集 classes.txt 为空                       │   │
│  │ 输出：D:\runs\train\exp_20260824_131522            │   │
│  │                [查看日志] [跳转到训练页] [删除]    │   │
│  └────────────────────────────────────────────────────┘   │
│                                                            │
│  ┌────────────────────────────────────────────────────┐   │
│  │ 🔍 推理                        已完成               │   │
│  │ 推理未抽样图片 - run_20260824_120345               │   │
│  │ 开始时间：2026-08-24 12:03:45                       │   │
│  │ 完成时间：2026-08-24 12:18:32                       │   │
│  │ 输出：site\.autolabeler\inference_results\run_...  │   │
│  │                [打开输出文件夹] [跳转到复核页]     │   │
│  │                                          [删除]     │   │
│  └────────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────────┘
```

#### 任务卡片规格

```python
# 卡片容器
background: #141922
border: 1px solid #21262D
border-bottom: 2px solid #1A1F29  # 边框模拟阴影
border-radius: 8px
padding: 20px 24px
margin-bottom: 12px

# 卡片头部（模块 + 状态）
display: flex
justify-content: space-between
align-items: center
margin-bottom: 12px

## 左侧：图标 + 模块名
display: flex
align-items: center
gap: 10px

### 模块图标（Emoji 或 Icon）
font-size: 24px
width: 32px
height: 32px

### 模块名称
font-size: 16px
font-weight: 600
color: #E6EDF3

## 右侧：状态标签
# 见下方"任务状态标签规格"

# 任务描述
font-size: 14px
color: #9DA9BB
line-height: 1.5
margin-bottom: 10px
# 长文本：最多 2 行，超出显示省略号
overflow: hidden
text-overflow: ellipsis
display: -webkit-box
-webkit-line-clamp: 2
-webkit-box-orient: vertical

# 时间信息
font-size: 13px
color: #6B7785
margin-bottom: 10px

## 开始时间（必有）
开始时间：2026-08-24 14:23:45

## 完成时间（已完成任务）
完成时间：2026-08-24 14:35:12

## 用时（已完成任务）
用时：11 分 27 秒

# 进度条（仅运行中任务）
background: #1A1F29
height: 8px  # 小进度条，紧凑场景
border-radius: 4px
margin-bottom: 12px
overflow: hidden

## 进度填充
background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                            stop:0 #0EA5E9, stop:1 #0284C7)
height: 100%
# 宽度由进度百分比决定

## 进度文字（显示在进度条旁边）
font-size: 13px
color: #9DA9BB
60% (3/5)  # 百分比 + 当前步骤/总步骤

# 错误信息（失败任务）
background: #7F1D1D  # 错误背景色
border: 1px solid #991B1B
border-radius: 6px
padding: 10px 12px
margin-bottom: 10px

## 错误文字
font-size: 13px
color: #EF4444
line-height: 1.5
# 长错误信息：最多 3 行，超出可展开

# 输出路径（已完成/失败任务）
font-size: 13px
color: #6B7785
margin-bottom: 12px

## 路径文字
输出：D:\runs\train\exp_20260824_131522
# 长路径：截断中间部分，保留头尾
# 完整路径显示在 Tooltip

# 操作按钮组
display: flex
justify-content: flex-end
align-items: center
gap: 8px

## 次要按钮（查看详情/查看日志/跳转到页面）
background: transparent
border: 1px solid #30363D
color: #9DA9BB
font-size: 13px
padding: 7px 14px
border-radius: 6px
cursor: pointer

## 次要按钮 Hover
background: #252D38
border-color: #525964
color: #E6EDF3

## 危险按钮（停止/删除）
background: transparent
border: 1px solid #991B1B
color: #EF4444
font-size: 13px
padding: 7px 14px
border-radius: 6px
cursor: pointer

## 危险按钮 Hover
background: #7F1D1D
border-color: #EF4444
color: #FFFFFF

## 主按钮（打开输出文件夹）
background: #0EA5E9
color: #FFFFFF
font-size: 13px
padding: 7px 14px
border-radius: 6px
border: none
cursor: pointer

## 主按钮 Hover
background: #0284C7
border-bottom: 2px solid #0369A1
```

#### 任务状态标签规格

```python
# 运行中
background: #065F46  # 成功背景色（深色）
color: #10B981       # 成功文字色（亮色）
font-size: 12px
font-weight: 600
padding: 5px 12px
border-radius: 4px
text-transform: uppercase
运行中

# 已完成
background: #1E3A8A  # 信息背景色（深色）
color: #3B82F6       # 信息文字色（亮色）
font-size: 12px
font-weight: 600
padding: 5px 12px
border-radius: 4px
text-transform: uppercase
已完成

# 失败
background: #7F1D1D  # 错误背景色（深色）
color: #EF4444       # 错误文字色（亮色）
font-size: 12px
font-weight: 600
padding: 5px 12px
border-radius: 4px
text-transform: uppercase
失败

# 已停止
background: #92400E  # 警告背景色（深色）
color: #F59E0B       # 警告文字色（亮色）
font-size: 12px
font-weight: 600
padding: 5px 12px
border-radius: 4px
text-transform: uppercase
已停止

# 已中断
background: #92400E  # 警告背景色（深色）
color: #F59E0B       # 警告文字色（亮色）
font-size: 12px
font-weight: 600
padding: 5px 12px
border-radius: 4px
text-transform: uppercase
已中断

# 等待中
background: #252D38  # 中性背景色
color: #9DA9BB       # 中性文字色
font-size: 12px
font-weight: 600
padding: 5px 12px
border-radius: 4px
text-transform: uppercase
等待中
```

#### 任务筛选面板规格

```python
# 容器
background: #1C2128
border: 1px solid #21262D
border-radius: 8px
padding: 16px 20px
margin-bottom: 16px
display: flex
gap: 12px
align-items: center

# 筛选按钮（标签式）
background: transparent
border: 1px solid #30363D
color: #9DA9BB
font-size: 13px
padding: 8px 16px
border-radius: 6px
cursor: pointer
transition: background-color 0.15s ease, border-color 0.15s ease, color 0.15s ease

# 筛选按钮 Hover
background: #252D38
border-color: #525964
color: #E6EDF3

# 筛选按钮 Active（已选中）
background: #082F49  # 品牌色背景
border-color: #0EA5E9
color: #0EA5E9
font-weight: 600

# 筛选按钮内容
[运行中 2]  # 状态名 + 数量
[失败 1]
[已完成 5]
[全部 8]
```

#### 删除确认交互流程

```python
# 步骤 1：用户点击"删除"按钮
# → 弹出模态确认对话框（不是内联确认）

# 模态对话框规格
background: #1C2128
border: 1px solid #30363D
border-radius: 12px
padding: 24px
width: 480px
max-width: 90%
# 阴影：使用真实阴影（临时显示，可接受）
box-shadow: 0 16px 32px rgba(0, 0, 0, 0.6)

## 对话框标题
font-size: 18px
font-weight: 600
color: #E6EDF3
margin-bottom: 12px
删除任务记录？

## 对话框正文
font-size: 14px
color: #9DA9BB
line-height: 1.5
margin-bottom: 20px
此操作将永久删除该任务的记录，包括：
- 任务状态和时间信息
- 错误日志（如果有）
- 任务元数据

注意：不会删除任务的输出文件（如推理结果、训练模型）。

## 任务详情（高亮）
background: #252D38
border-left: 3px solid #EF4444
padding: 12px 14px
border-radius: 4px
margin-bottom: 20px

font-size: 13px
color: #E6EDF3
模块：推理
描述：推理未抽样图片 - run_20260824_120345
开始时间：2026-08-24 12:03:45

## 按钮组
display: flex
justify-content: flex-end
gap: 12px

### 取消按钮
background: transparent
border: 1px solid #30363D
color: #9DA9BB
font-size: 14px
padding: 10px 20px
border-radius: 6px
cursor: pointer

### 取消按钮 Hover
background: #252D38
color: #E6EDF3

### 确认删除按钮
background: #EF4444
color: #FFFFFF
font-size: 14px
font-weight: 600
padding: 10px 20px
border-radius: 6px
border: none
cursor: pointer

### 确认删除按钮 Hover
background: #DC2626
border-bottom: 2px solid #B91C1C

# 步骤 2：用户确认删除
# → 任务卡片淡出消失（200ms 动画）
# → 显示 Toast 提示"任务记录已删除"

# 步骤 3：用户取消删除 / 点击对话框外部
# → 对话框关闭，无任何操作
```

#### 空状态设计

```python
# 当任务列表为空时显示

# 容器
display: flex
flex-direction: column
align-items: center
justify-content: center
padding: 80px 40px
text-align: center

# 空状态图标
font-size: 64px
color: #30363D
margin-bottom: 20px
📋  # 或使用自定义 SVG 图标

# 空状态标题
font-size: 18px
font-weight: 600
color: #9DA9BB
margin-bottom: 10px
暂无任务记录

# 空状态描述
font-size: 14px
color: #6B7785
line-height: 1.5
margin-bottom: 24px
当您运行扫描、抽样、训练、推理等任务时，
任务状态会显示在这里。

# 操作按钮
background: #0EA5E9
color: #FFFFFF
font-size: 14px
font-weight: 500
padding: 10px 20px
border-radius: 6px
border: none
cursor: pointer
返回首页开始工作
```

#### 响应式行为

```python
# >= 1920px（默认）
- 任务卡片完整显示
- 描述文字 2 行
- 按钮全部显示

# 1366-1919px
- 任务卡片完整显示
- 描述文字 2 行
- 按钮全部显示

# < 1366px
- 任务卡片完整显示
- 描述文字 1 行
- 次要按钮可能隐藏到"更多"菜单
- 路径截断更激进
```

#### 注意事项

1. **任务保留期**：任务记录保留 10 天（`_TASK_CENTER_RETENTION_DAYS = 10`），超期自动清理
2. **刷新频率**：任务中心页面打开时，每 1 秒自动刷新任务状态（`_task_center_timer.setInterval(1000)`）
3. **筛选持久化**：筛选状态不持久化，切换页面后重置为"全部"
4. **长路径处理**：任务卡片的路径字段最多显示 60 个字符，超出部分中间截断，完整路径显示在 Tooltip
5. **运行中任务强调**：运行中任务排在列表最前面，失败任务次之，已完成任务最后

---

### 2.5 扫描页（Scan Page）

> **设计说明**：扫描页设计沿用 `UI_SPEC.md` 第 16 节规格，此处不重复详细规格。

**核心设计要点**：
- 低风险操作（只读取目录，不移动/复制文件）
- 简洁表单：站点根目录选择器 + 目录结构说明
- 预检/扫描单按钮
- 结果显示：图片数、类别数、产品组数、mapping.json 路径、classes.txt 路径
- 错误提示：结构不符合时列出冲突路径

**参考实现**：`gui/scan_page.py`

---

### 2.6 抽样页（Sample Page）

> **设计说明**：抽样页设计沿用 `UI_SPEC.md` 第 11 节规格，此处不重复详细规格。

**核心设计要点**：
- Flow / Independent 模式切换（顶部 Segmented Control）
- 抽样策略切换：count | ratio | mixed（Segmented Control）
- 动态表单：根据策略显示/隐藏参数字段
- 预检面板：两列布局（估算结果 | 风险与阻塞）
- 内联确认：空 TXT 清理、覆盖确认
- Independent 模式：XML 标注文件夹 | YOLO 数据集输出选择

**参考实现**：`gui/sample_page.py`

---

### 2.7 标注页 & 复核页（Label & Review Page）

> **设计说明**：标注页和复核页设计沿用 `UI_SPEC.md` 第 17 节规格，此处不重复详细规格。

**核心设计要点（标注页）**：
- 模式切换：Free Labeling | Prediction Review（顶部 Segmented Control，标注页默认 Free Labeling）
- 格式切换：YOLO labeling | VOC labeling（Free Labeling 模式）
- 表单字段：
  - Free Labeling：图片目录、格式、classes.txt（YOLO）、标签输出目录（YOLO）
  - Prediction Review：站点根目录、推理 run 下拉框、Code/Product 树节点
- 预检/启动按钮：验证环境和输入后启动 LabelImg
- 启动成功：显示进程 PID、模式信息（简洁）

**核心设计要点（复核页）**：
- 默认模式：Prediction Review
- Code/Product 树控件：产品名称宽度足够显示完整
- 准备复核按钮：解析原图、预测标签路径、classes.txt，显示摘要
- 缺失标签警告：不阻塞启动，但提示用户
- 准备路径摘要：紧凑显示，长路径用 Tooltip

**参考实现**：`gui/labelimg_page.py`

---

### 2.8 训练页（Train Page）

> **设计说明**：训练页设计沿用 `UI_SPEC.md` 第 12 节规格，此处不重复详细规格。

**核心设计要点**：
- 基础表单：YOLO 数据集目录、初始模型路径、输出目录
- 常用设置（默认可见）：device、epochs、image size、batch size
- device 选项：CPU | GPU | Auto | All GPUs | GPU 0 | GPU 1 | GPU 0+1
- 高级设置（折叠）：patience、workers、optimizer、lr0、box/cls/dfl、scale、cache、固定 run 名、覆盖确认
- 运行时显示：阶段、当前 epoch/总 epoch、已用时间、设备、输出目录
- 指标显示：仅在可用时显示（loss、mAP 等）
- 原始 YOLO 日志：折叠，可展开/复制
- 完成面板：强调 best.pt 和 last.pt，但不自动选择推理模型

**参考实现**：`gui/train_page.py`

---

### 2.9 推理页（Infer Page）

> **设计说明**：推理页设计沿用 `UI_SPEC.md` 第 13 节规格，此处不重复详细规格。

**核心设计要点**：
- Flow 模式来源选择：Unsampled images（默认）| All scanned images（Segmented Control）
- 基础表单：模型路径、推理来源/范围、confidence、IoU、device、batch
- Independent 模式：图片文件夹 + 输出根目录
- 输出行为：自动创建 `run_YYYYMMDD_HHMMSS` 目录
- 预检：显示确切的 run 路径，已有冲突阻塞或重新生成名称
- 高级设置（折叠）：覆盖确认（仅当显式复用固定目录时）
- 运行时显示：进度条（24px 大进度条）、已推理/总数、预估剩余时间

**参考实现**：`gui/infer_page.py`

---

### 2.10 还原页（Restore Page）

> **设计说明**：还原页设计沿用 `UI_SPEC.md` 第 14 节规格，此处不重复详细规格。

**核心设计要点**：
- 来源模式切换：Flow inference run（默认）| Flow dataset labels | Independent restore
- 高风险操作：必须预检
- 预检面板：两列布局（匹配质量 | 写入影响和风险）
- 匹配质量：标签数、匹配图片数、缺失图片数、重复文件名、无效标签、classes 状态
- 写入影响：XML 文件数、目标文件夹、已有 XML 冲突、覆盖状态、阻塞问题、确认操作
- 阻塞规则：已有 XML 默认阻塞、缺失 classes、缺失图片、重复同名图片、无效标签、XML 转换错误
- 标注失败诊断：紧凑摘要 + 详细日志（标签路径、行号、原始 YOLO 行、匹配图片路径和尺寸、类别、像素边界、违反边界）
- 完成面板：写入 XML 数、跳过数、失败数、目标位置

**参考实现**：`gui/restore_page.py`

---

### 2.11 转换页（Convert Page）

> **设计说明**：转换页设计沿用 `UI_SPEC.md` 第 15 节规格，此处不重复详细规格。

**核心设计要点**：
- 主功能优先：Image + XML directory → standard YOLO dataset
- 辅助转换（折叠/次要区域）：YOLO TXT → VOC XML、VOC XML → YOLO TXT
- 主功能表单：源目录（图片 + XML）、输出 YOLO 数据集目录、训练/验证比例、类别来源（从 XML 收集 | 使用 classes.txt）
- 预检流程：分析 → 显示收集/提供的类别列表和顺序 → 用户确认类别顺序 → 转换
- 阻塞规则：XML 解析错误、文件名冲突、无有效图片/XML 对、XML 对象名称不在 classes 中、非空输出（需确认清理）
- 安全规则：复制图片不移动、保留原始文件名、image-without-XML 和 XML-without-image 跳过并计数、不做增量合并、预检失败不写部分数据集
- 结果摘要：有效图片/XML 对数、跳过图片数、跳过 XML 数、类别数、输出路径

**参考实现**：`gui/convert_page.py`

---

### 2.12 空状态设计（Empty State）

> **通用原则**：友好引导 + 明确下一步操作

#### 通用空状态组件规格

```python
# 容器
display: flex
flex-direction: column
align-items: center
justify-content: center
padding: 60px 40px
text-align: center
min-height: 320px

# 空状态图标/插图
width: 120px
height: 120px
margin-bottom: 24px
opacity: 0.6

# 图标类型（根据场景）
# - 任务中心：📋 空剪贴板
# - 推理 run 列表：📂 空文件夹
# - Code/Product 树：🌳 空树
# - 搜索无结果：🔍 放大镜
# - 数据集为空：📸 空相机

# 空状态标题
font-size: 18px
font-weight: 600
color: #9DA9BB
margin-bottom: 12px

# 空状态描述
font-size: 14px
color: #6B7785
line-height: 1.6
margin-bottom: 28px
max-width: 480px

# 主操作按钮（可选）
background: #0EA5E9
color: #FFFFFF
font-size: 14px
font-weight: 500
padding: 10px 24px
border-radius: 6px
border: none
cursor: pointer
margin-bottom: 12px

# 次要操作链接（可选）
font-size: 13px
color: #0EA5E9
text-decoration: none
cursor: pointer
```

#### 场景化空状态文案

**任务中心（无任务）**
```
图标：📋
标题：暂无任务记录
描述：当您运行扫描、抽样、训练、推理等任务时，任务状态会显示在这里。
主按钮：返回首页开始工作
次要链接：查看使用手册
```

**推理 run 列表（无推理结果）**
```
图标：📂
标题：还没有推理运行记录
描述：在推理页运行推理任务后，推理结果会列在这里。每次推理生成一个独立的 run 目录。
主按钮：前往推理页
次要链接：了解推理流程
```

**Code/Product 树（无产品组）**
```
图标：🌳
标题：未找到产品分组
描述：请先在扫描页扫描符合 site / Code / Product / image 结构的目录，生成 mapping.json 后再复核。
主按钮：前往扫描页
次要链接：查看目录结构要求
```

**搜索无结果**
```
图标：🔍
标题：未找到匹配结果
描述：尝试使用不同的关键词，或检查拼写。
主按钮：清除筛选
次要链接：（无）
```

**数据集为空（训练页）**
```
图标：📸
标题：数据集目录为空
描述：训练需要标准 YOLO 数据集，包含 images/train、labels/train 和 data.yaml。请先完成抽样和标注。
主按钮：前往抽样页
次要链接：查看数据集要求
```

**独立模式无 mapping（复核页）**
```
图标：🗺️
标题：独立推理不支持复核模式
描述：复核模式需要 Flow 模式推理结果（依赖 mapping.json）。独立推理请使用标注页的"自由标注"模式。
主按钮：前往标注页
次要链接：了解 Flow vs 独立模式
```

---

### 2.13 Loading 状态设计（Loading State）

> **通用原则**：明确反馈 + 不阻塞理解

#### Spinner（加载旋转器）规格

```python
# 小 Spinner（16x16）- 内联场景
width: 16px
height: 16px
border: 2px solid #30363D
border-top-color: #0EA5E9
border-radius: 50%
animation: spin 0.8s linear infinite

# 使用场景：
# - 按钮内加载状态（"加载中..."）
# - 下拉框选项加载
# - 表单字段验证中

# 中 Spinner（32x32）- 面板场景
width: 32px
height: 32px
border: 3px solid #30363D
border-top-color: #0EA5E9
border-radius: 50%
animation: spin 0.8s linear infinite

# 使用场景：
# - 预检执行中
# - Code/Product 树加载
# - 推理 run 列表加载

# 大 Spinner（48x48）- 全屏场景
width: 48px
height: 48px
border: 4px solid #30363D
border-top-color: #0EA5E9
border-radius: 50%
animation: spin 0.8s linear infinite

# 使用场景：
# - 页面首次加载
# - 长时间数据获取

# 旋转动画
@keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
}

# 颜色
border: 3px solid #E2E8F0      # 轨道颜色（浅灰）
border-top-color: #0EA5E9     # 旋转部分（品牌色）
```

#### Loading 面板（带文字说明）规格

```python
# 容器
display: flex
flex-direction: column
align-items: center
justify-content: center
padding: 40px
text-align: center
min-height: 240px

# Spinner（中等尺寸）
width: 32px
height: 32px
margin-bottom: 16px

# Loading 文字
font-size: 15px
font-weight: 500
color: #9DA9BB
margin-bottom: 8px

# Loading 提示（可选）
font-size: 13px
color: #6B7785
line-height: 1.5
max-width: 360px

# 示例
正在扫描目录...
正在分析 2,345 张图片，请稍候
```

#### 骨架屏（Skeleton）规格

```python
# 适用场景：已知内容结构，数据加载中

# 基础骨架块
background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                            stop:0 #1C2128,
                            stop:0.5 #252D38,
                            stop:1 #1C2128)
background-size: 200% 100%
animation: skeleton-loading 1.5s ease-in-out infinite
border-radius: 4px

# 骨架动画
@keyframes skeleton-loading {
    0% { background-position: 200% 0; }
    100% { background-position: -200% 0; }
}

# 任务卡片骨架（示例）
# 模拟任务卡片结构

## 头部骨架（图标 + 标题 + 状态）
display: flex
justify-content: space-between
margin-bottom: 12px

### 左侧
display: flex
gap: 10px

#### 图标占位
width: 32px
height: 32px
border-radius: 4px
# 骨架样式

#### 标题占位
width: 120px
height: 20px
border-radius: 4px
# 骨架样式

### 右侧状态占位
width: 60px
height: 24px
border-radius: 4px
# 骨架样式

## 描述骨架（2 行）
width: 100%
height: 16px
border-radius: 4px
margin-bottom: 8px
# 骨架样式

width: 80%
height: 16px
border-radius: 4px
margin-bottom: 12px
# 骨架样式

## 按钮组骨架
display: flex
justify-content: flex-end
gap: 8px

### 单个按钮占位
width: 80px
height: 32px
border-radius: 6px
# 骨架样式
```

#### 场景化 Loading 状态

**预检执行中**
```python
# 面板显示
[中等 Spinner]
正在预检...
正在检查目标目录、文件冲突和数据完整性
```

**推理运行中（右侧面板）**
```python
# 使用 24px 大进度条 + 动态文字
[进度条: 45%]
正在推理... 1,234 / 2,500
预计剩余时间：3 分 25 秒
```

**Code/Product 树加载中**
```python
# 树控件区域显示
[中等 Spinner]
正在加载产品树...
```

**训练数据集验证中**
```python
# 面板显示
[中等 Spinner]
正在验证数据集...
正在检查 data.yaml、images 和 labels 目录
```

**页面首次加载（罕见，仅复杂页面）**
```python
# 全屏遮罩（半透明背景）
background: rgba(10, 14, 20, 0.9)
position: fixed
top: 0
left: 0
width: 100%
height: 100%
z-index: 9999

# 居中内容
[大 Spinner]
正在加载页面...
```

#### 按钮 Loading 状态

```python
# 按钮禁用 + Spinner + 文字变化

# 原始按钮
[开始预检]

# Loading 按钮
background: #30363D  # 禁用色
color: #6B7785
cursor: not-allowed
pointer-events: none

# 内容
display: flex
align-items: center
gap: 8px

## 小 Spinner（16x16）
width: 16px
height: 16px
# Spinner 样式

## 文字
预检中...

# 示例代码
def set_button_loading(button: QPushButton, loading: bool, text: str):
    if loading:
        button.setEnabled(False)
        button.setText(f"  {text}...")  # 前置空格为 Spinner 预留空间
        # 添加 Spinner 图标或动画
    else:
        button.setEnabled(True)
        button.setText(text)
```

#### Loading 性能优化

```python
# 避免阻塞 UI 线程
# - 长时间操作（>100ms）必须使用后台线程
# - Spinner 动画使用 CSS animation 或 QPropertyAnimation（GPU 加速）
# - 骨架屏优先于全屏 Loading（提供结构预览）

# 示例：后台任务 + Loading 状态
async def run_preflight_async():
    self.preflight_button.setEnabled(False)
    self.show_loading_spinner()
    try:
        result = await self.worker.preflight()  # 后台线程
        self.show_preflight_result(result)
    finally:
        self.hide_loading_spinner()
        self.preflight_button.setEnabled(True)
```

---

### 2.14 错误状态设计（Error State）

> **设计说明**：错误状态设计沿用 `UI_SPEC.md` 第 8 节规格，此处补充视觉规格。

#### 错误提示面板规格

```python
# 容器
background: #7F1D1D  # 错误背景色（深色）
border: 1px solid #991B1B  # 错误边框色
border-left: 4px solid #EF4444  # 左侧强调条（错误色）
border-radius: 6px
padding: 16px 18px
margin-bottom: 16px

# 错误标题
font-size: 15px
font-weight: 600
color: #EF4444  # 错误文字色（亮色）
margin-bottom: 8px
display: flex
align-items: center
gap: 8px

## 错误图标
font-size: 18px
⚠️ 或 ❌

# 错误主要描述
font-size: 14px
color: #FEE2E2  # 错误次要文字色（浅色）
line-height: 1.6
margin-bottom: 12px

# 用户操作建议
font-size: 14px
color: #FEE2E2
line-height: 1.6
margin-bottom: 12px

## 建议列表
- 第一步操作
- 第二步操作
- 第三步操作

# 技术详情（可展开/折叠）
margin-top: 12px

## 展开/折叠按钮
background: transparent
border: none
color: #EF4444
font-size: 13px
font-weight: 500
cursor: pointer
display: flex
align-items: center
gap: 6px
padding: 6px 0

### 箭头图标
font-size: 10px
transition: transform 0.2s ease
▼  # 折叠状态
▲  # 展开状态

## 技术详情内容（展开后）
background: #5C1B1B  # 更深的错误背景色
border-radius: 4px
padding: 12px 14px
margin-top: 8px
font-size: 13px
font-family: "Consolas", "Monaco", monospace  # 等宽字体
color: #FCA5A5  # 技术文字色（中等亮度）
line-height: 1.5
white-space: pre-wrap
word-break: break-all
max-height: 240px
overflow-y: auto

### 内容示例
错误码: DATASET_INVALID_001
路径: D:\datasets\yolo_v3\data.yaml
异常: FileNotFoundError
堆栈: 
  File "core/trainer.py", line 234, in validate_dataset
    with open(data_yaml_path) as f:
```

#### 错误类型与文案

**数据集错误（训练页）**
```
标题：❌ 数据集验证失败
描述：数据集目录结构不符合 YOLO 要求，无法开始训练。
建议：
- 确认 data.yaml 文件存在且格式正确
- 检查 images/train 和 labels/train 目录是否存在
- 确保至少有一个有效的训练样本
技术详情：（展开显示路径、异常、堆栈）
```

**文件冲突错误（抽样页）**
```
标题：⚠️ 输出目录不为空
描述：目标输出目录已存在文件，继续操作可能覆盖现有数据。
建议：
- 选择一个空目录作为输出
- 或勾选"覆盖确认"选项（确认后会清空目标目录）
- 或手动备份现有数据后再继续
技术详情：（展开显示冲突文件列表）
```

**类别缺失错误（还原页）**
```
标题：❌ classes.txt 未找到
描述：还原 XML 需要 classes.txt 文件，用于将 YOLO 类别编号转换为 XML 对象名称。
建议：
- 在 Flow 模式下，确认站点目录包含 .autolabeler/classes.txt
- 在独立模式下，手动选择 classes.txt 文件
- 或从推理 run 目录复制 classes.txt
技术详情：（展开显示搜索路径）
```

**LabelImg 启动失败（标注页）**
```
标题：❌ 无法启动 LabelImg
描述：LabelImg 环境检查失败，可能是 Python 环境或依赖缺失。
建议：
- 确认已安装 LabelImg：pip install labelImg
- 检查 Python 环境是否激活
- 尝试在命令行手动运行：labelImg
技术详情：（展开显示 Python 路径、错误输出）
```

**推理失败（推理页）**
```
标题：❌ 推理任务失败
描述：模型推理过程中出现错误，部分图片可能未完成推理。
建议：
- 检查模型文件是否完整（best.pt 或 last.pt）
- 确认图片格式支持（jpg、png、bmp）
- 降低 batch size 以减少显存占用
- 切换到 CPU 模式排除显卡驱动问题
技术详情：（展开显示模型路径、失败图片列表、YOLO 错误输出）
```

#### 警告提示面板规格（轻度错误）

```python
# 容器（警告样式，不同于错误）
background: #78350F  # 警告背景色（深色）
border: 1px solid #92400E  # 警告边框色
border-left: 4px solid #F59E0B  # 左侧强调条（警告色）
border-radius: 6px
padding: 14px 16px
margin-bottom: 16px

# 警告标题
font-size: 14px
font-weight: 600
color: #F59E0B  # 警告文字色（亮色）
margin-bottom: 6px
display: flex
align-items: center
gap: 8px

## 警告图标
font-size: 16px
⚠️

# 警告描述
font-size: 13px
color: #FEF3C7  # 警告次要文字色（浅色）
line-height: 1.5
```

#### 警告场景示例

**验证集为空（训练页）**
```
标题：⚠️ 验证集为空
描述：labels/val 目录为空，训练过程中不会计算验证指标。建议在抽样时降低训练比例（如 0.8）以保留验证集。
```

**缺失预测标签（复核页）**
```
标题：⚠️ 部分图片缺失预测标签
描述：23 张图片没有对应的预测 txt 文件。您仍可在 LabelImg 中为这些图片新增标注。
```

**负样本检测（训练页）**
```
标题：⚠️ 检测到负样本
描述：发现 15 个空标签文件（负样本）。YOLO 支持负样本训练，但请确认这些图片确实不包含目标对象。
```

---

## 第三部分：交互规范

### 3.1 确认流程设计

> **设计说明**：确认流程设计沿用 `UI_SPEC.md` 第 6 节规格。

**核心原则**：
- 高风险操作（移动、删除、覆盖、还原、清理）必须预检 + 内联确认
- 预检必须完成才能进入确认阶段
- 内联确认优于模态对话框（任务删除例外）
- 确认面板显示操作影响和不可逆后果

**流程**：
```
填写参数 → 预检按钮 → 预检执行（显示 Loading）→ 预检结果面板（两列）→ 
阻塞问题？
├─ 是 → 禁用执行按钮，提示修正
└─ 否 → 需要确认？
    ├─ 是 → 显示内联确认复选框 + 执行按钮
    └─ 否 → 直接启用执行按钮
```

---

### 3.2 进度反馈设计

> **设计说明**：进度反馈设计沿用 `UI_SPEC.md` 第 6-8 节规格，此处补充视觉细节。

#### 进度条类型选择

**小进度条（8px）**
- 使用场景：任务中心任务卡片、训练页紧凑模式、列表行内
- 无文字标签，纯视觉进度
- 适合次要信息展示

**大进度条（24px）**
- 使用场景：推理页主进度面板、训练页完成百分比显示、转换页转换进度
- 包含文字标签（百分比、当前/总数）
- 适合主要进度展示

#### 进度文字格式

```python
# 百分比 + 当前/总数
"60% (1,234 / 2,500)"

# 百分比 + 步骤/总步骤
"60% (3/5)"

# 预估剩余时间（可选）
"预计剩余时间：3 分 25 秒"

# Epoch 进度（训练页）
"Epoch 45/100"
```

#### 不确定进度（Indeterminate Progress）

```python
# 使用场景：无法预估完成时间的操作
# - 预检执行
# - 目录扫描（未知文件数）
# - 模型加载

# 视觉：使用 Spinner 而非进度条
[中等 Spinner 32x32]
正在预检...
正在检查目标目录、文件冲突和数据完整性
```

---

### 3.3 错误提示设计

> **设计说明**：错误提示设计已在 2.14 节详细定义，此处补充交互行为。

#### 错误显示时机

1. **实时验证错误**：用户输入后立即显示（如路径不存在、数字超出范围）
2. **预检错误**：预检完成后显示在预检结果面板
3. **执行错误**：任务执行失败后显示在结果面板
4. **异步错误**：后台任务失败后在任务中心显示

#### 错误消失时机

1. **实时验证错误**：用户修正输入后自动消失
2. **预检错误**：用户修改参数重新预检后替换
3. **执行错误**：保持显示，直到用户切换页面或重新执行
4. **异步错误**：任务中心显示，用户手动删除任务记录后消失

#### 错误优先级（同时多个错误时）

1. **阻塞性错误**（优先显示）：阻止操作继续的错误
2. **警告**（次要显示）：不阻止操作但需要用户注意
3. **提示**（最后显示）：辅助信息，不影响操作

---

### 3.4 成功反馈设计

> **设计说明**：成功反馈设计沿用 `UI_SPEC.md` 第 8 节规格，此处补充视觉细节。

#### 成功面板规格

```python
# 容器
background: #064E3B  # 成功背景色（深色）
border: 1px solid #065F46  # 成功边框色
border-left: 4px solid #10B981  # 左侧强调条（成功色）
border-radius: 6px
padding: 16px 18px
margin-bottom: 16px

# 成功标题
font-size: 15px
font-weight: 600
color: #10B981  # 成功文字色（亮色）
margin-bottom: 8px
display: flex
align-items: center
gap: 8px

## 成功图标
font-size: 18px
✅ 或 ✓

# 成功描述
font-size: 14px
color: #D1FAE5  # 成功次要文字色（浅色）
line-height: 1.6
margin-bottom: 12px

# 结果摘要
font-size: 13px
color: #D1FAE5
line-height: 1.6
margin-bottom: 12px

## 摘要项（列表）
- 图片数：2,345
- 类别数：12
- 产品组数：8
- mapping.json: site\.autolabeler\mapping.json
- classes.txt: site\.autolabeler\classes.txt

# 操作按钮
background: #10B981
color: #FFFFFF
font-size: 14px
font-weight: 500
padding: 10px 20px
border-radius: 6px
border: none
cursor: pointer

## 示例
打开输出文件夹
前往下一步
返回首页
```

#### Toast 通知（轻量成功提示）

```python
# 使用场景：不需要完整面板的轻量成功反馈
# - 设置保存成功
# - 任务已停止
# - 文件已复制

# 容器
position: fixed
top: 80px
right: 24px
background: #064E3B
border: 1px solid #065F46
border-radius: 8px
padding: 14px 18px
box-shadow: 0 8px 16px rgba(0, 0, 0, 0.4)
z-index: 10000
min-width: 280px
max-width: 420px
animation: toast-slide-in 0.3s ease

# Toast 内容
display: flex
align-items: center
gap: 12px

## 图标
font-size: 20px
color: #10B981
✅

## 文字
font-size: 14px
color: #D1FAE5
line-height: 1.5
默认值已保存

# 自动消失
3 秒后自动淡出消失

# 动画
@keyframes toast-slide-in {
    from {
        transform: translateX(400px);
        opacity: 0;
    }
    to {
        transform: translateX(0);
        opacity: 1;
    }
}
```

---

### 3.5 响应式适配（简化版）

> **简化策略**：3 个断点 + 明确降级规则

#### 断点定义

```python
# 断点枚举
class Breakpoint(Enum):
    LARGE = "large"    # >= 1920px
    MEDIUM = "medium"  # 1366-1919px
    SMALL = "small"    # < 1366px

# 最小支持分辨率
MIN_WINDOW_WIDTH = 1280
MIN_WINDOW_HEIGHT = 720
```

#### 响应式布局规则

**主页（Homepage）**
```python
# >= 1920px (LARGE)
- AI 预览可见（260-318px）
- 模块卡片 4x2 网格
- 优势条带横向排列（4 列）
- Hero 区域完整显示

# 1366-1919px (MEDIUM)
- AI 预览可见（260px 固定）
- 模块卡片 4x2 网格
- 优势条带横向排列（4 列）
- Hero 区域完整显示

# < 1366px (SMALL)
- AI 预览隐藏（自动）
- 模块卡片 4x2 网格（可能拥挤，卡片内边距减小）
- 优势条带横向排列（4 列，文字缩略）
- Hero 区域按钮垂直排列

# < 1120px（AI 预览隐藏阈值，见 workbench.py）
- AI 预览立即隐藏
- 主内容区占满
```

**任务中心（Task Center）**
```python
# >= 1920px (LARGE)
- 任务卡片完整显示
- 描述文字 2 行
- 所有按钮显示
- 路径完整显示（最多 80 字符）

# 1366-1919px (MEDIUM)
- 任务卡片完整显示
- 描述文字 2 行
- 所有按钮显示
- 路径截断（最多 60 字符）

# < 1366px (SMALL)
- 任务卡片紧凑显示
- 描述文字 1 行
- 次要按钮可能隐藏到"更多"菜单
- 路径激进截断（最多 40 字符）
```

**工具页（Tool Pages）**
```python
# >= 1920px (LARGE)
- 左主面板 + 右支持面板（AI 预览或日志）
- 预检面板两列布局
- 表单字段宽度舒适

# 1366-1919px (MEDIUM)
- 左主面板 + 右支持面板（宽度减小）
- 预检面板两列布局（列宽度减小）
- 表单字段宽度适中

# < 1366px (SMALL)
- 仅左主面板（右支持面板隐藏或折叠）
- 预检面板单列布局
- 表单字段最小宽度
```

#### 响应式实现

```python
# 响应式管理器
class ResponsiveManager:
    def __init__(self, main_window: QMainWindow):
        self.main_window = main_window
        self.current_breakpoint = Breakpoint.LARGE
        main_window.installEventFilter(self)
    
    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.Resize:
            self._on_resize(event.size())
        return False
    
    def _on_resize(self, size: QSize):
        width = size.width()
        new_breakpoint = self._get_breakpoint(width)
        
        if new_breakpoint != self.current_breakpoint:
            self.current_breakpoint = new_breakpoint
            self._apply_breakpoint(new_breakpoint)
    
    def _get_breakpoint(self, width: int) -> Breakpoint:
        if width >= 1920:
            return Breakpoint.LARGE
        elif width >= 1366:
            return Breakpoint.MEDIUM
        else:
            return Breakpoint.SMALL
    
    def _apply_breakpoint(self, breakpoint: Breakpoint):
        """应用断点样式"""
        if breakpoint == Breakpoint.LARGE:
            self._apply_large_layout()
        elif breakpoint == Breakpoint.MEDIUM:
            self._apply_medium_layout()
        else:
            self._apply_small_layout()
    
    def _apply_large_layout(self):
        # 显示所有可选元素
        # 设置宽松间距
        pass
    
    def _apply_medium_layout(self):
        # 显示主要元素
        # 设置标准间距
        pass
    
    def _apply_small_layout(self):
        # 隐藏次要元素
        # 设置紧凑间距
        pass
```

---

### 3.6 多语言预留

> **设计说明**：多语言预留沿用 `UI_SPEC.md` 规格，此处不展开。

**预留策略**：
- 所有文字使用变量或资源文件，不硬编码
- 布局使用弹性容器，支持不同文字长度
- 中英文混排时使用正确的字体 fallback
- 日期/时间使用本地化格式

---

### 3.7 长文本显示策略（完整版）

> **通用原则**：优先截断 + Tooltip 显示完整 + 可展开详情

#### 路径截断规则

```python
def truncate_path(path: str, max_length: int = 60) -> str:
    """
    截断路径，保留头部和尾部
    
    示例:
    D:\very\long\path\to\somewhere\output\file.txt
    →
    D:\very\...\output\file.txt
    """
    if len(path) <= max_length:
        return path
    
    # 保留头部 30% 和尾部 60%
    head_length = int(max_length * 0.3)
    tail_length = int(max_length * 0.6)
    
    head = path[:head_length]
    tail = path[-tail_length:]
    
    return f"{head}...{tail}"

# 使用示例
label = QLabel(truncate_path(long_path, 60))
label.setToolTip(long_path)  # 完整路径显示在 Tooltip
```

#### 描述文字截断规则

```python
# CSS 方式（QLabel 支持）
QLabel {
    /* 单行截断 */
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    
    /* 多行截断（2 行） */
    overflow: hidden;
    text-overflow: ellipsis;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
}

# Python 方式
def truncate_text(text: str, max_lines: int = 2, max_chars_per_line: int = 50) -> str:
    """
    截断文字，保留指定行数
    
    示例:
    "这是一段很长的描述文字，包含很多信息，需要截断显示避免占用过多空间。"
    →
    "这是一段很长的描述文字，包含很多信息，需要截断显示..."
    """
    lines = []
    current_line = ""
    
    for word in text.split():
        if len(current_line) + len(word) + 1 <= max_chars_per_line:
            current_line += (" " if current_line else "") + word
        else:
            lines.append(current_line)
            current_line = word
            if len(lines) >= max_lines:
                break
    
    if current_line and len(lines) < max_lines:
        lines.append(current_line)
    
    result = "\n".join(lines)
    if len(lines) >= max_lines or len(text) > len(result):
        result += "..."
    
    return result
```

#### 错误信息截断规则

```python
# 默认显示：简洁摘要（3 行）
# 可展开：完整错误信息 + 技术详情

def format_error_message(error: Exception, max_lines: int = 3) -> tuple[str, str]:
    """
    格式化错误信息
    
    返回：(摘要, 完整详情)
    """
    # 摘要：错误类型 + 主要信息
    summary = f"{error.__class__.__name__}: {str(error)}"
    summary_lines = summary.split("\n")[:max_lines]
    summary_display = "\n".join(summary_lines)
    if len(summary_lines) >= max_lines:
        summary_display += "\n..."
    
    # 完整详情：包含堆栈跟踪
    import traceback
    full_details = traceback.format_exc()
    
    return summary_display, full_details

# 使用示例
try:
    # ... 操作 ...
except Exception as e:
    summary, details = format_error_message(e)
    error_label.setText(summary)
    error_label.setToolTip(details)
    # 可展开按钮显示完整 details
```

#### Tooltip 触发规则

```python
# Tooltip 延迟：500ms（Qt 默认，无需修改）
# Tooltip 显示时长：根据文字长度自动调整（Qt 默认）

# 设置 Tooltip
widget.setToolTip("完整内容...")

# 富文本 Tooltip（支持格式化）
widget.setToolTip("""
<p style="font-size: 13px; line-height: 1.5;">
<b>完整路径：</b><br/>
D:\very\long\path\to\somewhere\output\file.txt
</p>
""")

# 多行 Tooltip
widget.setToolTip(
    "第一行信息\n"
    "第二行信息\n"
    "第三行信息"
)
```

#### 可展开详情组件

```python
class ExpandableDetails(QWidget):
    """可展开详情组件"""
    
    def __init__(self, summary: str, details: str, parent=None):
        super().__init__(parent)
        self.summary = summary
        self.details = details
        self.expanded = False
        self._init_ui()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        # 摘要文字
        self.summary_label = QLabel(self.summary)
        self.summary_label.setWordWrap(True)
        layout.addWidget(self.summary_label)
        
        # 展开/折叠按钮
        self.toggle_button = QPushButton("▼ 显示技术详情")
        self.toggle_button.setObjectName("expandToggleButton")
        self.toggle_button.clicked.connect(self._toggle_details)
        layout.addWidget(self.toggle_button)
        
        # 详情面板（初始隐藏）
        self.details_panel = QTextEdit()
        self.details_panel.setObjectName("errorDetailsPanel")
        self.details_panel.setReadOnly(True)
        self.details_panel.setPlainText(self.details)
        self.details_panel.setMaximumHeight(240)
        self.details_panel.setVisible(False)
        layout.addWidget(self.details_panel)
    
    def _toggle_details(self):
        self.expanded = not self.expanded
        self.details_panel.setVisible(self.expanded)
        self.toggle_button.setText(
            "▲ 隐藏技术详情" if self.expanded else "▼ 显示技术详情"
        )
```

---

## 第四部分：实施建议

### 4.1 实施优先级（调整版）

> **修订原则**：设计 Token → 外壳 → 补充设计 → 功能页

#### Phase 1：视觉基础（1 周）

**目标**：建立设计系统，为所有页面提供统一基础

```
├─ 设计 Token 转换（1 天）
│  ├─ 色彩系统 Python 常量
│  ├─ 字体系统配置
│  ├─ 间距/圆角常量
│  └─ 组件阴影决策表
│
├─ QSS 主题文件编写（2 天）
│  ├─ 浅色主题完整 QSS
│  ├─ 组件样式（按钮/输入框/卡片/标签）
│  └─ 动画/过渡定义
│
├─ 边框模拟阴影实现（1 天）
│  ├─ 静态卡片边框样式
│  ├─ Hover 状态增强
│  └─ 组件对照表验证
```

**验收标准**：
- [ ] 浅色主题完整 QSS 文件
- [ ] 边框模拟阴影视觉效果达标
- [ ] 所有组件使用统一 Design Token

#### Phase 2：外壳重构（1 周）

**目标**：完成登录页、主页、导航栏的视觉重构

```
├─ 导航栏（2 天）
│  ├─ 宽度增加到 240px
│  ├─ 修复选中状态跳动（透明边框占位）
│  ├─ 编号徽章视觉分离
│  └─ Hover/选中状态优化
│
├─ 登录页（2 天）
│  ├─ 左右布局（40% / 60%）
│  ├─ 品牌区渐变背景 + 统计卡片
│  ├─ 表单卡片真实阴影
│  ├─ SSO 按钮（禁用状态）
│  └─ 保留测试契约组件
│
└─ 主页（3 天）
   ├─ Hero 区域重设计
   ├─ 8 个模块卡片（4x2 网格）
   ├─ AI 预览面板（响应式隐藏）
   ├─ 系统优势条带（4 列）
   └─ 响应式适配（3 个断点）
```

**验收标准**：
- [ ] 导航栏选中状态无跳动
- [ ] 登录页视觉符合企业级定位
- [ ] 主页 AI 预览在 < 1120px 时自动隐藏
- [ ] 3 个响应式断点测试通过

#### Phase 3：补充缺失设计（3 天）

**目标**：完成设计文档中标记为"补充完整"的章节

```
├─ 任务中心详细设计（1 天）
│  ├─ 任务卡片布局实现
│  ├─ 任务状态标签组件
│  ├─ 删除确认对话框
│  └─ 空状态设计
│
├─ 空状态/Loading 组件库（1 天）
│  ├─ 通用空状态组件
│  ├─ Spinner 组件（3 个尺寸）
│  ├─ Loading 面板
│  └─ 骨架屏组件
│
└─ 长文本省略规则实现（1 天）
   ├─ 路径截断函数
   ├─ 描述文字截断
   ├─ 错误信息可展开组件
   └─ Tooltip 统一设置
```

**验收标准**：
- [ ] 任务中心完整功能实现
- [ ] 空状态/Loading 组件库可复用
- [ ] 长文本在所有页面正确截断

#### Phase 4：功能页重构（2-3 周）

**目标**：按 UI_SPEC.md 优先级重构 8 个功能页

```
优先级顺序（按 UI_SPEC.md 第 10 节）:
1. 抽样页（Sample）     - 3 天
2. 训练页（Train）      - 3 天
3. 推理页（Infer）      - 3 天
4. 还原页（Restore）    - 3 天
5. 转换页（Convert）    - 2 天
6. 扫描页（Scan）       - 1 天
7. 标注页（Label）      - 2 天
8. 复核页（Review）     - 2 天

每个页面实施步骤：
├─ 应用新主题样式
├─ 调整布局和间距
├─ 集成空状态/Loading 组件
├─ 应用长文本截断规则
├─ 响应式适配测试
└─ 主题切换测试
```

**验收标准**：
- [ ] 所有功能页视觉统一
- [ ] 预检/Loading/错误/成功状态完整
- [ ] 响应式适配在 3 个断点测试通过
- [ ] 主题切换无视觉问题

---

### 4.2 技术实现路径（性能优化）

#### 阴影系统实施

```python
# 1. 定义阴影工具函数
def apply_border_shadow(widget: QWidget):
    """应用边框模拟阴影（浅色主题）"""
    widget.setStyleSheet("""
        border: 1px solid #E2E8F0;
        border-bottom: 2px solid #CBD5E1;
    """)

def apply_real_shadow(widget: QWidget, size: str = "medium"):
    """应用真实阴影（仅必要场景）"""
    shadow = QGraphicsDropShadowEffect()
    if size == "small":
        shadow.setBlurRadius(4)
        shadow.setOffset(0, 2)
    elif size == "medium":
        shadow.setBlurRadius(8)
        shadow.setOffset(0, 4)
    else:  # large
        shadow.setBlurRadius(16)
        shadow.setOffset(0, 8)
    shadow.setColor(QColor(0, 0, 0, 13))  # 5% 不透明度（浅色主题）
    widget.setGraphicsEffect(shadow)

# 2. 按组件对照表应用
# 主页模块卡片：边框模拟
for card in self.home_module_buttons:
    apply_border_shadow(card)

# 登录页表单卡片：真实阴影
apply_real_shadow(self.login_card, "medium")
```

#### 响应式实施

```python
# 1. 实现 ResponsiveManager（见 3.5 节）

# 2. 集成到主窗口
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.responsive_manager = ResponsiveManager(self)
        self.setMinimumSize(MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT)
    
    def resizeEvent(self, event):
        super().resizeEvent(event)
        # ResponsiveManager 已通过 eventFilter 处理
```

---

### 4.3 验证检查点（补充完整）

#### 视觉验证

**色彩对比度**
```
工具：WebAIM Contrast Checker
标准：WCAG AA（4.5:1 for normal text, 3:1 for large text）

检查项：
[ ] 浅色主题 - 主要文字 vs 背景（#0F172A on #FFFFFF）
[ ] 浅色主题 - 次要文字 vs 背景（#475569 on #FFFFFF）
[ ] 浅色主题 - 辅助文字 vs 背景（#94A3B8 on #FFFFFF）
[ ] 浅色主题 - 品牌色 vs 背景（#0EA5E9 on #FFFFFF）
```

**字体渲染**
```
检查项：
[ ] Windows - 微软雅黑 UI 正常显示
[ ] Windows - 中英文混排无字体回退问题
[ ] macOS - PingFang SC 正常显示
[ ] 所有字号清晰可读（12-28px）
[ ] 字重正确应用（400/500/600/700）
```

**间距与对齐**
```
检查项：
[ ] 8px 基础网格严格遵守
[ ] 卡片内边距符合规格（16/24/32px）
[ ] 按钮内边距符合规格
[ ] 垂直间距一致性
[ ] 水平对齐无偏移
```

**阴影效果**
```
检查项：
[ ] 静态卡片使用边框模拟阴影
[ ] Hover 状态阴影增强流畅
[ ] 登录页卡片真实阴影正确渲染
[ ] 弹窗/对话框阴影正确渲染
[ ] 无不必要的 QGraphicsDropShadowEffect（性能）
```

#### 功能验证

**主题切换**
```
检查项：
[ ] 深色 → 浅色切换流畅无闪烁
[ ] 浅色 → 深色切换流畅无闪烁
[ ] 切换时间 < 300ms
[ ] 所有组件颜色正确更新
[ ] 主题选择持久化（重启后保持）
[ ] 进度条/Spinner 不参与过渡动画
```

**响应式适配**
```
检查项：
[ ] 1920px - 所有元素完整显示
[ ] 1600px - AI 预览可见
[ ] 1366px - AI 预览可见
[ ] 1280px - AI 预览隐藏，主内容完整
[ ] 1120px - AI 预览自动隐藏阈值正确
[ ] 各断点切换无布局错位
[ ] 最小窗口尺寸（1280x720）可用
```

**任务中心**
```
检查项：
[ ] 任务列表正确显示（运行中/失败/已完成）
[ ] 任务状态标签颜色正确
[ ] 进度条（8px）正确渲染
[ ] 长路径正确截断 + Tooltip 显示完整
[ ] 删除确认对话框流程完整
[ ] 空状态显示正确
[ ] 自动刷新（1 秒）正常工作
[ ] 筛选功能正常
```

**空状态/Loading**
```
检查项：
[ ] 所有页面空状态设计一致
[ ] Spinner 动画流畅（60fps）
[ ] Loading 文字说明清晰
[ ] 骨架屏结构准确
[ ] 按钮 Loading 状态正确禁用
```

**长文本处理**
```
检查项：
[ ] 路径截断保留头尾
[ ] 描述文字多行截断正确
[ ] 错误信息可展开/折叠
[ ] Tooltip 延迟 500ms 触发
[ ] Tooltip 内容完整
[ ] 富文本 Tooltip 格式正确
```

#### 性能验证

**渲染性能**
```
工具：QTimer + fps 计数器

检查项：
[ ] 主页渲染 < 500ms
[ ] 页面切换 < 200ms
[ ] 卡片 Hover 动画流畅（60fps）
[ ] 进度条更新流畅（60fps）
[ ] 任务中心自动刷新不卡顿
[ ] 无不必要的重绘
```

**内存占用**
```
工具：Windows Task Manager / Activity Monitor

检查项：
[ ] 启动后内存 < 150MB
[ ] 页面切换无内存泄漏
[ ] 长时间运行（1 小时）内存稳定
```

**动画降级**
```
检查项：
[ ] DISABLE_ANIMATIONS = True 时所有动画禁用
[ ] 降级模式下功能完整可用
[ ] 性能弱设备（<30fps）自动降级
```

#### 兼容性验证

**操作系统**
```
检查项：
[ ] Windows 10 - 完整测试
[ ] Windows 11 - 完整测试
[ ] macOS - 字体/布局验证
```

**分辨率**
```
检查项：
[ ] 1920x1080 - 主要测试分辨率
[ ] 1366x768 - 笔记本常见分辨率
[ ] 1280x720 - 最小支持分辨率
[ ] 2560x1440 - 高分屏测试
[ ] 3840x2160 - 4K 测试
```

---

### 4.4 资源需求

#### 人力需求

```
UI 开发工程师（Python/PySide6）：1 人 × 5-6 周
├─ Phase 1：视觉基础（1 周）
├─ Phase 2：外壳重构（1 周）
├─ Phase 3：补充设计（3 天）
└─ Phase 4：功能页重构（2-3 周）

UI 测试工程师：0.5 人 × 2 周
├─ 视觉回归测试
├─ 响应式测试
├─ 主题切换测试
└─ 性能测试

设计师（可选，设计审查）：0.2 人 × 6 周
├─ 设计 Token 审查
├─ 实施过程视觉 QA
└─ 最终验收
```

#### 工具需求

```
开发工具：
- Python 3.10+
- PySide6 6.5+
- Qt Designer（可选，用于快速原型）
- Git

设计工具（设计师使用）：
- Figma / Sketch（设计原型，可选）
- 颜色对比度检查工具（WebAIM Contrast Checker）
- 截图/标注工具

测试工具：
- Windows 10/11 测试环境
- macOS 测试环境（可选）
- 多分辨率显示器 或 虚拟分辨率工具
- 性能监控工具（Task Manager / Activity Monitor）
```

#### 时间需求

```
总时间：5-6 周
├─ Phase 1：1 周
├─ Phase 2：1 周
├─ Phase 3：3 天
├─ Phase 4：2-3 周
└─ 测试与修复：分散在各 Phase
```

---

### 4.5 风险与应对（补充完整）

#### 高风险

**风险 1：阴影系统双轨制维护成本高**
```
描述：边框模拟 + 真实阴影混用，开发者难以决策，调试困难
影响：实施延期，视觉不一致
概率：中（30%）
影响：中

应对措施：
- 预案 A：严格遵守组件对照表（1.5 节），不允许自由发挥
- 预案 B：编写阴影工具函数封装（4.2 节），降低使用复杂度
- 预案 C：Phase 1 完成后全面审查，统一调整
- 降级方案：全部使用边框模拟，放弃真实阴影
```

#### 中风险

**风险 2：响应式适配测试工作量超预期**
```
描述：3 个断点 × 12 个页面 = 36+ 场景，测试时间不足
影响：实施延期，部分页面响应式不完整
概率：高（50%）
影响：中

应对措施：
- 预案 A：优先测试主页、任务中心、抽样页（高频页面）
- 预案 B：自动化响应式测试脚本（截图对比）
- 预案 C：降低最小支持分辨率到 1366x768，减少 SMALL 断点测试
- 降级方案：只支持 >= 1366px 分辨率
```

**风险 3：空状态/Loading/错误状态设计不一致**
```
描述：补充设计时间紧张，组件复用不足，视觉不统一
影响：用户体验不一致，维护成本高
概率：中（40%）
影响：中

应对措施：
- 预案 A：Phase 3 优先完成组件库，强制所有页面复用
- 预案 B：设计审查（设计师介入），确保一致性
- 预案 C：建立组件使用文档，明确使用场景
- 降级方案：简化设计，使用统一的通用模板
```

#### 低风险

**风险 4：色彩对比度不符合 WCAG AA 标准**
```
描述：部分颜色组合对比度不足 4.5:1
影响：可访问性不达标，视觉疲劳
概率：低（20%）
影响：低

应对措施：
- 预案 A：Phase 1 使用对比度检查工具验证所有颜色组合
- 预案 B：调整辅助文字颜色（#94A3B8 → #64748B）
- 预案 C：提供"高对比度模式"（可选）
```

**风险 5：字体回退问题（macOS）**
```
描述：macOS 上微软雅黑不可用，PingFang SC 渲染效果与设计稿差异大
影响：macOS 用户视觉体验下降
概率：低（20%）
影响：低

应对措施：
- 预案 A：为 macOS 单独调整字体 fallback 顺序
- 预案 B：macOS 测试时微调字重和字号
- 预案 C：接受平台差异，不做特殊适配
```

#### 风险监控

```
每周风险评审：
- 跟踪高风险项进展
- 更新风险概率和影响
- 及时启动应对措施

关键里程碑检查：
- Phase 1 结束：阴影系统性能达标？
- Phase 2 结束：响应式适配策略可行？
- Phase 3 结束：组件库复用率 > 80%？
- Phase 4 中期：功能页进度是否按计划？
```

---

## 附录

### A. 设计 Token 速查表

```python
# 色彩（浅色主题）
BRAND_PRIMARY = "#0EA5E9"
TEXT_PRIMARY = "#0F172A"
TEXT_SECONDARY = "#475569"
TEXT_TERTIARY = "#94A3B8"
BG_APP = "#F8FAFC"
BG_SURFACE = "#FFFFFF"
BG_ELEVATED = "#FFFFFF"

# 字体
FONT_SIZE_H1 = 28
FONT_SIZE_BODY = 14
FONT_WEIGHT_SEMIBOLD = 600

# 间距
SPACE_2 = 8
SPACE_4 = 16
SPACE_5 = 24

# 圆角
RADIUS_MD = 6
RADIUS_LG = 8
```

### B. 组件样式速查表

```python
# 主按钮
QPushButton#primaryButton {
    background-color: #0EA5E9;
    color: #FFFFFF;
    border: none;
    border-radius: 6px;
    padding: 10px 20px;
    font-size: 14px;
    font-weight: 500;
}

# 次要按钮
QPushButton#secondaryButton {
    background: transparent;
    border: 1px solid #30363D;
    color: #9DA9BB;
    border-radius: 6px;
    padding: 10px 20px;
    font-size: 14px;
}

# 输入框
QLineEdit#formInput {
    background: #1A1F29;
    border: 1px solid #30363D;
    border-radius: 6px;
    padding: 10px 12px;
    font-size: 14px;
    color: #E6EDF3;
}
```

### C. 常见问题与解答

**Q1：为什么优先使用边框模拟阴影而非真实阴影？**
A：QGraphicsDropShadowEffect 性能开销大，尤其在大量组件时会导致渲染卡顿。边框模拟阴影性能最佳，视觉效果也足够专业。

**Q2：主题切换为什么不能更快（<100ms）？**
A：PySide6 QSS 更新涉及大量组件重绘，100ms 物理极限难以突破。300ms 已经是优化后的合理目标。

**Q3：为什么不支持 < 1280px 分辨率？**
A：桌面应用主要用户使用 >= 1366px 分辨率，1280x720 已是极限最小支持。更小分辨率需要重新设计布局结构，成本过高。

**Q4：为什么任务中心不持久化筛选状态？**
A：任务中心是轻量级设计，用户每次进入都希望看到"全部"视图。持久化会增加复杂度且价值有限。

**Q5：为什么不实现真正的 AI 助手功能？**
A：AI 助手属于"预览功能"，当前版本只提供 UI 占位。实际功能需要后端 LLM 集成和 Agent 框架，超出 UI 重构范围。

---

**文档版本**：v2.1 (性能优化版)  
**最后更新**：2026-08-24  
**作者**：设计团队  
**审阅**：开发团队  

**变更历史**：
- v2.1 (2026-08-24): 补充完整任务中心、空状态、Loading、错误状态、交互规范、实施建议、风险应对
- v2.0 (2026-08-23): 初始版本，基础设计系统和部分页面规格

---

