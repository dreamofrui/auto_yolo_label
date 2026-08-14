# Changelog

All notable changes to this repo are recorded here.

## [Unreleased]

### Product / GUI

- Redesigned login page with painpoint-driven narrative: shows the annotation
  problem first ("万张图像，逐张标注？"), then the solution (半自动化), quantified
  proof (100 → 10,000), process flow, and trust markers. Removed function module
  cards and boundary panels for cleaner focus. Updated left panel to dark theme
  (#1a3743) with unified brand colors (#007b78) matching the main workbench.
- Redesigned utility navigation buttons (首页、任务中心、使用手册、设置) with
  compact single-line layout, emoji badges (🏠 📋 📖 ⚙️), reduced height from
  50-56px to 40px, and improved text contrast (#b8d4db) for clearer visual
  hierarchy against flow buttons.
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

- Added `docs/dev/ARCHITECTURE.md` as the current architecture description:
  system context, dependency direction, module responsibilities, key data
  flows, persistence locations, long-running task ownership, and external
  integrations. Excludes completed-work lists, per-file maps, risk logs,
  reading orders, and future plans.
- Separated architecture direction out of `docs/dev/PRODUCT_SPEC.md` so the
  product contract now covers only externally observable Flow and Independent
  mode behavior, inputs, outputs, validation, failure conditions, and
  destructive-operation safety guarantees.
- Kept old retained documents (`ONBOARDING_SUMMARY.md`, `UI_SPEC.md`) in place
  as temporary migration input while the new structure is reviewed.
- Rebuilt the interrupted Trellis bootstrap into codebase-backed specs for the
  core, GUI, worker, utility, and standalone server-script layers, with
  project-specific cross-layer and reuse guides.
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


### Documentation

- Added `docs/dev/UI_STANDARD.md` as the forward-looking UI standard: desktop
  product goals, information hierarchy, keyboard and focus behavior, WCAG 2.2 AA
  contrast and semantic state roles, fixed typography, responsive structure and
  small-window priority, error/loading/empty states, and Qt desktop interaction
  conventions. Gaps are recorded as future work rather than standard exceptions.
  Page-specific business behavior remains in PRODUCT_SPEC.md and UI_SPEC.md.

### Server Scripts

- Upgraded `scripts/ui_snapshot.py` to capture all GUI surfaces (login,
  workbench, modules, task-center, manual, settings) at more than one desktop
  size (defaults: 1440x900 and 1280x720). Output defaults to the git-ignored
  `.ui-snapshots/` directory; PNGs are not preserved as source assets.
  Added `.ui-snapshots/` to `.gitignore`.

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

### Documentation

- Consolidated `AGENTS.md` as the canonical agent rules: active workflow,
  architecture boundaries, filesystem safety, verification requirements,
  protected assets, disabled Trellis workflow, and mandatory GitNexus checks.
  Removed the trailing Trellis block. Added explicit Filesystem Safety section.
- Simplified `CLAUDE.md` to point to `AGENTS.md` for canonical rules, keeping
  only Claude-specific Direction guidance and the explicit Trellis reminder.
- Pruned `CONTEXT.md` glossary to only the implemented Annotation and Annotation
  Format terms; removed Annotation Diagnostic term.
- Retained only the strict Annotation bounds ADR (`0001`); removed the eight
  draft, strategy-only, or incomplete ADRs (`0002`–`0009`).


