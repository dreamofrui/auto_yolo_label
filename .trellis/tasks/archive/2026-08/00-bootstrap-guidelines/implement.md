# Implementation Plan: AutoLabeler Trellis Spec Refresh

1. Inspect the current task, spec tree, retained docs, source boundaries, and
   focused tests; re-index GitNexus before relying on graph results.
2. Replace the root spec index and add accurate `core`, `gui`, `workers`,
   `utils`, and `server_scripts` indexes plus topic guides.
3. Rewrite the two thinking guides with Python and AutoLabeler examples.
4. Search the final tree for stale backend/frontend wording, generic template
   placeholders, broken links, and references to deleted architecture.
5. Run `scripts/check_disciplines.py`, the import/contract tests, and the
   documentation consistency checks. Do not run tests that depend on
   `tests/A9950/`.
6. Run GitNexus `detect_changes` for the final worktree and confirm that only
   documentation/task files are in this task's scope.
7. Update `CHANGELOG.md`, finish the task, and archive it only after the
   quality gate passes.

## Validation Commands

```powershell
D:/miniforge3/envs/yolo_new/python.exe scripts/check_disciplines.py
D:/miniforge3/envs/yolo_new/python.exe -m pytest tests/test_imports.py tests/test_contracts.py -q
rg -n "backend|frontend|To be filled|TODO: fill|placeholder|FastAPI|runtime/services|active cli" .trellis/spec
```

The final command is expected to return no matches. Link validation is done by
checking every Markdown link target from the spec indexes against the tree.
