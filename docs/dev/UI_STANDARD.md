# AutoLabeler UI Standard

> Status: forward-looking standard for desktop UI work.
> Last updated: 2026-08-14
> See also: `docs/dev/UI_SPEC.md` (current GUI behavior and layout baseline),
> `docs/dev/PRODUCT_SPEC.md` (product behavior contract).

This document defines a forward-looking, standards-driven desktop UI baseline
for AutoLabeler. It is based on **WCAG 2.2 AA** principles where applicable and
**Qt desktop interaction conventions**. It guides future interface work without
requiring a GUI redesign.

Page-specific business behavior---inputs, outputs, mode switches, flow logic,
preflight rules, and result summaries---lives in the product and UI specs, not
here. This standard describes the shared shell, common patterns, and
accessibility baseline common to every surface.

Current implementation gaps are expressed as **Future Work** (section 10).
They are not exceptions that weaken the standard.

---

## 1. Desktop Product Goals

The GUI must feel like a **polished production tool**, not a collection of
scripts. Primary users are operators who use individual functions or run the
full labeling workflow. The interface must also be presentable to leadership.

The standard governs:

- **Login** --- enterprise-ready formal entry, one action per session.
- **Workbench shell** --- persistent navigation, shared chrome, global task
  awareness.
- **Module pages** --- tool-specific input/output surfaces.
- **Task center** --- lightweight running/recent task overview.
- **Manual** --- built-in usage reference.
- **Settings** --- persistent tool defaults.

---

## 2. Information Hierarchy

Every screen follows a clear visual hierarchy:

1. **Primary chrome** --- app shell, navigation, global status (always visible).
2. **Page title / identity** --- answers "where am I?" in one glance.
3. **Primary content area** --- the main action surface (inputs, results).
4. **Support area** --- contextual help, AI preview, supplementary info (right
   rail, collapsible on small windows).
5. **Status / feedback** --- inline progress, concise logs, result summaries.
6. **Footer / chrome bottom** --- reserved for persistent status bars, not
   decorative elements.

Within a page, hierarchy is structural:
- Headings distinguish sections (page title > section heading > group label).
- Primary actions are visually distinct from secondary or destructive actions.
- Related inputs are grouped with clear spacing and labels.
- Long lists (modules, tasks, manual sections) use scrolled containers, not
  infinite page growth.

---

## 3. Keyboard and Focus Behavior

### Keyboard Navigation

All interactive controls must be reachable and operable via keyboard alone.

- **Tab order** follows visual reading order: left to right, top to bottom.
- **Tab stop** is restricted to interactive widgets (buttons, inputs, selects,
  links). Non-interactive decorative elements do not receive focus.
- **Arrow keys** navigate within grouped controls (radio groups, tab lists,
  tree views).
- **Space / Enter** activates the focused control.
- **Escape** closes modal dialogs, pop-up menus, and inline confirmations.
- **F6 / Ctrl+Tab** moves focus between the navigation pane and content area
  (future work for multi-pane shell).

### Focus Indicators

- Every focusable widget shows a **visible focus ring** that meets 3:1
  contrast against the unfocused state.
- Focus rings are achieved via `QPushButton:focus` / `QLineEdit:focus` Qt
  style sheets, not by removing the default dotted outline without a
  replacement.
- Focus must not be suppressed or hidden except during mouse-driven
  interaction where the user agent convention is acceptable.

### Focus Management

- Opening a page or dialog sets focus to the first meaningful input or primary
  action.
- Closing a dialog returns focus to the element that triggered it.
- Page navigation does not reset focus to the window chrome unless the user
  explicitly moves there.

---

## 4. Contrast and Semantic State Roles

### Color Contrast

All text and interactive elements meet **WCAG 2.2 AA contrast ratios**:

| Role | Minimum contrast ratio | Notes |
|------|----------------------|-------|
| Normal text (< 18px / < 14px bold) | **4.5:1** against background | Body text, labels, descriptions |
| Large text (>= 18px or >= 14px bold) | **3:1** against background | Headings, module titles, hero text |
| Interactive controls | **3:1** against adjacent background | Button borders, input outlines, focus rings |
| Placeholder text | **4.5:1** against background | Must not rely on low-contrast placeholders |
| Disabled text | **3:1** against background | Minimum readability for disabled controls |

### Semantic State Roles

Colors communicate state consistently across all surfaces:

