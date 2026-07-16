# AutoLabeler Onboarding Summary

## Background

AutoLabeler is a desktop-first YOLO semi-automatic image labeling workbench.
Its main workflow is:

```text
scan -> sample -> label with LabelImg -> train -> infer
-> review with LabelImg -> restore XML labels
```

Operators use it to reduce manual labeling cost: scan a strict product image
tree, sample a smaller training set, label it, train a model, predict the
remaining images, review predictions, and restore reviewed labels beside the
original images.

This handoff is for engineers maintaining the desktop product or adding new
module behavior. It is not a general project brochure. Read this before coding
so you do not accidentally reintroduce removed architecture, bypass safety
checks, or break Flow/Independent mode boundaries.

Current non-goals:

- Web UI, FastAPI, browser UI, Node subprocess integration.
- Active `cli/` or `runtime/` service layers.
- Workflows that depend on AI execution.
- Editing or copying implementation from historical `legacy/` code.

## Current Status

The formal product surface is the PySide6 GUI, started through `gui.app`.
The GUI includes login, homepage, task center, manual/settings, and pages for
Scan, Sample, Label, Train, Infer, Review, Restore, and Convert.

Active architecture:

- `core/`: framework-free business logic. Public entrypoints accept one
  dataclass config and return typed results.
- `gui/`: PySide6 shell, pages, shared widgets, and UI state.
- `gui/workers/`: thin desktop adapters. They call `core/` directly and handle
  task lifecycle glue.
- `utils/`: shared infrastructure such as mapping, task registry, path
  encoding, device helpers, and business exceptions.
- `server_scripts/`: standalone Linux/Docker training and prediction scripts.
  They are useful operational tools, but the desktop GUI must not depend on
  them.

Reliable mainline behavior:

- Flow mode uses `.autolabeler/mapping.json` for traceability.
- Independent mode only runs where explicit paths are enough.
- Long-running GUI work is tracked through `TaskRegistry`.
- Path-like GUI inputs use the shared `gui/path_picker.py`.
- High-risk file operations use preflight and inline confirmation.

Limited or reserved areas:

- AI assistant UI is preview/reserved only.
- Login is local/demo access plus reserved enterprise SSO affordance, not a
  real permissions system.
- Local artifacts such as `.pytest-*`, `.autolabeler/`, run outputs, caches,
  and model weights are not product source.

When adding behavior, the normal route is:

```text
PRODUCT_SPEC if behavior changes -> core dataclass/result -> worker adapter
-> GUI page -> focused tests -> CHANGELOG if notable
```

## Tech Stack

- Language: Python.
- Desktop UI: PySide6.
- ML runtime: Ultralytics YOLO and PyTorch/CUDA where available.
- External tool: LabelImg is launched externally; it is not embedded.
- Storage: local filesystem, including `mapping.json`, YOLO datasets, VOC XML,
  YOLO TXT labels, task JSON files, defaults, logs, and model weights.
- Tests: pytest plus architecture/import discipline tests.

Use the project interpreter for local commands:

```powershell
D:/miniforge3/envs/yolo_new/python.exe
```

Common commands:

```powershell
D:/miniforge3/envs/yolo_new/python.exe -m gui.app
D:/miniforge3/envs/yolo_new/python.exe -m pytest tests/test_imports.py tests/test_contracts.py
D:/miniforge3/envs/yolo_new/python.exe scripts/check_disciplines.py
```

For implementation work, also run tests matching the touched module, worker, or
GUI page. Do not claim full product coverage unless the corresponding feature
tests or real smoke checks were actually run.

## Module Maintenance Map

Use this map to find the right layer before changing behavior. The product
contract lives in `PRODUCT_SPEC.md`; the GUI contract lives in `UI_SPEC.md`.
Do not put new business rules only inside a page or worker.

