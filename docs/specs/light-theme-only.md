# Spec: Light Theme Only - Remove Dark Theme Support

## Problem Statement

The application currently defaults to a dark theme with a near-black background (`#0A0E14`), making the interface appear completely black and controls barely visible. Users need a light theme with a light gray-white background (`#F8FAFC`) for better visibility in bright manufacturing environments. The existing dual-theme system (dark and light) with theme switching and persistence adds unnecessary complexity, as users have explicitly stated they only need a light theme without switching capability.

## Solution

Remove dark theme support entirely, making the application permanently use the light theme. This will be done in three phases:

**Phase 1 (Immediate)**: Change the default theme from dark to light with minimal code changes to validate the solution meets user needs.

**Phase 2 (User Validation)**: Users test all pages and features in production to ensure light theme works correctly across the entire application.

**Phase 3 (Cleanup)**: After successful validation, remove all dark theme code including definitions, switching logic, and persistence to simplify the codebase.

## User Stories

1. As a quality inspector, I want to see a light-colored interface, so that I can clearly view controls and text in a bright factory environment
2. As an application user, I want the login page to display with a light gray-white background (`#F8FAFC`) instead of near-black, so that it looks professional like enterprise SaaS products
3. As an application user, I want all pages (home, task center, scanning, etc.) to use consistent light colors, so that the visual experience is uniform
4. As an application user, I want input fields and buttons to have clear background colors that distinguish them from the page background, so that I can quickly locate interactive elements
5. As an application user, I want primary text to use dark color (`#0F172A`) on light background (`#F8FAFC`), so that reading is clear and comfortable
6. As an application user, I want cards and elevated surfaces to be white (`#FFFFFF`), so that they stand out from the page background
7. As an application user, I want the brand color (sky blue `#0EA5E9`) to remain consistent across all buttons and links, so that primary actions are recognizable
8. As an application user, I do not want to switch between dark and light themes, I just need one stable light theme
9. As a developer, I want only the actually-used light theme code in the codebase, so that maintenance is simpler
10. As a developer, I want to remove unnecessary theme switching logic, so that there are fewer potential bugs and less test burden
11. As a developer, I want to eliminate theme persistence logic (reading/writing `theme.json`), so that we avoid unnecessary file I/O
12. As a developer, I want to simplify or rename `ThemeManager` to reflect its single responsibility of generating stylesheets, so that the architecture is clearer
13. As a system maintainer, I want test code to only test features that actually exist, so that CI is faster and more reliable
14. As a code reviewer, I want to remove dead code (dark theme definitions and switching), so that future developers don't waste time understanding unused features
15. As a new team member, I want to see a simple stylesheet generation system without complex theme state management, so that I can understand the codebase faster

## Implementation Decisions

### Phase 1: Minimal Change (Immediate Implementation)

**Module Modified**: Theme manager's theme loading logic

**Change**: Modify the default theme return value from `"dark"` to `"light"` in the theme loading method

**Rationale**: Single-point change with lowest risk, easily reversible if validation fails

**Interface Impact**: None - external interface remains unchanged, only default behavior changes

**Validation**: Run application and verify login page background is light gray-white (`#F8FAFC`) and primary text is dark (`#0F172A`)

### Phase 2: User Validation (User-Driven Testing)

**Testing Scope**: All application pages and features
- Login page: background, cards, buttons, input fields
- Home page: navigation, stats cards, module buttons
- Task center: task lists, status badges
- Scanning, sampling, annotation, review pages: tool panels, controls
- Training, inference pages: parameter inputs, progress bars
- Restore, convert pages: form controls

**Success Criteria**:
- All page backgrounds are light-colored (`#F8FAFC`, `#FFFFFF`)
- All text is clearly readable (dark text on light background)
- No remnants of near-black background (`#0A0E14`)
- All interactive features work normally

### Phase 3: Code Cleanup (After Validation Passes)

**Module 1: Design System**
- Remove `DarkThemeColors` class definition
- Remove `DARK_THEME` constant
- Keep `LightThemeColors` and `LIGHT_THEME` unchanged

**Module 2: Theme Manager**
- Remove theme switching methods (`set_theme()`, `toggle_theme()`)
- Remove theme persistence methods (`_persist_theme()`, `_load_persisted_theme()`)
- Remove `_current_theme` instance variable
- Remove `ThemeMode` type definition
- Simplify to single-purpose stylesheet generator
- Consider renaming to `StylesheetManager` to reflect single responsibility

**Module 3: Stylesheet Generation**
- Remove `_dark_stylesheet` instance variable
- Remove `mode` parameter from stylesheet generation method
- Simplify to only generate light theme stylesheet

**Module 4: Components**
- Replace all `DARK_THEME.XXX` references with `LIGHT_THEME.XXX`
- Affected: hardcoded color references in custom widget implementations

**Module 5: Tests**
- Remove all dark theme test assertions
- Remove theme switching tests
- Remove theme persistence tests
- Remove config file handling tests
- Simplify stylesheet generation tests to only test light theme
- Keep transition and progress bar exclusion tests

