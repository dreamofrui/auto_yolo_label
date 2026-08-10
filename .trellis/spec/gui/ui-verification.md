# GUI Verification

The behavior baseline is `docs/dev/UI_SPEC.md`; this file records the local
verification seam rather than replacing that product contract.

## Focused Tests

`tests/test_gui_shell.py` constructs the login, homepage, navigation, task
center, module pages, preflight panels, and result surfaces with
`QT_QPA_PLATFORM=offscreen`. Add assertions there for new visible states,
small-window sizing, action reachability, and Flow/Independent labels.

Use the page-specific worker fakes already used by the test suite. Avoid
launching LabelImg, training a real model, or depending on live CUDA in widget
tests.

## Snapshot And Smoke Checks

Use `scripts/ui_snapshot.py` for a repeatable offscreen screenshot/smoke pass
when a GUI change affects layout. Verify that long Windows paths wrap or are
compacted, the main action remains reachable in a small desktop window, and
the right support rail does not become a third persistent column.

## Visual Constraints

Keep the restrained light-workspace/dark-navigation palette, fixed typography,
and familiar controls from `docs/dev/UI_SPEC.md`. Do not add decorative
gradients, oversized marketing sections, invented task tabs, or AI execution
claims. AI surfaces remain preview-only until a product contract says
otherwise.
