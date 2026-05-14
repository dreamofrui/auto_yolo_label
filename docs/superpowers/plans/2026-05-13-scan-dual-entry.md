# Scan Dual Entry Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Provide the first M1.3 desktop + HTTP dual-call entry for `Scanner.scan`.

**Architecture:** A shared scan service owns TaskRegistry lifecycle and calls `Scanner.scan`. The desktop worker and HTTP route are thin adapters over that service. API schemas use pydantic v2 camelCase aliases; examples demonstrate scan via the desktop worker and scan via FastAPI TestClient without duplicating business logic.

**Tech Stack:** Python 3.11, FastAPI, pydantic v2, PySide6-free testable worker class, pathlib, TaskRegistry, Scanner.

---

### Task 1: Scan Entry Tests

**Files:**
- Create: `tests/api/test_scan_route.py`
- Create: `tests/test_scan_worker.py`
- Create: `api/`
- Create: `gui/workers/`

- [ ] Write tests for camelCase API request/response, AutoLabelerError response handling, and TaskHandle success state.
- [ ] Write tests for desktop worker invoking Scanner through the same service and reporting a task handle.
- [ ] Run RED; expected failure is missing `api.main` / `gui.workers.scan_worker`.

### Task 2: Shared Service And Adapters

**Files:**
- Create: `api/schemas/base.py`
- Create: `api/schemas/scan.py`
- Create: `api/services/scan_service.py`
- Create: `api/routes/scan.py`
- Create: `api/main.py`
- Create: `gui/workers/scan_worker.py`

- [ ] Implement pydantic camelCase base schema.
- [ ] Implement `run_scan(config, registry)` service with TaskRegistry lifecycle.
- [ ] Implement FastAPI app and `/api/scan` route.
- [ ] Implement desktop `ScanWorker.run()` as a thin adapter over the same service.

### Task 3: Examples, Docs, Verification

**Files:**
- Create: `examples/scan_via_desktop.py`
- Create: `examples/scan_via_http.py`
- Modify: `docs/dev/CURRENT_STATE.md`
- Modify: `CHANGELOG.md`

- [ ] Add examples using generated temporary site folders.
- [ ] Run target tests, full tests, mypy, and discipline checks.
- [ ] Commit with `feat(entry): add scan desktop and http adapters`.
