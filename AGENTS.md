# AGENTS.md

> Start here for any work in this repo. Read this file, then
> `docs/dev/ONBOARDING_SUMMARY.md`, `docs/dev/PRODUCT_SPEC.md`, and
> `docs/dev/UI_SPEC.md`.

## Direction

- Desktop-first.
- GUI is the formal first-version product surface.
- Core logic stays stable and framework-free.
- `runtime/` and `cli/` are deleted; do not reintroduce them as active
  architecture surfaces.
- Web, FastAPI, browser UI, and Node subprocess integration are not current
  goals.
- `legacy/` is read-only.

## Required Docs

- `docs/dev/ONBOARDING_SUMMARY.md` is the handoff guide for current
  architecture, module ownership, and maintenance risks.
- `docs/dev/PRODUCT_SPEC.md` is the product behavior baseline.
- `docs/dev/UI_SPEC.md` is the GUI behavior and layout baseline.
- `README.md` is the compact project entry point.
- `CHANGELOG.md` records notable product, architecture, test, and doc changes.

## Work Rules

1. Confirm the task scope and owned files first.
2. Touch only files the task needs.
3. Do not edit `legacy/` or copy implementation bodies from it.
4. Do not add dependencies unless the owner explicitly approves.
5. Keep changes surgical; remove stale text instead of layering on process.
6. For bug fixes, first narrow the root cause to the specific function(s) and
   call path being corrected. Do not patch around symptoms or make speculative
   broad changes when the failing function has not been proven.
7. For small, single-function fixes, use a lightweight flow: state the root
   cause function, make the minimal direct change, then run scoped tests.
8. Update `CHANGELOG.md` for notable retained-doc, product, architecture, or
   test changes.
9. Update `PRODUCT_SPEC.md` only when product behavior changes.
10. Update `UI_SPEC.md` only when GUI behavior, layout, or verification rules
   change.

## Changelog Rules

- Record changes that affect maintenance, usage, testing, deployment, or
  handoff: product behavior, GUI workflows, architecture boundaries, server
  scripts, retained docs, tests, removals, and notable safety fixes.
- Do not record routine internal cleanup, typo fixes, temporary screenshots,
  cache/output changes, local-only test artifacts, or small visual spacing
  tweaks unless they change a documented behavior or reduce a known risk.
- Keep entries concise and group them by impact area when possible: Product /
  GUI, Architecture, Server Scripts, Documentation, Tests, and Removed.

## Architecture Constraints

- `core/` is business logic only and must not import GUI or HTTP frameworks.
- `utils/` is infrastructure only and must not depend on `core/`.
- `gui/workers/` stays thin and desktop-adapter only; it calls `core/`
  directly and owns desktop task lifecycle glue.
- Use `pathlib.Path` for paths.
- Keep module boundaries explicit with dataclasses and typed results.
- Use `MappingManager` for `mapping.json`.
- Long-running work uses `TaskHandle`.
- New business exceptions inherit `AutoLabelerError` and carry an error code.
- Do not introduce new HTTP routes, schemas, CLI JSON contracts, or Node-facing
  behavior by default.

## Commands

- Use `D:/miniforge3/envs/yolo_new/python.exe` for project commands, tests, and
  scripts.
- Keep verification scoped to changed behavior.
- Do not claim full product coverage unless the relevant feature tests or real
  smoke checks were actually run.
- `tests/A9950/` is reserved future real test data. Do not modify, stage, or
  depend on it unless explicitly approved.
- If real data is needed repeatedly, copy it into a temporary workspace inside
  the repo or `D:/tmp`, run the test, then clean up the copy.

## UI Work

- Before designing or changing GUI/UI, use `impeccable` for product UI critique
  and `frontend-ui-engineering` for implementation-quality structure.
- Every opened or modified GUI page must be reviewed against those UI skills
  before the work is considered complete. Prefer deterministic detectors,
  subagent review, and real screenshots when applicable.
