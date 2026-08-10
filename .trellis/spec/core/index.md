# Core Layer

`core/` contains framework-free business logic. It may use standard library,
Pillow, Ultralytics adapters, and contracts from `utils/`, but it must not
import Qt, HTTP, or other presentation frameworks.

## Read Before Editing

1. [Public contracts and dependencies](./contracts.md)
2. [Workflow module map](./workflow-modules.md)
3. [Annotation formats](./annotation-contracts.md) for YOLO/VOC work
4. [Filesystem safety and preflight](./filesystem-safety.md) for writes,
   moves, deletes, overwrite, or restore
5. `docs/dev/PRODUCT_SPEC.md` when product behavior is involved

## Quality Check

- Add or update the focused module test under `tests/test_<module>.py`.
- Run `tests/test_imports.py` and `tests/test_contracts.py` for boundary or
  public-entrypoint changes.
- Run `scripts/check_disciplines.py` for import, path, mapping, exception, and
  public-docstring rules.
- Inject a `TaskHandle` in tests when cancellation or progress is part of the
  behavior; avoid real model training or reserved `tests/A9950/` data.
