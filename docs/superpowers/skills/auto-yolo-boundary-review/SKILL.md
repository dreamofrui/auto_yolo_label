---
name: auto-yolo-boundary-review
description: Use for AutoLabeler boundary, dependency, doc-consistency, and PR-readiness reviews, especially for temporary workers with a narrow read-only scope.
---

# AutoLabeler Boundary Review

Use this skill for read-only checks around architecture boundaries, dependency direction, legacy isolation, doc consistency, and PR readiness.

## First Message

Say:

```text
Using Skill: auto-yolo-boundary-review for boundary and standard checks.
```

Then confirm the scope, owned files, and whether the task is read-only.

## Read First

1. `AGENTS.md`
2. `CLAUDE.md`
3. `docs/dev/CURRENT_STATE.md`

## Core Rules

- Never modify `legacy/`.
- Never copy implementation bodies from `legacy/`.
- Do not touch files owned by another worker.
- Keep `core/` free of GUI / HTTP dependencies.
- Keep `utils/` from depending on `core/`.
- Keep `gui/workers/` thin.
- Use `MappingManager` for `mapping.json`.
- Use `TaskHandle` for long-running work.
- New business exceptions inherit `AutoLabelerError`.

## Review Flow

1. Confirm owned scope and exclusions.
2. Run the relevant checks for the files in scope.
3. Inspect imports, contracts, and boundary direction.
4. Check `docs/dev/CURRENT_STATE.md` and `CHANGELOG.md` for doc consistency.
5. Report findings with file:line references first.

## Assignment Format

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
- CLAUDE.md
- docs/dev/CURRENT_STATE.md
Tasks:
1. Run/check <commands>.
2. Inspect <specific boundary>.
3. Return findings with file:line references.
Deliverable:
- Findings ordered by severity.
- Checks run and exact result.
- Any uncertainty or owner decision needed.
```

## Stop Conditions

Stop and ask before changing scope, touching `legacy/`, introducing dependencies, or editing another worker's files.
