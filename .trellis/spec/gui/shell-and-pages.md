# Shell And Page Patterns

## App Shell

`gui/app.py` owns application startup and creates `AutoLabelerWindow` from
`gui/workbench.py`. The workbench owns login, navigation, homepage, utility
surfaces, module registration, and the shared `TaskRegistry`. Keep module
metadata in the `MODULES` table and route pages through the existing workbench
factory instead of adding a second navigation registry.

The homepage and navigation are verified by `tests/test_gui_shell.py`. Preserve
the light workspace, dark side navigation, compact module cards, and small
desktop window behavior documented in `docs/dev/UI_SPEC.md`.

## Tool Pages

Pages such as `gui/scan_page.py`, `gui/sample_page.py`, and
`gui/restore_page.py` follow the same shape:

- a left scrollable main panel for title, mode, inputs, parameters, actions,
  preflight, results, and useful logs;
- a persistent right support/preview rail from `build_ai_assistant_panel`;
- shared spacing and path-width handling from `gui/tool_page_chrome.py`;
- a worker protocol that is easy to replace with a fake in tests;
- typed config construction in `_build_config` and typed outcome handling.

Use `PathPicker` for directories and files. Keep mode-specific controls
visible only when they apply, as `SamplePage.set_mode` and
`RestorePage.set_mode` do. Keep advanced or uncommon parameters collapsed or
secondary; do not add controls that are not in the product/UI spec.

## Defaults And Text

Persist non-path tool defaults through `gui/tool_defaults.py` and the existing
`.autolabeler` runtime file. Apply defaults to controls without changing the
core config contract. User-facing text should explain mode, output, risk, and
next action; technical exception details belong in a log or expandable detail.

## Boundaries

Do not import `server_scripts` into pages. Do not parse mapping JSON, YOLO rows,
or VOC XML in a page. Do not put a file move, delete, overwrite, or restore
operation behind a button without the worker/core preflight boundary.
