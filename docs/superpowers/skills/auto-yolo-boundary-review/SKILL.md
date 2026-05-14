---
name: auto-yolo-boundary-review
description: Use when assigning or performing AutoLabeler architecture boundary, enterprise coding standard, PR readiness, or discipline checks. Especially useful for temporary agents who need enough project context to review independently without touching overlapping files.
---

# AutoLabeler Boundary Review

Use this skill for read-only review work: architecture boundaries, enterprise coding standards, dependency direction, legacy isolation, API/core separation, documentation consistency, and PR readiness.

## First Message To The Owner

State:

```text
Using Skill: auto-yolo-boundary-review for boundary and standard checks.
```

Then confirm the review scope and whether the task is read-only. If the owner asks for fixes, ask which files you own before editing.

## Required Context

Read these files first:

1. `AGENTS.md`
2. `CLAUDE.md`
3. `docs/dev/CURRENT_STATE.md`
4. `docs/superpowers/specs/2026-05-13-auto-yolo-label-restructure/02-constraints.md`
5. `docs/superpowers/specs/2026-05-13-auto-yolo-label-restructure/01-requirements.md` only for modules in scope

Do not read `legacy/` unless the task explicitly asks for legacy comparison. If you do read it, keep it read-only and do not copy implementation bodies.

## Non-Negotiable Rules

- Never modify `legacy/`.
- Never copy-paste function bodies from `legacy/`.
- Do not stage or commit unrelated files.
- Do not edit files owned by another worker unless the project lead explicitly reassigns ownership.
- `core/` must not import GUI or HTTP frameworks.
- Inputs and outputs should be explicit dataclasses at module boundaries.
- Paths should use `pathlib.Path`.
- `mapping.json` access must go through `MappingManager`.
- New business exceptions must inherit `AutoLabelerError` and have an `ErrorCode`.
- API camelCase and Python snake_case conversion must be handled by pydantic schema aliases.
- Long-running work must use `TaskHandle`.

## Review Workflow

1. Capture state:
   - `git status --short --branch`
   - `git diff --name-only`
   - `git status --short -- legacy`
2. Identify owned scope:
   - files or modules assigned by the lead
   - files explicitly excluded from review
3. Run mechanical checks when available:
   - `python scripts/check_disciplines.py`
   - `ruff check core utils gui api tests scripts examples`
   - `mypy --strict core/ utils/` if reviewing core/utils contracts
   - targeted `pytest` for files in scope
4. Inspect dependency boundaries:
   - imports in `core/`
   - imports in `utils/`
   - route/service separation in `api/`
   - worker thinness in `gui/workers/`
5. Inspect contracts:
   - config/result dataclasses
   - public docstrings and type hints
   - error code mapping
   - cancellation and progress behavior
6. Inspect docs:
   - `docs/dev/CURRENT_STATE.md`
   - `CHANGELOG.md`
   - relevant requirement sections when behavior changed
7. Report findings before making fixes.

## Parallel Worker Protocol

When multiple workers share one repository, the lead must give each worker a disjoint write scope.

Use this assignment format:

```text
Role: Boundary reviewer for <module/group>
Mode: read-only unless explicitly approved
Owned files:
- <paths>
Do not edit:
- legacy/**
- files owned by other workers
Context to read:
- AGENTS.md
- docs/dev/CURRENT_STATE.md
- docs/.../02-constraints.md
Tasks:
1. Run/check <commands>.
2. Inspect <specific boundary>.
3. Return findings with file:line references.
Deliverable:
- Findings ordered by severity.
- Tests/checks run and exact result.
- Any uncertainty or owner decision needed.
```

## Finding Format

Lead with issues, not summaries:

```text
Severity: High|Medium|Low
File: path/to/file.py:123
Issue: What violates the contract or creates risk.
Why it matters: Concrete failure mode.
Recommendation: Minimal fix or owner decision.
Evidence: command output, import line, spec reference, or test gap.
```

If there are no findings:

```text
No issues found in <scope>.
Checks run:
- <command>: passed
Residual risk:
- <manual/untested area>
```

## When To Stop And Ask

Stop before changing anything if:

- the spec conflicts with implemented behavior
- a forced discipline appears impossible
- a new dependency is needed
- a fix requires touching another worker's files
- the review scope is ambiguous
- `legacy/` appears modified
