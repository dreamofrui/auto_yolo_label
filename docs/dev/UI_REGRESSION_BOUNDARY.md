# AutoLabeler UI Regression Boundary

> Status: owner-confirmed migration gate.
> Last updated: 2026-08-20.
> Origin: GitHub Issue #25, under the UI redesign route in Issue #24.

This document defines the user-visible behavior that must survive each PySide6
UI redesign batch. It turns the product and GUI contracts into an executable
regression boundary without making the current widget tree a permanent design
interface.

It does not authorize product behavior changes. `PRODUCT_SPEC.md` remains the
product contract, `UI_SPEC.md` remains the current GUI behavior and layout
contract, and `UI_STANDARD.md` remains the forward-looking shared UI standard.
This document defines how a redesign batch proves that it still satisfies those
contracts.

## 1. Gate Policy

Regression evidence is split into three gates. Passing one gate never
substitutes for another.

| Gate | Scope | Merge policy |
|------|-------|--------------|
| Functional and safety | Product results, filesystem gates, task lifecycle, worker configuration, and LabelImg boundaries | Always blocking |
| Touched-surface semantics | Keyboard access, small-window use, accessible names, loading/empty/error states, and readable paths on changed pages or shared shell surfaces | Blocking for every touched surface |
| Visual quality | Hierarchy, density, alignment, typography, color, responsive composition, and state clarity | Human review required; screenshots do not prove behavior |

Known gaps on an untouched page do not block an unrelated migration batch, but
they must not become worse. Once a page is migrated, the applicable semantic
gaps in this document become part of that page's blocking gate. A shared shell,
navigation, stylesheet, task surface, or shared control change activates the
gate for every affected consumer.

## 2. Batch Scope and Evidence

A migration batch owns:

- every page or shared component changed by the batch;
- every page whose layout, navigation, task state, styling, or shared control
  behavior can change as a consequence;
- the core and worker contracts exercised by those user flows, even when their
  implementation is unchanged.

Every batch must provide:

1. Focused semantic GUI tests for each touched workflow and state.
2. Focused worker/core tests when the GUI still depends on those contracts.
3. A passing complete `tests/gui/` suite.
4. A passing complete project test suite before merge.
5. Screenshots for affected surfaces and states at the required sizes and DPI.
6. The applicable real smoke result for LabelImg or asynchronous task flows.
7. A short record of known pre-existing gaps that remain out of scope.

## 3. Stable Test Interface

Workflow tests observe behavior through user actions and public outcomes. They
may assert:

- the current application route or page identity;
- whether a user action is available, blocked, running, stopped, or complete;
- worker input dataclasses and typed outcomes at the desktop adapter boundary;
- visible summaries, risks, progress, errors, and recoverable technical detail;
- persisted `TaskHandle` state and output paths;
- filesystem results only through the operation's public workflow.

Tests must not preserve the following as compatibility contracts:

- Python widget member names or the exact widget nesting hierarchy;
- styling-only `objectName` values such as `logBox`, `leftMainPanel`, or
  `riskCheckbox`;
- exact pixel coordinates, row indexes, fixed heights, or a specific Qt layout
  class when the user-visible result is unchanged;
- complete marketing copy or punctuation;
- the absence of old private members through `hasattr` assertions.

### Semantic Locators

Migrated controls use `accessibleName` as the stable automation and
accessibility locator. `objectName` remains an internal styling mechanism and
may change with the design.

Use names from these families where the control exists:

| Family | Examples |
|--------|----------|
| Page | `page.home`, `page.sample`, `page.restore` |
| Navigation | `nav.home`, `nav.sample`, `nav.tasks` |
| Action | `action.login`, `action.preflight`, `action.confirm`, `action.run`, `action.stop`, `action.prepare`, `action.launch` |
| Field | `field.site`, `field.output`, `field.model`, `field.classes` |
| State | `state.summary`, `state.details`, `state.progress`, `state.empty`, `state.error` |

