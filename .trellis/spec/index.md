# AutoLabeler Development Specs

These are project-specific coding rules for the desktop-first AutoLabeler
application. Read the layer index before editing code and use the cross-layer
guides when a change crosses an ownership boundary.

## Architecture

```text
PySide6 shell/pages -> gui/workers -> core workflows -> local files
                                      |
                                      +-> utils contracts
```

`server_scripts/` is a separate offline operational surface. It is not a
desktop worker and is not imported by the GUI.

## Layer Index

| Layer | Owns | Start here |
| --- | --- | --- |
| Core | Framework-free business workflows and annotation contracts | [Core](./core/index.md) |
| GUI | PySide6 shell, pages, shared controls, and display state | [GUI](./gui/index.md) |
| Workers | Thin desktop task adapters under `gui/workers/` | [Workers](./workers/index.md) |
| Utils | Mapping, tasks, errors, paths, devices, and logging | [Utils](./utils/index.md) |
| Server scripts | Standalone Linux/Docker train and predict commands | [Server scripts](./server_scripts/index.md) |

## Cross-Layer Guides

- [Cross-layer data flow](./guides/cross-layer-thinking-guide.md)
- [Code reuse](./guides/code-reuse-thinking-guide.md)

## Baseline Documents

When behavior or layout is involved, read `AGENTS.md`,
`docs/dev/ONBOARDING_SUMMARY.md`, `docs/dev/PRODUCT_SPEC.md`, and
`docs/dev/UI_SPEC.md` before using these coding specs.

## Repository Rules

- Keep `core/` free of GUI and HTTP framework imports.
- Keep worker modules thin and call core directly.
- Use `pathlib.Path` for filesystem paths.
- Route `mapping.json` through `MappingManager`.
- Use `TaskHandle` for long-running work and `AutoLabelerError` for business
  failures with stable error codes.
- Do not edit or copy implementation bodies from `legacy/`.
