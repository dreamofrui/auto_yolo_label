# 登录页优化方案

## 现状分析

### 发现两个登录实现：

1. **`gui/login_studio.py`** - 独立文件（未使用）
   - Git: `ffb4eef feat: Wayfinder LoginStudio #21`
   - 特点：40/60布局、主题切换器、现代设计
   - 状态：**孤立代码，未被任何地方引用**

2. **`gui/workbench.py` 内嵌登录** - 当前使用版本
   - Git: `50b59ee feat(gui): redesign login page with painpoint-driven narrative`
   - 特点：包含 `loginWorkflowPanel` 和 `loginBoundaryPanel` 测试组件
   - 状态：**正在生产使用**

## 决策：删除 login_studio.py，增强 workbench 内嵌登录

### 理由：

1. **最小风险** - workbench 已在生产使用，基础稳定
2. **符合设计规范** - 设计规范 2.2 节要求保留测试面板（workbench 已有）
3. **避免架构变动** - 不需要重构 workbench 的初始化流程
4. **增量改进** - 在稳定基础上添加统计卡片，而非整体替换
5. **无隐藏依赖** - login_studio.py 完全孤立，删除无影响

### 实施计划：

#### 第一步：删除孤立代码
```bash
git rm gui/login_studio.py
```

#### 第二步：增强 workbench 登录页

在 `workbench.py` 的 `_build_login_page()` 方法中添加：

**1. 添加统计数据展示**（在 workflow panel 和 boundary panel 之间）
```python
# 在 story_layout 中，self.login_workflow_panel 之后插入：

self.login_stats = QWidget()
stats_layout = QHBoxLayout(self.login_stats)
stats_layout.setContentsMargins(0, 0, 0, 0)
stats_layout.setSpacing(56)

stats_data = [
    ("95%", "标注准确率"),
    ("10x", "效率提升"),
    ("50K+", "处理图像")
]

for i, (value, label) in enumerate(stats_data):
    stat_widget = QWidget()
    stat_widget.setObjectName("loginStatReadout")
    stat_vbox = QVBoxLayout(stat_widget)
    stat_vbox.setContentsMargins(0, 0, 0, 0)
    stat_vbox.setSpacing(6)
    stat_vbox.setAlignment(Qt.AlignmentFlag.AlignCenter)
    
    stat_value = QLabel(value)
    stat_value.setObjectName("loginStatValue")
    stat_value.setAlignment(Qt.AlignmentFlag.AlignCenter)
    
    stat_label = QLabel(label)
    stat_label.setObjectName("loginStatLabel")
    stat_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    
    stat_vbox.addWidget(stat_value)
    stat_vbox.addWidget(stat_label)
    stats_layout.addWidget(stat_widget)
    
    # 添加分隔线（最后一个不加）
    if i < len(stats_data) - 1:
        separator = QFrame()
        separator.setObjectName("loginStatSeparator")
        separator.setFrameShape(QFrame.Shape.VLine)
        separator.setFixedWidth(1)
        separator.setFixedHeight(60)
        stats_layout.addWidget(separator)

# 插入到布局中：
story_layout.addWidget(self.login_workflow_panel, 0)
story_layout.addSpacing(24)  # 新增
story_layout.addWidget(self.login_stats)  # 新增
story_layout.addSpacing(24)  # 新增
story_layout.addWidget(self.login_boundary_panel, 0)
```

**2. 更新 QSS 样式**（在 `_stylesheet()` 方法中添加）
```css
/* 统计数据 - 工业仪表风格 */
#loginStatReadout {
    background: transparent;
}

#loginStatValue {
    font-size: 40px;
    font-weight: 700;
    color: #0EA5E9;
    letter-spacing: -1px;
}

#loginStatLabel {
    font-size: 14px;
    font-weight: 400;
    color: #6B7785;
    letter-spacing: 0.3px;
}

#loginStatSeparator {
    background: #21262D;
    border: none;
}
```

**3. 优化品牌区文案**（可选，与设计规范对齐）
```python
# 更新 headline
headline = QLabel("AI 驱动的\n智能标注平台")

# 更新 copy
copy = QLabel(
    "使用先进的机器学习技术，自动完成数据标注任务，"
    "将标注效率提升 10 倍，助力制造业质检团队实现智能化升级。"
)
```

#### 第三步：移除主题切换器

**问题：** login_studio.py 有主题切换器，但设计规范明确主题切换应在主应用侧边栏，不在登录页。

**操作：** workbench 登录页已经没有主题切换器，无需额外操作。

### 优势分析：

✅ **鲁棒性**
- 在稳定基础上增量添加，不破坏现有流程
- 保留测试面板（设计规范要求）
- 不引入新的组件依赖

✅ **维护性**
- 单一登录实现，无重复代码
- 统一的样式管理（在 workbench stylesheet 中）
- 清晰的代码组织

✅ **设计合规性**
- 符合设计规范 2.2 节要求
- 保留测试契约组件
- 添加统计数据展示

❌ **不采纳 login_studio.py 的原因：**
- 未集成到应用流程
- 缺少测试面板（设计规范要求保留）
- 需要大规模重构 workbench 初始化
- 引入主题切换器在登录页（不符合设计规范）

## 实施检查清单

- [ ] 确认 login_studio.py 无其他引用（已确认：无）
- [ ] 删除 gui/login_studio.py
- [ ] 在 workbench.py 添加统计数据组件
- [ ] 更新 workbench QSS 添加统计样式
- [ ] 测试登录页显示（测试面板保持隐藏）
- [ ] 验证响应式行为（< 1366px 时调整）
- [ ] 提交改动：`feat: add statistics to login page per UI spec v2.2`

## 风险评估

**低风险：**
- 删除未使用的文件
- 在已有容器中添加新组件
- 纯视觉改进，不改变逻辑

**注意事项：**
- 测试面板必须保持 `setVisible(False)` 或通过 QSS 隐藏
- 统计数据为静态展示，不需要数据绑定
- 保持现有布局结构，只添加新元素
