# Login Page Implementation Guide

## Design Overview

The login page uses a 40/60 split layout with an industrial precision aesthetic:

- **Left (40%)**: Brand story with gradient background, statistics as industrial readouts
- **Right (60%)**: Elevated form card with shadow, centered on the surface

## Key Design Decisions

### 1. Statistics as Industrial Readouts
Instead of typical SaaS marketing cards with heavy backgrounds, the statistics are presented as **precision instruments**:
- Minimal chrome (no card backgrounds)
- Tabular numbers in brand color
- Subtle vertical dividers between metrics
- Data-forward presentation appropriate for manufacturing QA context

### 2. Visual Hierarchy
- Brand wordmark establishes identity
- Large headline creates impact
- Statistics provide credibility without competing for attention
- Form card uses real shadow (acceptable for single static element)

### 3. Interaction Design
- Focus states use outline instead of shadow (performance)
- Button hover uses background color change + subtle transform
- Disabled SSO button clearly communicates unavailability

## PySide6 Implementation Changes

### Structure Updates to `login_studio.py`

```python
def _build_story(self) -> QWidget:
    """Left brand section with statistics."""
    frame = QFrame()
    frame.setObjectName("brandSection")
    
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(56, 56, 56, 64)
    layout.setSpacing(0)
    
    # Brand wordmark
    brand = QLabel("Auto Labeler")
    brand.setObjectName("brandWordmark")
    
    # Main headline
    headline = QLabel("AI 驱动的\n智能标注平台")
    headline.setObjectName("brandHeadline")
    headline.setWordWrap(True)
    
    # Description
    description = QLabel("使用先进的机器学习技术，自动完成数据标注任务，"
                        "将标注效率提升 10 倍，助力制造业质检团队实现智能化升级。")
    description.setObjectName("brandDescription")
    description.setWordWrap(True)
    description.setMaximumWidth(480)
    
    # Statistics container
    stats_container = QWidget()
    stats_layout = QHBoxLayout(stats_container)
    stats_layout.setContentsMargins(0, 0, 0, 0)
    stats_layout.setSpacing(56)
    
    # Create three stat readouts
    stats_data = [
        ("95%", "标注准确率"),
        ("10x", "效率提升"),
        ("50K+", "处理图像")
    ]
    
    for i, (value, label) in enumerate(stats_data):
        stat_widget = QWidget()
        stat_widget.setObjectName("statReadout")
        stat_layout = QVBoxLayout(stat_widget)
        stat_layout.setContentsMargins(0, 0, 0, 0)
        stat_layout.setSpacing(6)
        stat_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        stat_value = QLabel(value)
        stat_value.setObjectName("statValue")
        stat_value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        stat_label = QLabel(label)
        stat_label.setObjectName("statLabel")
        stat_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        stat_layout.addWidget(stat_value)
        stat_layout.addWidget(stat_label)
        
        stats_layout.addWidget(stat_widget)
        
        # Add separator line after first two stats
        if i < len(stats_data) - 1:
            separator = QFrame()
            separator.setObjectName("statSeparator")
            separator.setFrameShape(QFrame.Shape.VLine)
            separator.setFixedWidth(1)
            separator.setFixedHeight(60)
            stats_layout.addWidget(separator)
    
    # Footer
    footer = QLabel("© 2026 Auto Labeler. 企业级 AI 标注解决方案")
    footer.setObjectName("brandFooter")
    
    # Layout assembly
    layout.addWidget(brand)
    layout.addSpacing(90)
    layout.addWidget(headline)
    layout.addSpacing(24)
    layout.addWidget(description)
    layout.addSpacing(64)
    layout.addWidget(stats_container)
    layout.addStretch(1)
    layout.addWidget(footer)
    
    return frame

def _build_form(self) -> QWidget:
    """Right form section with elevated card."""
    frame = QFrame()
    frame.setObjectName("formSection")
    
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(80, 80, 80, 80)
    layout.setSpacing(0)
    layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
    
    # Form card container
    card = QFrame()
    card.setObjectName("formCard")
    card.setMaximumWidth(440)
    
    card_layout = QVBoxLayout(card)
    card_layout.setContentsMargins(48, 48, 48, 48)
    card_layout.setSpacing(0)
    
    # Title
    title = QLabel("登录")
    title.setObjectName("formTitle")
    
    # Subtitle
    subtitle = QLabel("欢迎回来,请输入您的凭据继续使用")
    subtitle.setObjectName("formSubtitle")
    subtitle.setWordWrap(True)
    
    # Username field
    username_label = QLabel("用户名")
    username_label.setObjectName("formLabel")
    username = QLineEdit()
    username.setPlaceholderText("输入您的用户名")
    username.setObjectName("formInput")
    
    # Password field
    password_label = QLabel("密码")
    password_label.setObjectName("formLabel")
    password = QLineEdit()
    password.setPlaceholderText("输入您的密码")
    password.setEchoMode(QLineEdit.EchoMode.Password)
    password.setObjectName("formInput")
    
    # Forgot password link
    forgot = QLabel('<a href="#" style="color: #0EA5E9; text-decoration: none;">忘记密码？</a>')
    forgot.setObjectName("forgotLink")
    forgot.setOpenExternalLinks(False)
    forgot.setAlignment(Qt.AlignmentFlag.AlignRight)
    
    # Login button
    self.login_button = QPushButton("登录")
    self.login_button.setObjectName("btnPrimary")
    self.login_button.clicked.connect(self.login_requested.emit)
    
    # Enterprise label
    enterprise_label = QLabel("企业用户")
    enterprise_label.setObjectName("enterpriseLabel")
    
    # SSO button (disabled)
    sso = QPushButton("使用 SSO 登录")
    sso.setObjectName("btnSecondary")
    sso.setEnabled(False)
    
    # Layout assembly
    card_layout.addWidget(title)
    card_layout.addSpacing(12)
    card_layout.addWidget(subtitle)
    card_layout.addSpacing(48)
    card_layout.addWidget(username_label)
    card_layout.addSpacing(8)
    card_layout.addWidget(username)
    card_layout.addSpacing(24)
    card_layout.addWidget(password_label)
    card_layout.addSpacing(8)
    card_layout.addWidget(password)
    card_layout.addSpacing(10)
    card_layout.addWidget(forgot)
    card_layout.addSpacing(16)
    card_layout.addWidget(self.login_button)
    card_layout.addSpacing(32)
    card_layout.addWidget(enterprise_label)
    card_layout.addSpacing(12)
    card_layout.addWidget(sso)
    
    layout.addWidget(card)
    
    return frame
```

