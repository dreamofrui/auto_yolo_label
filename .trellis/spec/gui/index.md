# GUI Layer

`gui/` is the PySide6 desktop shell and presentation layer. Pages collect user
input into typed core configs, call workers through a `TaskRunner`, and render
typed outcomes. They do not own mapping mutation, annotation parsing, model
execution, or filesystem policy.

## Read Before Editing

1. [Shell and page patterns](./shell-and-pages.md)
2. [Task feedback and high-risk actions](./task-feedback.md)
3. [UI verification](./ui-verification.md)
4. `docs/dev/UI_SPEC.md` for layout and interaction behavior

## Quality Check

- Use `PathPicker` for path-like fields and ordinary Qt widgets for numeric,
  strategy, mode, and confirmation controls.
- Keep long paths wrapped or compacted with a tooltip/details path; do not let
  them widen the page.
- Test page construction and important workflows with `QT_QPA_PLATFORM=offscreen`
  in `tests/test_gui_shell.py`.
- Use `ImmediateTaskRunner` in focused widget tests and
  `AsyncTaskRunner` only for production background execution.
- Preserve Flow/Independent visibility and preflight/confirmation behavior
  from `docs/dev/UI_SPEC.md`.