| Area | Core owner | GUI owner | Worker owner | Focused tests |
| --- | --- | --- | --- | --- |
| Scan | `core/scanner.py` | `gui/scan_page.py` | `gui/workers/scan_worker.py` | `tests/test_scanner.py`, `tests/test_scan_worker.py` |
| Sample | `core/sampler.py` | `gui/sample_page.py` | `gui/workers/sample_worker.py` | `tests/test_sampler.py`, `tests/test_sample_worker.py` |
| Label with LabelImg | `core/labelimg_launcher.py`, `core/annotation_formats.py` | `gui/labelimg_page.py` | `gui/workers/labelimg_worker.py` | `tests/test_labelimg_launcher.py`, `tests/test_labelimg_worker.py`, `tests/test_annotation_formats.py` |
| Review predictions | `core/label_inspector.py`, `core/labelimg_launcher.py` | `gui/labelimg_page.py` | `gui/workers/label_inspector_worker.py`, `gui/workers/labelimg_worker.py` | `tests/test_label_inspector.py`, `tests/test_label_inspector_worker.py`, `tests/test_labelimg_worker.py` |
| Train | `core/trainer.py` | `gui/train_page.py` | `gui/workers/train_worker.py` | `tests/test_trainer.py`, `tests/test_train_worker.py` |
| Infer | `core/inferencer.py` | `gui/infer_page.py` | `gui/workers/infer_worker.py` | `tests/test_inferencer.py`, `tests/test_infer_worker.py` |
| Restore | `core/restorer.py`, `core/annotation_formats.py` | `gui/restore_page.py` | `gui/workers/restore_worker.py` | `tests/test_restorer.py`, `tests/test_restore_worker.py`, `tests/test_annotation_formats.py` |
| Convert | `core/converter.py`, `core/annotation_formats.py` | `gui/convert_page.py` | `gui/workers/convert_worker.py` | `tests/test_converter.py`, `tests/test_convert_worker.py`, `tests/test_annotation_formats.py` |
| Desktop shell | no core owner | `gui/app.py`, `gui/workbench.py`, `gui/tool_page_chrome.py`, `gui/tool_defaults.py` | `gui/task_runner.py`, `gui/workers/_task_lifecycle.py` | `tests/test_gui_shell.py`, `tests/test_task_runner.py`, `tests/test_service_cancellation.py` |
| Shared infrastructure | `utils/mapping_manager.py`, `utils/task_registry.py`, `utils/device.py`, `utils/path_encoder.py`, `utils/exceptions.py`, `utils/logging_setup.py` | `gui/path_picker.py` | `gui/workers/_task_lifecycle.py` | `tests/test_mapping_manager.py`, `tests/test_task_registry.py`, `tests/test_device.py`, `tests/test_path_encoder.py`, `tests/test_exceptions.py`, `tests/test_logging_setup.py`, `tests/test_path_picker.py` |
| Server operations | `server_scripts/train_yolo.py`, `server_scripts/predict_yolo.py` | none | none | `tests/test_server_scripts.py` |

Integration coverage currently lives under `tests/integration/` with
scenario-style tests. Architecture and import discipline are covered by
`tests/test_contracts.py`, `tests/test_imports.py`, and
`scripts/check_disciplines.py`.

When a module change spans layers, update in this order:

1. Product or UI spec only if the documented behavior changes.
2. Core dataclass, validation, result, and business operation.
3. Thin worker adapter and task lifecycle payload.
4. GUI page state, preflight display, result display, and errors.
5. Focused core, worker, GUI, and integration tests.
6. `CHANGELOG.md` if the change affects handoff, usage, behavior, safety, or
   verification.

## Constraints

Source priority when files disagree:

1. Active executable code paths.
2. Passing tests and smoke checks.
3. `AGENTS.md`, `docs/dev/PRODUCT_SPEC.md`, and `docs/dev/UI_SPEC.md`.
4. `README.md`, `CHANGELOG.md`, and retained docs.
5. Historical plans, stale screenshots, archived notes, or `legacy/`.

Architecture rules:

- `core/` must not import GUI or HTTP frameworks.
- `utils/` must not depend on `core/`.
- `gui/workers/` must call `core/` directly, not runtime services.
- Public core entrypoints keep the single dataclass config contract.
- New business exceptions inherit `AutoLabelerError` and carry an `ErrorCode`.
- Use `pathlib.Path` for paths.
- Use `MappingManager` for `mapping.json`.
- Long-running work uses `TaskHandle` and `TaskRegistry`.

Product rules:

- Flow mode starts from strict `site/Code/Product/image` structure.
- `mapping.json` belongs to Flow traceability only.
- Independent mode must not secretly create or require mapping.
- Flow sampling copies source images; Independent sampling moves only selected
  files and leaves unselected files in place.
- Move, delete, overwrite, restore, and clear actions require preflight before
  execution.
- Destructive or high-risk actions require inline confirmation.
- Training expects a standard YOLO dataset with `images/*`, `labels/*`, and
  `data.yaml`.
- Review uses external LabelImg and editable prediction labels, not an internal
  annotation editor.