### QSS Stylesheet

Create a new file `gui/styles/login_page.qss`:

```css
/* ========== BRAND SECTION ========== */
#brandSection {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                stop:0 #0A0E14, stop:1 #141922);
}

#brandWordmark {
    font-size: 32px;
    font-weight: 700;
    color: #E6EDF3;
    letter-spacing: -0.5px;
}

#brandHeadline {
    font-size: 36px;
    font-weight: 700;
    line-height: 1.3;
    color: #E6EDF3;
    letter-spacing: -0.5px;
}

#brandDescription {
    font-size: 16px;
    font-weight: 400;
    line-height: 1.7;
    color: #9DA9BB;
}

/* Statistics - Industrial Readout Style */
#statReadout {
    background: transparent;
}

#statValue {
    font-size: 40px;
    font-weight: 700;
    color: #0EA5E9;
    letter-spacing: -1px;
}

#statLabel {
    font-size: 14px;
    font-weight: 400;
    color: #6B7785;
    letter-spacing: 0.3px;
}

#statSeparator {
    background: #21262D;
    border: none;
}

#brandFooter {
    font-size: 13px;
    color: #6B7785;
    line-height: 1.5;
}

/* ========== FORM SECTION ========== */
#formSection {
    background: #141922;
}

#formCard {
    background: #1C2128;
    border: 1px solid #30363D;
    border-radius: 12px;
    /* Note: QGraphicsDropShadowEffect applied in Python code for real shadow */
}

#formTitle {
    font-size: 28px;
    font-weight: 700;
    color: #E6EDF3;
    letter-spacing: -0.5px;
}

#formSubtitle {
    font-size: 14px;
    color: #9DA9BB;
    line-height: 1.5;
}

#formLabel {
    font-size: 14px;
    font-weight: 500;
    color: #E6EDF3;
}

#formInput {
    background: #1A1F29;
    border: 1px solid #30363D;
    border-radius: 6px;
    padding: 12px 14px;
    font-size: 14px;
    color: #E6EDF3;
}

#formInput::placeholder {
    color: #6B7785;
}

#formInput:focus {
    border: 1px solid #0EA5E9;
    outline: 2px solid rgba(14, 165, 233, 0.2);
}

#forgotLink {
    font-size: 13px;
    color: #0EA5E9;
}

#forgotLink:hover {
    color: #0284C7;
}

#btnPrimary {
    background: #0EA5E9;
    color: #FFFFFF;
    border: none;
    border-radius: 6px;
    padding: 14px 28px;
    font-size: 15px;
    font-weight: 600;
}

#btnPrimary:hover {
    background: #0284C7;
    border-bottom: 2px solid #0369A1;
}

#btnPrimary:pressed {
    background: #0369A1;
}

#enterpriseLabel {
    font-size: 12px;
    color: #6B7785;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    font-weight: 600;
}

#btnSecondary {
    background: transparent;
    color: #6B7785;
    border: 1px solid #30363D;
    border-radius: 6px;
    padding: 12px 24px;
    font-size: 14px;
}

#btnSecondary:disabled {
    opacity: 0.5;
}
```

### Add Shadow Effect to Form Card

In the `_build_form` method, after creating the card:

```python
from PySide6.QtWidgets import QGraphicsDropShadowEffect
from PySide6.QtGui import QColor

# Add shadow to form card (acceptable for single static element)
shadow = QGraphicsDropShadowEffect()
shadow.setBlurRadius(16)
shadow.setColor(QColor(0, 0, 0, 102))  # 40% opacity
shadow.setOffset(0, 8)
card.setGraphicsEffect(shadow)
```

## Removed Elements

**Theme Switcher**: Removed from login page per design spec. Theme switching should be in the sidebar after login, not on the login page.

## Performance Notes

1. **Shadow usage**: Only one real shadow on the form card (single static element, acceptable)
2. **Focus states**: Use outline instead of shadow (performance optimization)
3. **Button hover**: Uses border-bottom simulation instead of real shadow
4. **Statistics**: No card backgrounds, minimal rendering overhead

## Responsive Behavior

At < 1366px window width:
- Left section reduces to 35%
- Statistics stack vertically instead of horizontally
- Separators hidden in vertical layout
- Form card remains centered

## Testing Checklist

- [ ] Gradient background renders correctly on left section
- [ ] Statistics display with proper spacing and separators
- [ ] Form card shadow appears (check QGraphicsDropShadowEffect)
- [ ] Input focus states show blue outline
- [ ] Login button hover effect works
- [ ] SSO button appears disabled (grayed out)
- [ ] Text wrapping works for Chinese characters
- [ ] Layout adapts at smaller window sizes

## Next Steps

1. Update `login_studio.py` with new structure
2. Create/update QSS stylesheet file
3. Remove theme switcher from login page
4. Add shadow effect to form card
5. Test at different window sizes
6. Verify Chinese font rendering (Microsoft YaHei)
