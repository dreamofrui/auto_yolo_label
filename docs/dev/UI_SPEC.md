# AutoLabeler UI Spec

> Status: owner-confirmed GUI spec.
> Last updated: 2026-09-06
> Regression gate: `docs/dev/UI_REGRESSION_BOUNDARY.md`.

This document defines the first-version desktop GUI direction. It complements
`docs/dev/PRODUCT_SPEC.md`; when product behavior and UI differ, clarify before
implementation.

## 1. UI Goal

AutoLabeler is a desktop-first semi-automatic labeling workbench. The GUI must
feel like a polished production tool, not a collection of scripts.

Primary users are employees who use individual functions or run the full
labeling workflow. The interface must also be presentable to leadership, so the
first screen should communicate product value clearly.

Success means the user can complete these eight entries from the GUI with real
backend integration:

- Scan
- Sample
- LabelImg labeling
- Train
- Infer
- LabelImg review
- Restore
- Convert

Each entry must provide clear inputs, running state, progress or stage
feedback, logs, result summary, and actionable errors.

## 2. Design Direction

Use a calm, high-trust visual language for professional visual-data operations:

- **Canvas:** cool mist `#F4F7FA` with white workflow surfaces
- **Navigation:** deep navy `#101C2E` with clear inverse text hierarchy
- **Actions:** cool teal `#0C766E`; champagne `#C89B5B` is a brand detail only
- **Typography:** Inter first, with Microsoft YaHei UI/Segoe UI fallbacks;
  regular 32px page titles and a compact 14px body scale
- **Depth:** thin borders and low-diffusion shadows; no glassmorphism or visual
  noise

Design rules:

- Follow the UI workflow requirements in `AGENTS.md` before UI design or
  implementation work.
- Use Qt-native techniques only; keep hover/pressed/focus feedback short and
  skippable (120–180ms) and respect system reduced-motion settings
- Colors follow WCAG 2.2 AA contrast requirements (see `UI_STANDARD.md`)
- Typography is fixed (not viewport-scaled)
- Keep all pages usable in smaller desktop windows (minimum 1024×680px)

The complete visual token source is `gui/design_system.py`; generated widget
styles live in `gui/theme_manager.py`. This document remains the behavior and
layout baseline, while `docs/adr/0002-enterprise-visual-language.md` records
the rationale for the current visual direction.

## 3. App Shell

The app uses a workbench layout:

- Login page before entering the workbench.
- Dark left navigation with the homepage and eight module entries.
- Main content area for homepage or active tool page.
- Global lightweight task center entry.
- Settings and manual entry in the side navigation area, not as homepage
  primary content.

The homepage must be a single-screen product entry, not a scrolling landing
page. It should show:

- Product value statement.
- Eight module entry cards.
- Compact system strengths.
- One compact usage manual affordance. The full manual entry remains in side
  navigation or a dedicated help surface.
- Optional AI assistant preview area.

Do not show engineering noise such as Python interpreter, device, current work
directory, or recent run in the homepage top bar.

Small-window priority:

1. Module cards remain visible and primary.
2. Product value statement stays visible but may tighten copy.
3. System strengths compress to short labels.
4. Usage manual becomes a single compact affordance.
5. AI preview is the first optional content to collapse, hide, or mark as
   preview-only.

## 4. Login

First version login is:

- Enterprise SSO entry reserved in the UI.
- Local login or demo login for actual first-version access.
- No permissions system, multi-user collaboration, cloud auth, or server-side
  identity management in the first version.

The login page should look formal and enterprise-ready, but must not pretend to
provide security that has not been implemented.

## 5. Global Tasks

Use a lightweight task center, not a full task history system.

It should show:

- Running tasks.
- Recent tasks.
- Module name.
- Status.
- Start time.
- Result/output path when available.
- Failure reason entry when failed.
- Link back to the relevant tool page.
- Delete actions for terminal task records.

The task summary may filter the task list for high-signal categories such as
running tasks and failed/stopped/interrupted tasks. Filtered task-center views
must provide a clear return action back to the full task-center homepage.

Task rows must keep their primary text readable while preserving visible action
buttons at the right edge; long summaries must wrap instead of forcing
horizontal scrolling.

Switching pages must not lose running task state.

## 6. Tool Page Pattern

Tool pages use a page-specific workbench pattern:

- Left main area: title, mode switch, inputs, parameters, advanced settings,
  actions, and inline confirmation when needed.
