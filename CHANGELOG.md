# Changelog

All notable changes to this repo are recorded here.

## [Unreleased]

### Changed
- (docs) Reduced the top-level operational docs to a compact desktop-first guide set.
- (docs) Removed stale stage/progress workflow text and old Web / FastAPI mainline phrasing.
- (docs) Reframed the current direction around desktop-first core stability, CLI / JSON preview boundaries, and read-only `legacy/`.
- (runtime) Moved shared service code from `api/services` to `runtime/services`.
- (gui) Updated desktop workers to call `runtime/services` instead of API-owned services.

### Added
- (cli) Added a minimal JSON scan adapter at `python -m cli.main scan <request.json>` for future Node.js subprocess integration.
- (cli) Added a matching JSON sample adapter at `python -m cli.main sample <request.json>`.
- (cli) Added a JSON train adapter for YOLO training requests.
- (cli) Added read-only JSON inspect adapters for listing inference runs, reading run trees, and reading product labels.
- (cli) Added JSON convert adapters for TXT-to-XML and XML-to-TXT annotation conversion.
- (cli) Added a JSON restore adapter for copying labels back to original product folders.
- (cli) Added a JSON LabelImg validate adapter while leaving GUI launch out of the CLI surface.

### Removed
- (web) Removed current-mainline API routes, schemas, HTTP examples, API reference docs, and API tests.
- (docs) Removed stale implementation plans, progress templates, and old web-centric restructuring specs from the active docs.
