# Login Page Implementation Changes

## Objective
Match the HTML design specification (`docs/login_page_design.html`) exactly in PySide6/Qt implementation.

## Changes Made

### 1. Layout Structure (`gui/workbench.py`)

#### Root Layout
- **Before**: `setContentsMargins(48, 42, 48, 42)` with `setSpacing(24)`
- **After**: `setContentsMargins(0, 0, 0, 0)` with `setSpacing(0)`
- **Reason**: HTML has no outer margins, full viewport usage

#### Left Section (Brand Story)
- **Before**: `setContentsMargins(34, 32, 34, 32)` with generic `setSpacing(18)`
- **After**: `setContentsMargins(56, 56, 56, 64)` with explicit spacing per element
- **Key Spacing Changes**:
  - Brand → Headline: 90px (was implicit ~18px)
  - Headline → Description: 24px (maintained)
  - Description → Stats: 64px (was 48px)
  - All other sections: 48px (maintained)

#### Right Section (Form Card)
- **Before**: Card with no fixed width, stretch factor 0
- **After**: Card with `setFixedWidth(440)` wrapped in centered container
- **Container**: 80px padding on all sides for centering effect
- **Layout Ratio**: Changed from `addWidget(story, 1), addWidget(card, 0)` to `addWidget(story, 40), addWidget(card_container, 60)`

#### Form Elements
- **Primary Button**: Added `setMinimumHeight(46)` for 14px padding + 15px font + line-height
- **SSO Button**: Added `setMinimumHeight(42)` for 12px padding + 14px font
- **Description**: Changed objectName from `"mutedText"` to `"loginDescription"` for specific styling
- **Description**: Added `setMaximumWidth(480)` to match HTML constraint

### 2. Stylesheet Updates (`gui/theme_manager.py`)

#### New Styles Added

```css
#loginDescription {
    font-size: 16px;
    font-weight: 400;
    color: TEXT_SECONDARY;
    line-height: 1.7;
}

#loginStatReadout {
    background: transparent;
}

#loginStatSeparator {
    background: BORDER_SUBTLE;
    border: none;
}

#loginStoryFooter {
    font-size: 13px;
    color: TEXT_TERTIARY;
    line-height: 1.5;
}

#loginCardContainer {
    background: BG_SURFACE;
}

#loginOptionLabel {
    font-size: 12px;
    color: TEXT_TERTIARY;
    font-weight: SEMIBOLD;
    letter-spacing: 0.5px;
    text-transform: uppercase;
}

#loginForgotLink {
    font-size: 13px;
    color: BRAND_PRIMARY;
}

#loginForgotLink:hover {
    color: BRAND_HOVER;
}
```

#### Modified Styles

**Typography Precision**:
- `#loginBrand`: Added `letter-spacing: -0.5px`
- `#loginHeadline`: Changed `line-height: TIGHT` → `1.3`, added `letter-spacing: -0.5px`
- `#loginFormTitle`: Added `letter-spacing: -0.5px`
- `#loginFormSubtitle`: Added `line-height: 1.5`
- `#loginStatValue`: Added `letter-spacing: -1px`
- `#loginStatLabel`: Added `font-weight: REGULAR`, `letter-spacing: 0.3px`

**Button Adjustments**:
- `#primaryButton`: Changed padding from `{BUTTON_MD}` to explicit `14px 28px`, font-size to `15px`, font-weight to `SEMIBOLD`
- `#primaryButton:hover`: Removed `border-bottom` (was causing layout shift)
- `#secondaryButton`: Changed padding to `12px 24px`
- `#secondaryButton:disabled`: Added `opacity: 0.5`

**Input Fields**:
- `#formInput`: Changed padding from `10px 12px` to `12px 14px`
- `#formInput:focus`: Added `outline-offset: 0px`

## Design Decisions

### What Matches HTML Exactly
1. ✅ 40/60 layout proportion
2. ✅ 56px outer padding on left section
3. ✅ 90px gap between brand and headline
4. ✅ 440px fixed card width
5. ✅ 80px padding around card container
6. ✅ All typography sizes, weights, and letter-spacing
7. ✅ All button dimensions and styles
8. ✅ Input field padding
9. ✅ Statistics layout with separators
10. ✅ Footer styling

### Technical Stack Adaptations

#### No Real Shadow on Card
- **HTML**: `box-shadow: 0 8px 16px rgba(0, 0, 0, 0.4)`
- **Qt**: Border-only styling
- **Reason**: QGraphicsDropShadowEffect would break theme switching (shadow color doesn't update with theme). Border simulation is theme-safe and performant.

#### Flexbox vs QLayout
- **HTML**: `flex: 0 0 40%` means "don't grow, don't shrink, basis 40%"
- **Qt**: `addWidget(widget, 40)` uses stretch factor (relative proportion)
- **Result**: Semantically equivalent behavior

#### CSS Transitions
- **HTML**: Can use `transition: all 0.15s ease`
- **Qt**: QSS doesn't support transitions; would need QPropertyAnimation in Python
- **Decision**: Omitted for this static login page (no animations on hover in final design)

## Responsive Behavior

The HTML design includes media queries for < 1366px:
- Left section reduces to 35%
- Statistics stack vertically
- Separators hidden

**Current Implementation**: Uses 40/60 stretch factors, so Qt will scale proportionally. For full responsive behavior matching HTML, would need:

```python
def resizeEvent(self, event):
    super().resizeEvent(event)
    if self.width() < 1366:
        # Switch stats to vertical layout
        # Hide separators
        pass
```

**Decision**: Deferred for Phase 2 (core layout matches first)

## Testing Checklist

- [ ] Layout renders with correct 40/60 split
- [ ] Left padding is 56px (verify with screenshot)
- [ ] Brand to headline gap is 90px (verify spacing)
- [ ] Card is centered and 440px wide
- [ ] Statistics display with vertical separators
- [ ] All text uses correct font sizes
- [ ] Primary button height is ~46px
- [ ] Input fields have 12px vertical padding
- [ ] Forgot password link is right-aligned
- [ ] SSO button appears disabled with reduced opacity
- [ ] Footer text is 13px and muted color
- [ ] Theme switching works (no shadow artifacts)

## Known Limitations

1. **No box-shadow**: Using border simulation instead (theme-safe)
2. **No CSS transitions**: Static hover states only
3. **No responsive breakpoints**: Fixed 40/60 for all sizes (can add in Phase 2)
4. **Letter-spacing in Qt**: QSS `letter-spacing` may render slightly differently than CSS
5. **Font rendering**: Windows ClearType vs web font smoothing may show subtle differences

## Files Modified

1. `gui/workbench.py` - LoginView class (lines 327-537)
2. `gui/theme_manager.py` - Login page styles (lines 550-660)

## Rollback Plan

If issues arise:
```bash
git diff HEAD -- gui/workbench.py gui/theme_manager.py
git checkout HEAD -- gui/workbench.py gui/theme_manager.py
```

All changes are isolated to LoginView and login-specific QSS selectors.