Names identify meaning, not position or presentation. Repeated controls add a
domain qualifier, for example `restore.action.preflight`, when a page-scoped
test cannot disambiguate them.

Visible text assertions use stable meaning rather than full string equality.
Safety consequences, blocking reasons, confirmation actions, recovery advice,
and the standard terms `mapping.json`, `classes.txt`, Flow, Independent, YOLO,
and LabelImg must remain unambiguous. Titles, marketing copy, and explanatory
phrasing may change.

### Existing Qt Properties

The current GUI also uses Qt properties that must be classified before a page is
migrated:

- `feedbackRole`, `buttonRole`, and `surfaceRole` are visual or semantic state
  hints. Preserve the user-visible meaning (explanation, result, risk,
  confirmation, product/access boundary), but do not preserve the property name
  or exact stylesheet value as the workflow contract.
- `task_id`, `module_key`, and `filter_key` are task-center routing metadata.
  Tests must assert the user outcome (delete the selected terminal task, open
  the owning module, or apply the selected filter), not the metadata property.
- `current_module_key()` is a route outcome seam. Keep asserting the active
  route through a page-level semantic identity even if the helper method or
  widget attribute changes.

## 4. Behavior Invariants

### Login, Shell, and Tasks

- A supported local or demo login enters the workbench at the product homepage.
- Reserved SSO presentation must not imply working cloud authentication.
- Homepage and navigation expose the supported product workflows, regardless
  of whether they are rendered as cards, lists, or another accessible control.
- Selecting a navigation destination opens the correct page and communicates
  the active route.
- Navigating away from a running task does not cancel it or lose its state.
- The task center shows running and recent supported tasks, progress, terminal
  result or failure information, and the route back to the owning page.
- Returning to a running page renders the latest persisted progress and permits
  supported stop behavior.

### Sample

- Flow mode uses the scanned site and `mapping.json`, copies selected files,
  and preserves the source tree.
- Independent mode uses explicit paths, does not create mapping, and clearly
  distinguishes XML and YOLO output.
- Independent moves cannot start until preflight succeeds and the user confirms
  the move impact. Unselected files remain in place.
- Blocking preflight issues keep execution disabled and cause no writes.
- Changing a preflight-relevant input invalidates the prior result and
  confirmation.
- Empty TXT cleanup or deletion is never silent and requires explicit consent.

### Restore

- Every source mode resolves images, labels, classes, conflicts, and write
  targets before any XML write.
- Missing classes or images, duplicate same-stem images, invalid labels, and
  conversion errors block execution.
- Existing XML blocks by default. An allowed overwrite still requires a passed
  preflight and explicit write confirmation.
- Changing a relevant source or overwrite input invalidates prior confirmation.
- Failure summaries stay concise while actionable conversion diagnostics remain
  available in technical details.

### Convert

- Dataset conversion analyzes valid pairs, skips, class order, output risk, and
  blockers before conversion is enabled.
- The user confirms class order after successful analysis.
- Invalid analysis, missing confirmation, or a stale analysis after input
  changes prevents conversion and causes no partial dataset write.
- Images are copied, original names are preserved, mapping is not used, and a
  non-empty output requires the documented confirmation behavior.

### Train, Infer, and Convert Runtime

- Long-running work uses an asynchronous desktop runner; the UI remains
  responsive and permits navigation while work continues.
- Starting a task renders a running state, useful progress or stage, and its
  output destination when known.
- Returning to the page or task center restores the latest persisted progress.
- Where a page exposes stop/cancel (currently Train and Infer), it is available
  only for a stoppable active task, records a cancellation request, and renders
  the eventual stopped outcome without misreporting failure.
- Convert currently exposes asynchronous progress and terminal success/error
  but no stop control. This ticket does not invent one; a future Convert stop
  action requires a separate product decision and then adopts the same stop
  semantics.
