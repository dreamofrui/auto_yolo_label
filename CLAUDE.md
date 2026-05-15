# CLAUDE.md

> Read this before any task in the repo. It is the compact companion to `AGENTS.md`.

## Current Direction

- Desktop-first rewrite.
- Core stays stable and framework-free.
- CLI / JSON is the preview boundary for future Node.js child-process use.
- Web / FastAPI is not the mainline.
- `legacy/` is read-only.

## Hard Rules

- Do not edit `legacy/`.
- Do not copy implementation bodies from `legacy/`.
- Keep `core/` free of GUI / HTTP dependencies.
- Keep `utils/` from depending on `core/`.
- Keep `gui/workers/` thin.
- Use `MappingManager` for `mapping.json`.
- Use `TaskHandle` for long-running work.
- New business exceptions inherit `AutoLabelerError`.

## Working Notes

- Read `docs/dev/CURRENT_STATE.md` before changing behavior.
- Sync `docs/dev/CURRENT_STATE.md` and `CHANGELOG.md` when docs-facing state changes.
- Prefer small, explicit changes over broad process.
- State uncertainty early instead of guessing.

## Behavioral Guidelines

- Think before coding.
- Keep it simple.
- Make surgical changes.
- Define success in verifiable terms.