| State | Visual cue | Notes |
|-------|-----------|-------|
| **Normal / Idle** | Default widget appearance | Light background, dark text |
| **Hover** | Slightly lighter or darker background | 10--15% brightness shift |
| **Active / Pressed** | Inverted or darker background | Indicates current interaction |
| **Selected / Current** | Brand accent color (#007b78) | Navigation item, active tab, card |
| **Focus** | Visible focus ring | 2px solid outline, WCAG 3:1 |
| **Disabled** | Reduced opacity (50--60%) | No interactive visual feedback |
| **Error** | Red-tinted text and border | #b91c1c or equivalent 4.5:1 on background |
| **Warning** | Amber-tinted text and border | #92400e or equivalent 4.5:1 on background |
| **Success** | Green-tinted text | #166534 or equivalent 4.5:1 on background |
| **Info** | Blue-tinted text | #1e40af or equivalent 4.5:1 on background |

The brand accent (#007b78) is reserved for selection, primary action, and
active state. It is not used for decorative emphasis.

### Non-Text Contrast

- Icons, status dots, and graphical indicators have **3:1 contrast** against
  adjacent backgrounds.
- Essential information conveyed by color alone is also conveyed by text label,
  icon, or pattern.

---

## 5. Fixed Typography

Typography is **fixed** (not viewport-scaled). Font sizes are set in the
application stylesheet and do not change with window size.

### Font Family

- Primary: `"Microsoft YaHei UI"` (Windows CJK).
- Fallback: `system-ui, -apple-system, sans-serif`.
- Monospace (code, paths, logs): `"Cascadia Code", "Consolas", monospace`.

### Font Sizes and Weights

| Role | Size | Weight | Line height |
|------|------|--------|-------------|
| Product name / branding | 26px | Bold (700) | 1.2 |
| Page title | 20px | Bold (700) | 1.3 |
| Section heading | 15px | Bold (700) | 1.4 |
| Body text | 13px | Normal (400) | 1.5 |
| Small / caption | 12px | Normal (400) | 1.4 |
| Button label | 13px | Semi-bold (600) | 1.2 |
| Monospace / code | 12px | Normal (400) | 1.4 |
| Navigation item | 13px | Medium (500) | 1.2 |

### Typography Rules

- All text is single-line unless marked `word-wrap: true`.
- Long paths and URLs wrap inside their container.
- CJK text is not artificially letter-spaced.
- No viewport-scaled or fluid type (`em`/`rem` relative to container width is
  not used in Qt desktop; use fixed `px` values).

---

## 6. Responsive Structure

The app is a **fixed-shell desktop application** with a minimum window size.
Within that fixed structure, content areas adapt to available width.

### Small-Window Priority

When the window is narrower than the ideal width (1440px), the following
priority determines what is visible:

1. **Module cards and page content** remain visible and primary.
2. **Page title and section headings** remain visible; copy may tighten.
3. **Navigation pane** remains fully visible (collapsed icon-only mode is
   future work).
4. **Support panels** (right rail, AI preview) are the first to hide or
   collapse to a toggle button.
5. **Descriptive text** compresses to short labels or tooltips.
6. **Log surfaces** and large result blocks scroll internally rather than
   stretching the page.

### Minimum Window

The minimum usable window size is **1024 x 680 px**. Below this, the window
may clip content; no guarantee of usability is made.

### Resize Behavior

- The main content area expands and contracts within the window.
- Navigation width is fixed (240 px).
- Support panels have a minimum width (176 px) and collapse gracefully.
- Module pages use `QScrollArea` for content overflow, not page-level
  scrolling.

---

## 7. Error, Loading, and Empty States

### Error States

- **Inline errors** appear beside the relevant input field, not in a global
  banner.
- **Action errors** (task failure, preflight failure) appear in a visible
  result area below the action button.
- **Unrecoverable errors** (app crash, missing Python) appear in a modal dialog
  with clear next-step instructions.
- Error text is human-readable: explain what went wrong, what the user can do,
  and reference the underlying error in expandable technical details.
- Error text meets WCAG 2.2 AA contrast (4.5:1) and is not styled solely with
  color.

### Loading States

- **Long-running tasks** (seconds to minutes) use a running indicator and
  real-time log output.
- **Instant actions** (under 1 second) use a brief spinner or do not show a
  loading state.
- The user can navigate away from a running task without losing task state.
- The task center reflects running status.

### Empty States

Every list or collection surface defines an empty state:
- **Task center**: "No tasks yet. Start a module to see your tasks."
- **Module page**: No empty state (always shows inputs).
- **Manual**: No empty state (always populated).
- **Settings**: No empty state (always populated).
- **Homepage**: No empty state (always shows module cards).

Empty states use body text, center alignment, and a subtle icon or emoji when
appropriate. They are not blank white pages.

---

## 8. Qt Desktop Interaction Conventions

### Window Conventions

- Standard window chrome (title bar, system menu, minimize/maximize/close).
- Single main window, no multiple document windows.
- Modal dialogs for critical confirmations.
- QDialog with `exec()` for blocking decisions (file overwrite, unsaved work).

### Navigation Conventions

- Left sidebar navigation with clear active-indicator.
- Clicking an already-active navigation item scrolls to top of the page.
- Task center is a dedicated view, not a popup.
- Manual and settings are in the navigation area, not on the homepage.

### Control Conventions

- `QPushButton` for primary and secondary actions.
- `QLineEdit` for text/path input (with `QFileDialog` browse button).
- `QComboBox` for enumeration selection.
- `QCheckBox` for boolean options.
- `QRadioButton` for mutually exclusive choices within a group.
- `QScrollArea` for content overflow on tool pages.
- Right-click context menus are not required for primary workflows.

### Confirmation Pattern

High-risk operations (data overwrite, destructive actions, batch operations)
use a two-step inline confirmation:

1. User clicks primary action -> preflight validation runs.
2. If preflight passes and risk is high, show a confirmation panel with a
   summary of what will happen and a "Confirm" / "Cancel" choice.
3. User confirms -> action proceeds.

This pattern is preferred over Qt's `QMessageBox` for inline workflow
continuity.

---

## 9. WCAG 2.2 AA Principles Applied

### Perceivable

- **1.1.1 Non-text Content**: All icons, status dots, and graphical indicators
  have text alternatives (tooltip or adjacent label).
- **1.4.1 Use of Color**: Color is never the sole differentiator; status is
  conveyed by text, icon, or symbol.
- **1.4.3 Contrast (Minimum)**: See section 4 above.
- **1.4.4 Resize Text**: Text can be resized via system DPI settings without
  loss of content or functionality.
- **1.4.11 Non-text Contrast**: UI components and graphical objects meet 3:1
  contrast.

### Operable

- **2.1.1 Keyboard**: All functionality is operable through keyboard alone.
  See section 3.
- **2.4.3 Focus Order**: Focus order preserves meaning and operability.
- **2.4.7 Focus Visible**: Any keyboard operable user interface has a visible
  focus indicator. See section 3.
- **2.5.8 Target Size (Minimum)**: Interactive targets are at least 24x24 px
  with 4 px spacing between adjacent targets. (WCAG 2.2 AA new.)

### Understandable

- **3.2.1 On Focus**: Focusing a control does not initiate a context change.
- **3.3.1 Error Identification**: Input errors are described in text. See
  section 7.
- **3.3.2 Labels or Instructions**: All inputs have visible labels.
- **3.3.4 Error Prevention (Legal, Financial, Data)**: For destructive
  operations, confirmation is required. See section 8.

### Robust

- **4.1.2 Name, Role, Value**: Qt widget accessibility names and roles are
  set through `setObjectName` and `setAccessibleName` for all interactive
  controls.

---

## 10. Future Work (Implementation Gaps)

The following are documented gaps that the current implementation does not
fully meet. They are **future work**, not exceptions to the standard.

| Gap | Standard reference | Current state |
|-----|-------------------|---------------|
| Full keyboard navigation for all pages | Section 3 | Login, home, and basic pages work; some module pages have incomplete tab order. |
| Visible focus rings on all controls | Sections 3, 4 | Focus ring styles are applied in the global stylesheet but not verified per-page. |
| WCAG AA contrast audit | Section 4 | Contrast ratios are targeted by design colors but not verified by automated tools. |
| Accessible names on all interactive controls | Section 9 | Core controls have `setObjectName`; `setAccessibleName` is not consistently applied. |
| Target size >= 24x24 px on all interactive targets | Section 9 | Main buttons meet this; some inline links and compact controls may not. |
| Collapsed icon-only navigation mode | Section 6 | Navigation is always expanded; no icon-only mode exists. |
| Collapsible support panels | Sections 6, 8 | Right rail panels have minimum width but no collapse toggle. |
| Resizable navigation pane | Section 6 | Navigation width is fixed at 240 px. |
| Error prevention for all destructive operations | Section 9 | Convert and Restore use inline confirmation; other destructive paths are not fully hardened. |
| Keyboard-accessible task center actions | Section 3 | Task center delete and filter actions are mouse-accessible but not fully keyboard-navigable. |
| Context menus for power users | Section 8 | Right-click context menus are not implemented. |
| Automated accessibility testing | Section 9 | No automated accessibility regression tests exist. |

---

## 11. Relationship to Other Specs

| Document | Scope |
|----------|-------|
| `PRODUCT_SPEC.md` | Product behavior: inputs, outputs, workflows, mode logic, preflight rules, result summaries. |
| `UI_SPEC.md` | Current GUI behavior and layout: page structure, visual design, current behavior per surface. |
| **UI_STANDARD.md** (this file) | Forward-looking standard: accessibility, typography, contrast, focus, responsive, state patterns. |

The standard does not duplicate page-specific business behavior. When a
standard rule conflicts with a UI_SPEC behavior, the UI_SPEC governs the
current implementation until the standard is adopted.

---

## Version History

| Date | Change |
|------|--------|
| 2026-08-14 | Initial forward-looking UI standard based on WCAG 2.2 AA and Qt conventions. |
