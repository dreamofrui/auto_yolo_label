# AutoLabeler

AutoLabeler is a desktop-first YOLO semi-automatic image labeling workbench.
It helps an operator scan a strict product image tree, sample images for manual
labeling, train a YOLO model, infer remaining images, review predictions with
LabelImg, and restore reviewed labels as VOC XML beside the original images.

The formal product surface is the PySide6 GUI. `core/` contains framework-free
business logic, and `gui/workers/` adapts GUI actions directly to `core/` while
recording task state through `TaskRegistry`.

## Workflow

```text
scan -> sample -> label with LabelImg -> train -> infer
-> review with LabelImg -> restore XML labels
```

Independent tools are also available from the GUI when the selected operation
can run from explicit paths without `mapping.json`.

## Run

Use the project Python environment for local commands:

```powershell
D:/miniforge3/envs/yolo_new/python.exe -m gui.app
```

Run scoped tests with the same interpreter:

```powershell
D:/miniforge3/envs/yolo_new/python.exe -m pytest tests/test_imports.py -q
```

## Project Docs

- `AGENTS.md`: repository working rules for contributors and coding agents.
- `docs/dev/ONBOARDING_SUMMARY.md`: handoff guide for current architecture,
  module ownership, and maintenance risks.
- `docs/dev/PRODUCT_SPEC.md`: product behavior and module contract baseline.
- `docs/dev/UI_SPEC.md`: desktop GUI structure and interaction baseline.
- `docs/dev/UI_REGRESSION_BOUNDARY.md`: behavior and verification gates for
  staged GUI redesign work.
- `CHANGELOG.md`: notable product, architecture, and test changes.

`runtime/` and `cli/` are not part of the active architecture. Web, FastAPI,
Node subprocess integration, and browser UI are not current goals.