- Right support area: a persistent AI assistant rail or preview, plus page-
  specific runtime feedback only when it is useful.

Use a left-main/right-support layout. Avoid three-column complexity for the
first version. Do not force a log surface onto pages that do not produce useful
runtime output.

Path-like fields should use the shared `gui/path_picker.py` control with browse
buttons and pasted-path acceptance; keep numeric and strategy inputs as plain
widgets.

Long result/status text, especially Windows paths, must not participate in
horizontal page sizing. Visible summaries should wrap or compact long paths and
preserve full values in tooltips, logs, or details.

For modules with Flow and Independent modes, use a top segmented control:

```text
Flow mode | Independent mode
```

The active mode must explain whether it depends on `mapping.json`.

For high-risk actions, use:

```text
Fill parameters -> Preflight -> Inline confirmation -> Execute
```

Use inline confirmation panels, not generic modal-first confirmation. Preflight
must finish before move, delete, overwrite, restore, or clear actions.

Two-column preflight layouts live inside the left main area. They may replace
the normal form summary after preflight, but they must not create a third
persistent column. The right support panel remains a persistent AI rail, and
pages may optionally place concise logs or state feedback there only when the
information is useful.

## 7. Right Support Panel

The right panel is a persistent AI assistant rail or preview on tool pages.
The current first version does not use a Task/AI tab strip inside each tool
page. The global task center remains a separate surface in the app shell.

AI must never bypass confirmation for destructive or high-risk actions. If AI
is not implemented, the assistant rail and homepage preview must be hidden,
disabled, or clearly marked as preview-only. The interface must not imply that
AI can execute real work before the feature exists.

## 8. Preflight, Results, and Errors

Preflight views should show both expected output and risks when needed.

Rules:

- Blocking issues prevent execution.
- Confirmation-only issues show an inline confirmation panel.
- Safe preflight enables execution.
- Flow mode copy operations should clearly say source files are not moved.
- Independent mode move operations should clearly say selected files will move
  and unselected files remain.

Results:

- Default view shows concise summary and output path.
- Details are expandable.
- Logs are copyable when the page actually exposes a log surface.
- Reports can be exported or copied where useful.
- Output folder can be opened.

Errors:

- Default error text is human-readable.
- Show what happened, why it matters, and what the user should do next.
- Technical details are expandable.
- Technical details may include error code, paths, exception detail, and log
  snippets.

## 9. AI Assistant Scope

AI is not required for the first version to work.

UI direction:

- Homepage may show a chat-like AI assistant preview.
- Tool pages may reserve a right-side AI assistant rail or preview.
- AI examples should be direct commands, such as selecting a folder or asking to
  prepare sampling, not generic "how do I use this" help.
- AI may later jump to a page and prefill fields, but execution must still wait
  for user confirmation.

Do not build core workflows that depend on AI.

## 10. Module Priority

Detailed GUI design and implementation should prioritize high-risk and complex
modules first:

1. Sample
2. Train
3. Infer
4. Restore
5. Convert
6. Scan
7. Label
8. Review

## 11. Sample Page

Default mode: Flow mode.

Mode switch:

- Flow mode: uses scanned site and mapping; copies files.
- Independent mode: uses explicit source paths; selected files move into the
  selected output; no mapping is created.

Sampling strategy control:

```text
count | ratio | mixed
```

Default strategy: `mixed`.

The form changes dynamically by strategy.

Flow fields:

- Scanned site folder.
- Mapping status.
- Output YOLO dataset folder.
- Sampling strategy and parameters.
- Train/validation ratio.

Independent fields:

- Source image folder.
- Output folder.
- Output format: `XML labeling folder | YOLO dataset`, default XML.
- Classes source or classes file only when YOLO output is selected.
- Sampling strategy and parameters.
- Train/validation ratio.

Default Independent XML output creates a structure-preserving folder for manual
VOC labeling: selected images keep their source-relative directories under the
output folder, existing same-stem XML labels move beside them, and no YOLO
dataset metadata is created. YOLO output remains available for users who
explicitly want the old dataset-shaped output. If classes are not provided for
YOLO output, the UI should state that an empty `classes.txt` will be created
and training will block until classes are filled.

Preflight layout uses two columns:

- Estimated sampling result: selected count, train/val count, group summary,
  labeled images kept, unlabeled images added.
- Risks and blocking issues: non-empty output, filename conflicts, empty labels,
  ambiguous folders, selected output format, move/copy count, confirmation
  needs.