**Preservation Decisions**:
- `UI_DESIGN_SPEC_v2.md` remains unchanged (reference document only)
- Light theme color definitions remain unchanged
- Core stylesheet generation logic remains unchanged
- Design token system (`FONT_SIZE`, `SPACING`, `RADIUS`) remains unchanged

## Testing Decisions

### What Makes a Good Test

**Test external behavior only**: Verify that the stylesheet generation produces correct color values in the output string, not how it generates them internally

**Test at the highest seam**: Use `ThemeManager.get_stylesheet()` as the primary test seam - it returns the complete QSS string which can be validated for correct color codes

**Avoid implementation details**: Don't test internal methods, instance variables, or generation steps

### Modules to Test

**Primary**: Theme manager stylesheet generation
- Test that `get_stylesheet()` returns a non-empty string
- Test that output contains light theme colors (`#F8FAFC`, `#FFFFFF`, `#0F172A`)
- Test that output contains CSS properties (`background-color:`, `color:`)
- Test that transitions are included (300ms for color properties)
- Test that progress bars exclude transitions

**Secondary**: Singleton pattern (if preserved)
- Test that `get_theme_manager()` returns the same instance

### Prior Art

Current test patterns in `tests/gui/test_theme_manager.py`:
- Check stylesheet length to ensure complete generation
- Check for presence of specific color values (e.g., `#F8FAFC`)
- Check for presence of CSS properties (e.g., `background-color:`)
- Check for transition rules
- Check for progress bar transition exclusions

### Phase 1 Test Changes

- Modify test expecting default theme to be "dark" → expect "light"
- Leave other tests unchanged temporarily (tolerate dark theme testing for now)

### Phase 3 Test Changes

- Delete all dark theme color assertions
- Delete `test_theme_manager_toggles_theme`
- Delete `test_theme_manager_persists_theme`
- Delete `test_theme_manager_handles_missing_config_gracefully`
- Delete `test_theme_manager_handles_corrupt_config_gracefully`
- Simplify `test_theme_manager_generates_stylesheets` to only test light theme
- Keep `test_theme_manager_stylesheet_excludes_progress_from_transition`
- Keep `test_theme_manager_includes_300ms_transitions`
- Update `test_theme_manager_initializes_with_dark_theme` to verify light theme default

## Out of Scope

The following are **explicitly out of scope** for this change:

**UI Design Specification Document**: `UI_DESIGN_SPEC_v2.md` will not be modified - it is a reference document, not an implementation document

**QSS Incompatible Properties**: Properties like `cursor`, `line-height`, `text-transform` that QSS doesn't support will remain in the code for now - they are ignored by Qt but don't affect functionality

**Global QWidget Background Optimization**: Although diagnostics identified this as a potential issue, it is mitigated by switching to light theme and can be optimized separately later

**Stylesheet Generation Logic Refactoring**: The core template-based generation approach remains unchanged, only dark theme portions are removed

**Design Token System**: Color, spacing, font, and radius constants remain unchanged

**Other GUI Component Changes**: Except for hardcoded dark theme references in components module, other widgets are unchanged

**Performance Optimization**: Theme switching performance, stylesheet caching, and rendering optimizations are not in scope

**Singleton Pattern Removal**: While theme state management is removed, the decision to keep or remove singleton pattern is deferred to implementation

## Further Notes

### Risk Assessment

**Phase 1 Risk: Very Low**
- Single-line change, easily reversible
- No impact on existing features, only changes default value
- User can immediately validate the effect

**Phase 3 Risk: Medium**
- Involves deletions across multiple files
- Need to ensure no missed references remain
- Recommend using GitNexus impact analysis to verify blast radius before deletion

### Rollback Strategy

**Phase 1 Rollback**: Change single line back to return `"dark"`

**Phase 3 Rollback**: Use git revert on the cleanup commit

### Recommended Follow-up Work

1. **Clean QSS incompatible properties** - Remove `line-height`, `cursor`, `text-transform`
2. **Optimize global QWidget background** - Change to specific selectors
3. **Refactor theme manager** - Simplify to `get_stylesheet()` factory function
4. **Unify component hardcoded colors** - Use `LIGHT_THEME` throughout or manage via QSS

### Related Documentation

- `docs/theme_fix_completion_report.md` - Root cause analysis report
- `docs/UI_DESIGN_SPEC_v2.md` - UI design reference (lines 154-179 define light theme)
- `_diagnostic_report.md` - Diagnostic report (generated by subagent)

### Decision Rationale

**Why Progressive Instead of One-Shot Deletion?**
- User requirement: "ensure absolute safety"
- Phase 1 validates whether solution meets needs immediately
- Avoids large-scale deletion discovering missed references causing crashes
- Aligns with "pragmatic fallback" principle of robust engineering

**Why Not Keep Theme Switching?**
- User explicitly stated "don't need theme switching functionality"
- Simplifies code, reduces maintenance cost
- Follows YAGNI principle (You Aren't Gonna Need It)

**Why Three Phases?**
- Separates validation from cleanup
- Allows production testing before committing to large deletions
- User can abort after Phase 1 if light theme doesn't meet expectations
- Cleanup happens only after proven success
