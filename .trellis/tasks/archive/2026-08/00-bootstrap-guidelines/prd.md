# Bootstrap Project-Specific Trellis Specs

## Goal

Refresh the interrupted Trellis bootstrap so `.trellis/spec/` describes the
current AutoLabeler repository instead of the generated full-stack template.

## Scope

- Spec directory: `.trellis/spec/`
- Source areas to inspect: `core/`, `gui/`, `gui/workers/`, `utils/`,
  `server_scripts/`
- Tests and checks to inspect: `tests/test_contracts.py`,
  `tests/test_imports.py`, layer-focused tests, `tests/integration/`, and
  `scripts/check_disciplines.py`
- Retained docs to align with: `AGENTS.md`, `CLAUDE.md`,
  `docs/dev/ONBOARDING_SUMMARY.md`, `docs/dev/PRODUCT_SPEC.md`,
  `docs/dev/UI_SPEC.md`, `server_scripts/README.md`
- Out of scope: product code, GUI behavior, dependencies, `legacy/`, reserved
  real data under `tests/A9950/`, and generated artifacts

## Requirements

- Replace the stale backend/frontend scaffold with guides for the actual
  framework-free core, PySide6 GUI, thin GUI workers, shared infrastructure,
  and standalone server scripts.
- Keep `index.md` files navigable and limited to files that exist.
- Ground important rules in real source files or tests and call out local
  anti-patterns such as direct `mapping.json` access and business logic in
  pages or workers.
- Rewrite the generic thinking guides so they use AutoLabeler examples.
- Leave no template placeholders, empty headings, or obsolete web/CLI/runtime
  guidance in the resulting spec tree.

## Acceptance Criteria

- [x] Every listed spec link resolves to a file in `.trellis/spec/`.
- [x] Core, GUI, workers, utils, and server-script guidance names concrete
      local files and focused tests.
- [x] Cross-layer guidance documents Flow/Independent data and error paths.
- [x] Placeholder and stale backend/frontend text searches return no matches.
- [x] Scoped repository checks and spec consistency checks pass.
- [x] `CHANGELOG.md` records this retained documentation change.