- Success renders the typed result and relevant output path. Failure renders a
  human-readable summary plus available technical details.
- Flow and Independent Infer continue to honor their mapping and output-root
  rules, including separate timestamped run directories.

### Label and Review

- Label preflight validates the selected image path, environment, annotation
  format, and non-empty YOLO classes before launching LabelImg.
- VOC labeling launches against the image directory and writes same-stem XML
  beside images without requiring YOLO fields.
- Review resolves the site, inference run, mapping node, original images,
  editable prediction labels, and classes before launch.
- The Code/Product tree keeps long product names fully understandable through
  visible text, horizontal availability, or a full-value tooltip; selecting a
  product node and expanding or moving through the tree remain keyboard
  operable.
- Missing original images block review. Missing prediction labels warn without
  blocking valid images.
- Open Review may prepare automatically, but changed inputs invalidate prepared
  paths and force fresh resolution.
- The external launcher receives the resolved public configuration; internal
  wrapper source or complete command strings are not user-facing output.

### Shared Inputs and Feedback

- Path controls accept pasted paths with wrapping quotes and browse-selected
  files or directories.
- A blank path is rejected before it can resolve to the process working
  directory.
- Long Windows paths wrap or compact within the available panel; their full
  value remains available through a tooltip or details surface.
- Chinese and English text, spaces, and long path segments do not overlap,
  truncate a required action, or force horizontal page growth.
- Loading, empty, error, warning, success, stopped, and disabled states remain
  distinguishable without color alone.
- Error presentation explains what happened, why it matters, and the next
  action; technical details are reachable but do not dominate the default view.

## 5. Existing GUI Test Migration

The current tests are migration input, not the definition of the redesigned
widget tree. Apply the following disposition when a page is touched.

| Disposition | Existing examples | Required replacement or preservation |
|-------------|-------------------|--------------------------------------|
| Preserve the workflow | `test_login_enters_workbench`; Sample preflight and Independent confirmation tests; Restore preflight/confirmation tests; Convert analysis/class-confirmation tests | Keep the user action, blocking state, and public outcome; switch lookup to semantic locators |
| Preserve public configuration | Train/Infer configuration tests; Label YOLO/VOC launch tests; Review launch configuration tests | Assert typed worker configuration and result, not form construction |
| Preserve lifecycle behavior | Train/Infer persisted-progress and cancellation tests; task-center running-progress tests | Add navigation-away/return and eventual callback completion at the public page/task seam |
| Rewrite as semantic layout behavior | Long-path tests; Review action reachability and product-name visibility | Assert no horizontal overflow, required actions remain reachable, and full data remains available; do not assert layout row numbers or resize modes |
| Move to visual review | Login region styling; homepage card height/geometry; strengths alignment; panel spacing; stylesheet role coverage | Capture the required state and review hierarchy, density, alignment, contrast, and clipping |
| Remove implementation-only assertions | Exact styling `objectName`; `findChild("toolScrollArea")`; exact marketing strings; absence of retired widget attributes | No replacement unless a user behavior or accessible semantic role would otherwise be untested |

Current gaps to activate when their surface is migrated:

- a real asynchronous start, navigate-away, return, stop, and completion flow
  for Train/Infer; Convert currently requires start, progress, navigation-away,
  terminal success, and error coverage but has no stop control;
- keyboard-only login, navigation, confirmation, and primary actions;
- consistent `accessibleName` coverage for interactive controls;
- loading, empty, and expandable error-detail states outside the currently
  covered Restore path;
- mixed Chinese/English/space/long-segment path cases;
- complete missing-image and missing-label Review outcomes;
- a real LabelImg launch smoke test on a configured development machine.

## 6. Minimum Verification Matrix

### Window and DPI

The supported minimum window is `1024x680`; the baseline review window is
`1440x900`.