UI rules:

- Keep the light main workspace, dark side navigation, and restrained accent.
- Preserve each tool's inputs, outputs, summaries, errors, and confirmations.
- Use `gui/path_picker.py` for path inputs; keep numeric and strategy controls
  as normal widgets.
- Do not add decorative gradients, card spam, or invented controls.
- Update `UI_SPEC.md` only when GUI behavior, layout, or verification rules
  change.

Collaboration rules:

- Touch only files needed by the task.
- Do not modify `tests/A9950/` without explicit approval.
- Update `CHANGELOG.md` for notable product, architecture, test, or retained
  doc changes.
- Update `PRODUCT_SPEC.md` only when product behavior changes.
- Do not add dependencies without owner approval.

## Completed Work

- Desktop GUI is the active first-version product surface.
- `core/` is framework-free business logic, and `gui/workers/` directly adapts
  it for desktop tasks.
- Deleted `cli/` and `runtime/services` are no longer active architecture.
- Product and GUI baselines are consolidated in `PRODUCT_SPEC.md` and
  `UI_SPEC.md`.
- The GUI shell includes login, homepage, navigation, task center, manual,
  settings, and all eight module pages.
- Tool pages use shared chrome, path picker controls, task feedback, and
  page-specific result/error surfaces.
- Core workflows cover scan, sample, LabelImg launch/review, train, infer,
  restore, and convert.
- Server training and prediction scripts remain under `server_scripts/` as
  standalone operational tools.
- Tests cover core contracts, import boundaries, GUI shell behavior, path
  picker behavior, workers, task lifecycle, core modules, server scripts, and
  integration scenarios.

Do not reopen these decisions casually:

- GUI-first product direction.
- Framework-free `core`.
- No active CLI/runtime service/web API architecture.
- AI remains preview/reserved until explicit behavior is specified.

## Risks And No-Go Areas

Highest-risk change areas:

- `core/sampler.py`: copy vs move semantics, label conversion, output safety,
  empty labels, grouping, and preflight.
- `core/restorer.py`: writes labels back to original locations; confirmation
  boundaries matter.
- `core/inferencer.py` and `core/trainer.py`: device handling, Ultralytics
  behavior, output structure, and error wrapping.
- `gui/workbench.py`: large central shell; keep edits surgical.
- `gui/*_page.py`: page state can drift from `PRODUCT_SPEC.md`.
- `server_scripts/`: standalone server tools; do not make GUI depend on them.

No-go areas unless explicitly approved:

- Reintroducing CLI, FastAPI, browser UI, Node integration, or runtime service
  layers.
- Editing generated runs, model weights, caches, or reserved real test data as
  source changes.
- Editing or copying from `legacy/`.
- Bypassing `MappingManager`.
- Hiding new behavior inside GUI pages instead of extending typed `core`
  contracts first.
- Running destructive filesystem operations without the required preflight and
  confirmation path.

Operational risks worth remembering:

- Multi-GPU Ultralytics DDP child-process logs can bypass the parent script log
  if shell output is redirected to `/dev/null`; use explicit nohup log files.
- `cache=ram`, `batch=-1`, high `workers`, and multi-GPU DDP together can make
  training startup harder to diagnose.
- Long Windows paths can break layouts unless wrapped, compacted, or moved into
  details/tooltips.
- Some UI/source text is Chinese; preserve UTF-8.
- The worktree may contain unrelated user changes or generated artifacts. Do
  not revert files outside the current task.

## Reading Order

Read these first:

1. `AGENTS.md`: repo rules and hard boundaries.
2. `docs/dev/PRODUCT_SPEC.md`: product behavior contract.
3. `docs/dev/UI_SPEC.md`: GUI behavior and layout baseline.
4. `README.md` and `CHANGELOG.md`: entry point and recent decisions.
5. `gui/app.py` and `gui/workbench.py`: desktop entrypoint and shell.
6. The GUI page, worker, and `core` module for the feature you will touch.
7. `utils/mapping_manager.py`, `utils/task_registry.py`, and
   `utils/exceptions.py` when work touches mapping, tasks, or errors.
8. `tests/test_contracts.py`, `tests/test_imports.py`, and tests matching the
   files you will touch.
9. `server_scripts/README.md` only when working on offline server training or
   prediction.

Historical plans, archived docs, screenshots, deleted architecture, and
`legacy/` content are context only. Current code, tests, and retained docs are
the source of truth.
