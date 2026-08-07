# Changelog

All notable changes to this repo are recorded here.

## [Unreleased]

### Product / GUI

- Fixed tool page header stretch and enhanced utility nav buttons with structured
  two-line layout (badge + title + subtitle) matching flow button visual density.
- Expanded Restore validation logs with the exact label row, matched image,
  class, converted pixel bounds, and violated boundary while keeping the
  visible failure summary compact.
- Moved persisted tool defaults from the user home directory to the project's
  ignored `.autolabeler/tool_defaults.json` runtime file.
- Updated Task Center rows so action buttons remain visible with long summaries,
  and added clickable 运行中/需要处理 summary filters with a return action to
  the full task list.
- Changed Scan to ignore existing VOC XML label files during Flow metadata
  creation and to block unsupported non-image/non-XML files in Product folders.
- Added explicit training CUDA device choices with clear labels for `All GPUs`,
  `GPU 0`, `GPU 1`, and `GPU 0+1`, plus usage-manual guidance for multi-GPU
  batch and workers semantics.
- Changed Independent Sample output to default to a structure-preserving XML
  labeling folder for LabelImg workflows, while keeping YOLO dataset output as
  an explicit option.
- Added the PySide6 desktop shell with login, homepage, left navigation, task
  center, usage manual, settings, and concrete pages for Scan, Sample, Label,
  Train, Infer, Review, Restore, and Convert.
- Added a YOLO/VOC switch to the LabelImg labeling page; VOC mode opens an
  image folder and writes Pascal VOC XML beside images.
- Fixed VOC LabelImg launch so validation no longer displays CLI help text and
  A/D image navigation no longer opens the save-directory picker.
- Changed LabelImg preflight to validate current mode inputs before launch and
  cleaned launch logs so internal wrapper code is not shown in the GUI.
- Refreshed the PySide6 desktop GUI visual hierarchy, including the login page
  and dense tool-page status/risk/result surfaces, without changing module
  inputs, outputs, worker interfaces, or confirmation boundaries.
- Changed homepage module entries to use neutral default cards with whole-card
  hover and click behavior, removing the previous default Sample emphasis.
- Added the shared `gui/path_picker.py` path input widget and
  `gui/task_runner.py` task runner abstraction for GUI execution.

### Architecture

- Documented staged annotation migration through Restore, Convert, and Sample,
  with private format implementations removed after each adoption step.
- Reframed the active architecture around the PySide6 desktop GUI, stable
  framework-free `core/`, and thin `gui/workers/` adapters that call `core/`
  directly.
- Added standard YOLO/VOC annotation helpers used by restore and conversion
  flows.
- Added worker-level cancellation lifecycle handling after removing the
  temporary runtime service layer.

### Server Scripts

- Kept standalone server training/prediction scripts documented in their own
  folder; they remain separate from the desktop GUI architecture.
- Added an optional inference label Y-offset parameter for desktop inference
  and `server_scripts/predict_yolo.py`, so consistently high saved boxes can be
  shifted down by source-image pixels without changing box size.

### Documentation

- Documented one canonical LabelImg-compatible VOC XML serialization for
  annotation workflows instead of preserving conflicting historical layouts.
- Added `CONTEXT.md` to define Annotation and Annotation Format as shared
  domain terms across YOLO TXT and Pascal VOC XML workflows, including strict
  rejection of out-of-bounds annotations and shared Annotation Diagnostics.
- Added per-repo engineering-skill configuration for GitHub issue tracking,
  canonical triage labels, and single-context domain docs.
- Added contributor rules requiring bug fixes to be traced to specific
  functions and call paths, with a lightweight flow for small single-function
  fixes.
- Tightened the product contract in `docs/dev/PRODUCT_SPEC.md` around Flow and
  Independent modes, mapping ownership, safe preflight behavior, LabelImg
  review, training, inference, restore, and conversion.
- Tightened the GUI contract in `docs/dev/UI_SPEC.md` around the workbench
  shell, tool pages, task feedback, settings, manual page, and page-level
  verification expectations.
- Simplified repository instructions in `AGENTS.md` so contributor rules point
  only to retained long-term docs.
- Rewrote `README.md` as the compact project entry point.
- Added `docs/dev/ONBOARDING_SUMMARY.md` as a handoff guide for engineers
  taking over maintenance or new feature work.
- Added the onboarding guide to first-read documentation entry points and
  extended it with a code-level module maintenance map.

### Tests

- Documented the annotation test seam: format behavior belongs to the shared
  module interface, while feature and worker tests retain policy and lifecycle
  coverage without duplicating private parser tests.
- Added scanner coverage for ignoring XML label files and rejecting unsupported
  Product-folder files.

### Removed

- Deleted the inactive `cli/` surface and its CLI JSON tests.
- Deleted the temporary `runtime/services` layer; desktop workers now call
  `core/` directly.
- Removed obsolete web/API docs, stale implementation plans, current-state
  journals, static GUI mockups, old user guides, project-specific scratch
  notes, and repo-local agent skill docs from the active documentation set.
- Removed `CLAUDE.md`; `AGENTS.md` is now the single contributor-rule entry.