- Preserve each tool's business inputs, outputs, result summaries, errors, and
  destructive-action confirmations from `PRODUCT_SPEC.md`.
- Keep the visual direction light main workspace, dark side navigation,
  restrained brand accent, and no decorative AI-looking gradients or card spam.
- Use `gui/path_picker.py` for path-like inputs that need browse/paste support;
  keep numeric and strategy controls as plain widgets.

## Subagents

- Subagents are allowed proactively for bounded read-only review, verification,
  UI critique, boundary checks, or disjoint implementation slices.
- Give each subagent a self-contained prompt with scope, exclusions, expected
  output, and verification command.
- For implementation work, assign disjoint file ownership. Workers must not
  revert edits made by others.
- Keep concurrency conservative; this repo's owner-approved upper limit is six
  concurrent subagents.
- The lead agent remains responsible for integration, conflict resolution,
  final verification, and the final answer.

<!-- gitnexus:start -->
# GitNexus — Code Intelligence

This project is indexed by GitNexus as **auto_yolo_label** (3081 symbols, 6339 relationships, 262 execution flows). Use the GitNexus MCP tools to understand code, assess impact, and navigate safely.

> Index stale? Run `node .gitnexus/run.cjs analyze` from the project root — it auto-selects an available runner. No `.gitnexus/run.cjs` yet? `npx gitnexus analyze` (npm 11 crash → `npm i -g gitnexus`; #1939).

## Always Do

- **MUST run impact analysis before editing any symbol.** Before modifying a function, class, or method, run `impact({target: "symbolName", direction: "upstream"})` and report the blast radius (direct callers, affected processes, risk level) to the user.
- **MUST run `detect_changes()` before committing** to verify your changes only affect expected symbols and execution flows. For regression review, compare against the default branch: `detect_changes({scope: "compare", base_ref: "main"})`.
- **MUST warn the user** if impact analysis returns HIGH or CRITICAL risk before proceeding with edits.
- When exploring unfamiliar code, use `query({search_query: "concept"})` to find execution flows instead of grepping. It returns process-grouped results ranked by relevance.
- When you need full context on a specific symbol — callers, callees, which execution flows it participates in — use `context({name: "symbolName"})`.
- For security review, `explain({target: "fileOrSymbol"})` lists taint findings (source→sink flows; needs `analyze --pdg`).

## Never Do

- NEVER edit a function, class, or method without first running `impact` on it.
- NEVER ignore HIGH or CRITICAL risk warnings from impact analysis.
- NEVER rename symbols with find-and-replace — use `rename` which understands the call graph.
- NEVER commit changes without running `detect_changes()` to check affected scope.

## Resources

| Resource | Use for |
|----------|---------|
| `gitnexus://repo/auto_yolo_label/context` | Codebase overview, check index freshness |
| `gitnexus://repo/auto_yolo_label/clusters` | All functional areas |
| `gitnexus://repo/auto_yolo_label/processes` | All execution flows |
| `gitnexus://repo/auto_yolo_label/process/{name}` | Step-by-step execution trace |

## CLI

| Task | Read this skill file |
|------|---------------------|
| Understand architecture / "How does X work?" | `.claude/skills/gitnexus/gitnexus-exploring/SKILL.md` |
| Blast radius / "What breaks if I change X?" | `.claude/skills/gitnexus/gitnexus-impact-analysis/SKILL.md` |
| Trace bugs / "Why is X failing?" | `.claude/skills/gitnexus/gitnexus-debugging/SKILL.md` |
| Rename / extract / split / refactor | `.claude/skills/gitnexus/gitnexus-refactoring/SKILL.md` |
| Tools, resources, schema reference | `.claude/skills/gitnexus/gitnexus-guide/SKILL.md` |
| Index, status, clean, wiki CLI commands | `.claude/skills/gitnexus/gitnexus-cli/SKILL.md` |

<!-- gitnexus:end -->