| Window | Scale | Required use |
|--------|-------|--------------|
| `1024x680` | 100% | Every batch: minimum-window actions, wrapping, overflow, and scrolling |
| `1024x680` | 150% | Every batch: text scaling, focus, target reachability, and clipping |
| `1440x900` | 100% | Every batch: baseline composition and full affected state set |
| `1440x900` | 200% | Shared shell batches and Sample, Restore, or Convert high-risk surfaces |

No guarantee is made below `1024x680`. A test may use offscreen rendering, but
a DPI claim requires the configured Qt scale to be recorded in the evidence.

Use at least one mixed path fixture such as
`D:/视觉数据/Site A/Code_01/超长产品名称/images/sample 01.jpg`.

### Keyboard

Every migrated page provides one complete keyboard-only primary path:

- Tab order follows visible reading order and skips decoration.
- Enter activates the focused primary action.
- Space changes a mode or confirmation control.
- Escape closes the current pop-up or cancels the current inline confirmation.
- Focus remains visible, and navigation does not silently move focus to
  unrelated chrome.

The shared shell migration must cover login, side navigation, task center, and
return to the owning page. No new undocumented shortcut is required.

### State and Screenshot Coverage

| Surface | Required states when touched |
|---------|------------------------------|
| Login and shell | Logged out, logged in/home, active navigation, running task, terminal task, task error |
| Sample | Flow preflight, blocker, Independent move confirmation, success |
| Restore | Match/write preflight, blocker, overwrite/write confirmation, expanded error details, success |
| Convert | Initial, analysis result, blocker, class confirmation, running, success/error |
| Train and Infer | Initial, running progress, navigate-away/return, stop requested, stopped, success, error |
| Label | YOLO and VOC input states, blocking preflight error, passed preflight, launched result |
| Review | Empty run/tree, prepared node, missing-image blocker, missing-label warning, long paths and long product names, keyboard tree selection, launched result |

Screenshot review checks hierarchy, readable labels, visible focus and state,
reachable primary and confirmation actions, absence of incoherent overlap or
horizontal overflow, and correct loading/empty/error presentation. Screenshots
are generated as review artifacts, are not committed, and are not evaluated by
a pixel-equality merge threshold.

## 7. Real Smoke Boundary

Automated GUI tests normally use deterministic fake workers to prove page
configuration and state rendering. A batch additionally runs:

- one real LabelImg preflight and launch when Label or Review changes;
- one real asynchronous start, navigation-away/return, stop, and result/error
  flow when Train, Infer, the task runner, registry display, or shared task
  shell changes;
- one real asynchronous start, progress, navigation-away/return, and
  terminal result/error flow when Convert changes. Convert stop coverage is
  activated only if a separately approved stop action is introduced.

The asynchronous smoke may use a quick controlled operation. It does not need
to run a complete model training job. Real data must follow the repository
filesystem-safety rules and must not use `tests/A9950/` without approval.

## 8. Per-Batch Checklist

Before implementation:

- [ ] List touched pages, shared components, and affected public workflows.
- [ ] Map each workflow to the behavior invariants above.
- [ ] Record pre-existing gaps that are not activated by this batch.

Automated verification:

- [ ] Run the focused page test file after each semantic slice.
- [ ] Run affected worker/core tests.
- [ ] Run `tests/gui/` after the batch is assembled.
- [ ] Run the complete project suite before merge.

Interaction and visual verification:

- [ ] Run the complete keyboard path for each migrated page.
- [ ] Capture affected states at the required window/DPI matrix.
- [ ] Review visuals separately from behavior and safety results.
- [ ] Run the applicable LabelImg or asynchronous smoke.

Merge evidence:

- [ ] Record commands, results, screenshot locations, scale settings, and smoke
  outcomes.
- [ ] Confirm that no test preserves styling-only object names or widget-tree
  structure as product behavior.
- [ ] Obtain product-owner approval for the visual evidence.
- [ ] Confirm that functional and safety gates pass independently.
