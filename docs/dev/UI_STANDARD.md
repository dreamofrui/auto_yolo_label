# AutoLabeler UI Standard

> Status: accepted visual standard (2026-09-06)
> Source of truth: `gui/design_system.py` and `gui/theme_manager.py`
> Behavior/layout baseline: `docs/dev/UI_SPEC.md`
> Decision record: `docs/adr/0002-enterprise-visual-language.md`

This standard keeps AutoLabeler calm and legible for long production sessions.
It defines visual language and verification rules; product behavior, field
semantics, worker contracts, and safety confirmations remain in the product/UI
specs.

## 1. Visual language

- Light cool-mist canvas with white workflow surfaces.
- Deep navy navigation rail; inverse text and a teal active marker.
- Cool teal for executable primary actions and focus states.
- Champagne gold only for restrained brand details or key metrics; it is not a
  success/warning color.
- Business status colors remain distinct: emerald success, amber warning, red
  error, sky information.
- Use thin boundaries and low-diffusion elevation. Avoid glassmorphism,
  decorative gradients, glow, and card spam.

## 2. Tokens

The canonical values live in `LightThemeColors`, `FontSize`, `Spacing`,
`BorderRadius`, and the shadow helpers in `gui/design_system.py`.

| Role | Token/value |
| --- | --- |
| Canvas | `BG_APP #F4F7FA` |
| Surface | `BG_SURFACE #FFFFFF` |
| Navigation | `NAV_BG #101C2E` |
| Primary action | `BRAND_PRIMARY #0C766E` |
| Primary hover/pressed | `#0B6F69` / `#07534F` |
| Primary subtle | `BRAND_SUBTLE #E2F3F0` |
| Brand detail | `BRAND_ACCENT #C89B5B` |
| Ink/secondary | `TEXT_PRIMARY #0B1220` / `TEXT_SECONDARY #52657A` |
| Borders | `#D9E2EC` default, `#B8C7D6` emphasis |

Typography uses Inter first, then SF Pro Display, Microsoft YaHei UI, Segoe UI,
and platform sans-serif fallbacks. Page titles use 32px regular; section titles
24px regular; body text 14px; captions 12px. Keep the existing 8px spacing rhythm
and the minimum desktop window of 1024×680.

## 3. Component rules

- Primary buttons are teal, 36px minimum height, 8px radius, and use a clear
  hover/pressed/disabled state.
- Secondary buttons use a transparent or white surface with a 1px border.
- Destructive actions use the semantic error palette and never the brand gold.
- Inputs and combo boxes use white surfaces, a 1px border, and a visible teal
  focus ring; path pickers keep their shared browse affordance.
- Navigation rows use navy hover/active surfaces, 3px teal active edge, and
  inverse text. Keep the fixed 240px rail and existing entry order.
- Homepage module cards retain the existing 4×2 grid. A 3px left accent may
  differentiate modules; the whole card remains the click target.
- Tool pages retain their left-main/right-support structure and current field
  grouping. Only intra-group spacing, border weight, and hierarchy may change.
- Status, preflight, result, and risk surfaces keep their existing semantics;
  visual changes must not hide confirmation or error copy.

## 4. Motion and accessibility

- Use only short 120–180ms state feedback; never animate layout or task state.
- Respect the system reduced-motion preference and degrade to static styling.
- Keyboard focus must remain visible on every interactive control.
- Text and status colors must meet WCAG 2.2 AA contrast against their surface.
- Long paths and summaries wrap or compact; tooltips/details retain full values.

## 5. Verification gate

Review the login page, homepage, navigation, task center, manual/settings, and
one representative tool page at 1440×900 and 1280×720 using the offscreen Qt
test setup. Confirm that:

1. No input, action, status, or confirmation control is removed or clipped.
2. Navigation and module cards remain discoverable and keyboard reachable.
3. Running tasks and error/result feedback still render in their existing
   regions.
4. Contrast and focus states remain legible in both window sizes.
5. `tests/gui` focused tests pass with the project Anaconda `yolo` interpreter.