Empty TXT labels are invalid. Any delete or cleanup action for empty TXT labels
requires explicit user confirmation and must not happen silently.

## 12. Train Page

Basic form fields:

- YOLO dataset directory.
- Initial model path.
- Output directory.

Common settings are visible by default and include:

- Device: CPU, GPU, Auto.
- Epochs.
- Image size.
- Batch size.

CUDA device choices should also expose clear labels for common local multi-GPU
training: `All GPUs`, `GPU 0`, `GPU 1`, and `GPU 0+1`. The training page and
usage manual must explain that multi-GPU `batch` is the total batch passed to
YOLO and `workers` is per training process, so total data loader workers grow
with the selected GPU count.

Advanced settings are collapsed by default and include less common YOLO training
parameters such as patience, workers, optimizer, learning rate, loss weights,
scale, cache, fixed run name, and overwrite confirmation.

The defaults should be usable for quick CPU smoke runs. Less common YOLO
parameters stay in advanced settings.

Runtime display:

- Show stage and summary by default.
- Show current epoch, total epochs, elapsed time, device, and output directory.
- Show metrics only when actually available.
- Raw YOLO logs are collapsed by default and can be expanded/copied.
- Completion emphasizes `best.pt` and `last.pt`, but the app must not
  automatically select the inference model for the user.

Validation and output rules:

- Invalid or missing `data.yaml` classes block training.
- Empty classes block training.
- `images/train` must be non-empty.
- `labels/train` must contain at least one valid label.
- Empty validation images or labels are warnings, not blockers.
- Negative samples are allowed and should be reported.
- Missing/empty labels should be counted and explained.
- Non-empty fixed output directories are refused by default and require user
  confirmation before clearing or overwrite behavior.
- Resume training is not a first-version mainline feature.

## 13. Infer Page

Flow mode source selection order:

1. Unsampled images, default.
2. All scanned images, optional.

The "all scanned images" option should explain that it includes sampled or
already labeled images, is mainly for full reruns or model checks, and only
updates `inferred` in `mapping.json` without changing `sampled`.

Basic form fields:

- Model path.
- Inference source/range.
- Confidence.
- IoU.
- Device: CPU, GPU, Auto.
- Batch.

In Flow mode, source/range is a prominent segmented choice:

```text
Unsampled images | All scanned images
```

In Independent mode, the user selects an image folder and an output root.

Advanced settings are collapsed by default and include less common or risky
output controls:

- Overwrite confirmation for an existing inference output directory when a fixed
  output location is explicitly reused.

The backend also has an internal `save_to_separate_dir` switch, but the product
contract keeps it enabled because first-version inference runs must be stored as
separate `run_YYYYMMDD_HHMMSS` directories.

Output behavior:

- In Flow mode, the output root is fixed to the scanned site
  `.autolabeler/inference_results/` location. The UI may show this path but
  must not imply it is freely user-changeable.
- In Independent mode, the user chooses only the output root.
- App automatically creates `run_YYYYMMDD_HHMMSS`.
- Preflight shows the exact run path that will be created.
- Existing run conflicts block or require regenerated names; never overwrite
  silently.
- Independent mode selects an image folder, recursively infers supported images,
  does not require or update mapping, preserves source relative structure under
  `run/labels`, and does not copy images.

## 14. Restore Page

Default source: Flow inference run.

Source modes:

1. Flow inference run: `run/labels` plus mapping.
2. Flow dataset labels: dataset labels plus mapping.
3. Independent restore: label root plus image root plus classes.

All restore sources require `classes.txt` or an equivalent resolved classes file
to convert class ids to VOC XML object names. Flow modes may resolve it from the
site `.autolabeler/classes.txt`, dataset, or run context; the resolved path must
be visible in preflight.

Restore is high risk and always requires preflight.

Preflight uses two columns:

- Match quality: labels, matched images, missing images, duplicate stems,
  invalid labels, classes status.
- Write impact and risk: XML files to write, target folders, existing XML
  conflicts, overwrite status, blocking issues, confirmation actions.

Rules:

- Existing XML blocks by default.
- Missing classes, missing images, duplicate same-stem images, invalid labels,
  and XML conversion errors block.
- Annotation failures keep the visible summary compact and put actionable
  diagnostics in the log: label path, line number, raw YOLO row, matched image
  path and size, class, converted pixel bounds, and the violated boundary.
