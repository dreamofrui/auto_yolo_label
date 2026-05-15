# AutoLabeler Current State

> Last updated: 2026-05-15
> Branch: `refactor/scaffold-v2`

## Status

AutoLabeler is being rewritten as desktop-first. The stable core is the priority, with a shared runtime/service layer in support of desktop use. CLI / JSON is the preview boundary for future Node.js child-process integration. Web / FastAPI has been removed from the current mainline.

## Current Direction

- Keep `core/` focused on business logic.
- Keep `utils/` as shared infrastructure.
- Keep `gui/workers/` thin desktop adapters.
- Put shared runtime/service code in `runtime/`.
- Use `cli/` only for thin JSON adapters over `runtime/services`.
- Treat `legacy/` as read-only reference material.

## Doc Sync

When behavior or scope changes, update:

- `docs/dev/CURRENT_STATE.md`
- `CHANGELOG.md`

## Notes

- Old API routes, schemas, HTTP examples, and web-specific specs were removed from the active tree.
- `python -m cli.main scan <request.json>` and `python -m cli.main sample <request.json>` are the first working JSON boundaries for future Node.js subprocess calls.
- YOLO training is exposed through `python -m cli.main train <request.json>`.
- YOLO inference is exposed through `python -m cli.main infer <request.json>`.
- Annotation conversion is exposed through `python -m cli.main convert txt-to-xml|xml-to-txt <request.json>`.
- Label restoration is exposed through `python -m cli.main restore <request.json>`.
- LabelImg environment validation is exposed through `python -m cli.main labelimg validate <request.json>`; launching remains desktop-owned for now.
- Read-only inspection is exposed through `python -m cli.main inspect list-runs|run-tree|product-labels <request.json>`.
- Other CLI commands should follow the same thin-adapter pattern only when needed.
