# GUI Workers Layer

The worker layer is the desktop adapter under `gui/workers/`. It owns task
registration, cancellation/progress plumbing, and conversion of core outcomes
and business exceptions into GUI-friendly dataclasses. It does not own product
policy.

## Read Before Editing

- [Adapters and lifecycle](./adapters-and-lifecycle.md)
- `docs/dev/ONBOARDING_SUMMARY.md` module maintenance map
- the matching core spec and worker test for the operation being changed

## Quality Check

- Confirm the worker imports the core service directly and does not import a
  deleted runtime service layer.
- Keep outcome dataclasses typed and immutable where possible.
- Add success and business-error assertions to the focused worker test.
- Exercise cancellation through `tests/test_service_cancellation.py` when the
  worker or core loop owns a long-running task.