- No file writes happen before preflight and confirmation.
- Completion shows written XML count, skipped count, failed count, and target
  locations.

## 15. Convert Page

Default view prioritizes the main feature:

```text
Image + XML directory -> standard YOLO dataset
```

Auxiliary conversions live in an advanced or collapsed tool area:

- YOLO TXT + images + classes -> VOC XML.
- VOC XML -> YOLO TXT.

Auxiliary conversion must be labeled as a helper. It does not infer original
business structure and does not replace Restore.

Main fields:

- Source directory containing images and XML.
- Output YOLO dataset directory.
- Train/validation ratio.
- Classes source: collect from XML or use existing `classes.txt`.

Rules visible in the UI:

- No mapping is used.
- No sampling strategies are used here; only train/validation ratio.
- Source images are copied, not moved.
- Original file names are preserved.
- Image-without-XML and XML-without-image are skipped and counted.
- The conversion does not do incremental merge.
- Preflight failure writes no partial dataset.

Flow:

1. Analyze.
2. Show collected or provided class list and order.
3. User confirms class order.
4. Convert.

Blocking issues:

- XML parse errors.
- Filename conflicts.
- No valid image/XML pairs.
- XML object names missing from provided classes.
- Non-empty output unless user explicitly confirms clearing.

Result summary:

- Valid image/XML pairs.
- Skipped images.
- Skipped XML files.
- Class count.
- Output path.

## 16. Scan Page

Scan is low risk but defines Flow mode.

UI:

- Short default note: Flow scan requires `site / Code / Product / image`.
- Expandable directory example.
- Site root selector.
- Preflight/scan action.

Errors:

- Invalid structure lists offending paths.
- Same `Code/Product` same-stem conflicts block.

Success summary:

- Image count.
- Class count.
- Product group count.
- `mapping.json` path.
- `classes.txt` path.

## 17. LabelImg and Review Page

The app keeps two navigation entries:

- Label
- Review

Both can reuse one LabelImg page component with different default mode.

Modes:

- Free labeling.
- Prediction review.

Free labeling fields:

- Image folder.
- Format switch: `YOLO labeling | VOC labeling`.
- YOLO labeling: non-empty `classes.txt` and label output folder.
- VOC labeling: image folder only; LabelImg writes same-stem XML beside images.
- The preflight action validates the selected Python/LabelImg environment and
  current mode inputs before launch. It should report missing image folders,
  missing or empty YOLO `classes.txt`, and unreadable image folders without
  starting LabelImg.
- Successful launch logs show concise user-facing details such as PID and mode,
  not internal wrapper source code or full `python -c` commands.

Prediction review fields:

- Site root.
- Inference run dropdown on one line.
- Code/Product tree node.

Review behavior:

- Uses mapping to resolve original images.
- Uses `run/labels` as editable prediction label root.
- Code/Product tree rows must give product names enough width to display in
  full, especially after long encoded product names from inference runs.
- Preparing review is a useful preflight because it resolves original images,
  prediction label paths, classes, and missing-label warnings. It should not be
  a mandatory extra click: Open Review may run the prepare step automatically
  before launching LabelImg.
- Prepared-path summaries use compact paths in the visible panel and full paths
  in tooltips/details so long Windows paths cannot stretch the page horizontally.
- Prepare/Open Review actions stay above the prepared-path summary so they
  remain reachable in smaller desktop windows.
- Missing original images block.
- Missing labels warn but do not block.
- Independent inference review uses Free Labeling.
- Review mode does not need a bottom log box if the tree/list and status summary
  already provide the useful feedback.

LabelImg missing or invalid classes should block launch with human-readable
error text and expandable technical details.

## 18. Non-Goals

First-version GUI does not include:

- Built-in bounding-box editor.
- Web UI.
- Node integration.
- Multi-user permissions.
- Cloud storage.
- Complex project database.
- Full task history system.
- AI-dependent workflows.
- Automatic source directory cleanup.
- Silent file moves, deletes, or overwrites.

## 19. Verification Expectations

Before claiming GUI work complete:

- Each implemented page can call its backend worker/core path.
- Long-running tasks do not freeze the UI.
- Task states, useful logs, results, and errors render where the page needs
  them.
- High-risk operations require preflight and inline confirmation.
- Flow/Independent dependencies are visible to the user.
- Small desktop windows remain usable.
- UI changes are reviewed using the required UI skills.
