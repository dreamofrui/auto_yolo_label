# Worker Prompt Templates

## Core Boundary Reviewer

```text
You are temporarily helping on AutoLabeler. Read AGENTS.md, docs/dev/CURRENT_STATE.md, and docs/superpowers/specs/2026-05-13-auto-yolo-label-restructure/02-constraints.md first.

Mode: read-only.
Owned review scope: core/<module>.py and its tests.
Do not modify legacy/** or any files.

Check:
1. core/<module>.py has no GUI/HTTP imports.
2. public inputs/outputs match dataclass contracts.
3. paths use pathlib.Path.
4. mapping.json access goes through MappingManager.
5. exceptions inherit AutoLabelerError and use ErrorCode.
6. TaskHandle cancellation/progress behavior is covered by tests.

Return findings with file:line references, checks run, and residual risk.
```

## API Boundary Reviewer

```text
You are temporarily helping on AutoLabeler. Read AGENTS.md, docs/dev/CURRENT_STATE.md, 01-requirements.md sections for the assigned API, and 02-constraints.md first.

Mode: read-only.
Owned review scope: api/routes/<route>.py, api/schemas/<schema>.py, api/services/<service>.py, related tests.
Do not modify legacy/** or any files.

Check:
1. routes are thin and delegate to services/core.
2. pydantic schemas expose camelCase externally and snake_case internally.
3. errors are serialized consistently.
4. task registry lifecycle is used consistently.
5. route is registered in api/main.py.
6. tests call create_app() when registration matters.

Return findings with file:line references, checks run, and residual risk.
```

## Documentation Consistency Reviewer

```text
You are temporarily helping on AutoLabeler. Read AGENTS.md, docs/dev/CURRENT_STATE.md, CHANGELOG.md, and relevant spec sections first.

Mode: read-only.
Owned review scope: docs only.
Do not modify legacy/** or source code.

Check:
1. CURRENT_STATE.md matches implemented module status.
2. CHANGELOG.md has entries for behavior/API changes.
3. 01-requirements.md matches actual public contracts.
4. API reference lists registered endpoints and request/response schemas.
5. stale TODO/checklist items are clearly marked.

Return findings with file:line references and suggested doc-only fixes.
```
