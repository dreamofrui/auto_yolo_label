# Utils Exceptions Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the new `utils/exceptions.py` foundation for typed business errors, shared error codes, and API/GUI-friendly `ErrorInfo`.

**Architecture:** `utils/exceptions.py` owns only shared exception infrastructure: `ErrorCode`, `ErrorInfo`, `AutoLabelerError`, and generic common exceptions. Module-specific exceptions remain in their future module files but must register codes in this enum. Tests validate behavior and reflection-friendly contracts.

**Tech Stack:** Python 3.11 dataclasses, `enum.Enum`, pytest, mypy strict-compatible type hints.

---

### Task 1: Create Exception Contract Tests

**Files:**
- Create: `tests/test_exceptions.py`
- Create: `utils/__init__.py`
- Create: `utils/exceptions.py`

- [ ] **Step 1: Write failing tests for base error behavior**

Create tests that import `AutoLabelerError`, `ErrorCode`, `ErrorInfo`, and generic subclasses. Cover message/details/retryable storage, string formatting, `to_error_info()`, and enum coverage for common + task + all module codes listed in `01-requirements.md`.

- [ ] **Step 2: Run tests to verify RED**

Run: `pytest tests/test_exceptions.py -v`
Expected: FAIL during import because `utils.exceptions` does not exist.

- [ ] **Step 3: Implement minimal exception infrastructure**

Create:
- `ErrorCode(str, Enum)` with common, task, and module-level codes from requirements.
- `ErrorInfo` dataclass with `code`, `message`, `details`, `retryable`.
- `AutoLabelerError` with class attributes `code = ErrorCode.INTERNAL_ERROR`, `retryable = False`, constructor, and `to_error_info()`.
- Common subclasses: `ValidationError`, `PathNotFoundError`, `PermissionDeniedError`, `InternalError`, `TaskNotFoundError`, `TaskAlreadyRunningError`, `TaskCancelledError`.

- [ ] **Step 4: Run tests to verify GREEN**

Run: `pytest tests/test_exceptions.py -v`
Expected: PASS.

### Task 2: Mechanical Discipline And Type Checks

**Files:**
- Modify: `utils/exceptions.py`
- Modify: `tests/test_exceptions.py`

- [ ] **Step 1: Run discipline checker**

Run: `python scripts/check_disciplines.py`
Expected: PASS with `utils/exceptions.py` checked.

- [ ] **Step 2: Run targeted mypy**

Run: `mypy --strict utils/`
Expected: PASS, unless mypy is not installed in the active environment. If unavailable, report the exact failure.

- [ ] **Step 3: Run targeted pytest**

Run: `pytest tests/test_exceptions.py -v`
Expected: PASS.

### Task 3: Documentation And Changelog

**Files:**
- Modify: `docs/dev/CURRENT_STATE.md`
- Modify: `CHANGELOG.md`

- [ ] **Step 1: Update progress docs**

Mark `utils/exceptions.py` as complete, add a completed entry, and set next in-progress module to `utils/logging_setup.py`.

- [ ] **Step 2: Update changelog**

Add an `[Unreleased]` entry under `Added` for the new exception infrastructure.

- [ ] **Step 3: Final verification**

Run:
- `python scripts/check_disciplines.py`
- `pytest tests/test_exceptions.py -v`
- `mypy --strict utils/`

Expected: all pass or exact unavailable-tool failure is documented.
