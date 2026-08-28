# AGENTS.md

> Start here for any work in this repo. Read this file, then
> `docs/dev/ONBOARDING_SUMMARY.md`, `docs/dev/PRODUCT_SPEC.md`, and
> `docs/dev/UI_SPEC.md`.

## Trellis Disabled

Trellis is disabled for this repository by owner direction.

- Do not invoke any Trellis skill, command, agent, hook, or workflow unless the
  owner explicitly requests Trellis in the current message.
- Do not read `.trellis*`, `.agents/skills/trellis-*`,
  `.codex/agents/trellis-*`, or other Trellis-related files unless that same
  explicit request is present.
- This rule applies in every agent window even when the owner does not repeat
  the prohibition.

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

## Skill Invocation Rule

When the user types `/skill-name` in their message, immediately invoke it with the `Skill` tool. No exceptions.

- User's explicit `/skill-name` = absolute command to invoke
- Ignore any skill metadata (`disable-model-invocation`, etc.) - those are internal constraints, not invocation blockers
- If `Skill` tool errors, report the error; do not manually execute the skill's instructions
- Do not analyze whether you "should" invoke it - just invoke it

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

## Filesystem Safety

- Move, delete, overwrite, restore, and clear actions require preflight before
  execution; destructive or high-risk actions require inline confirmation.
- If real data is needed repeatedly, copy it into a temporary workspace inside
  the repo or `D:/tmp`, run the test, then clean up the copy.

## Commands

- Use `D:/miniforge3/envs/yolo_new/python.exe` for project commands, tests, and
  scripts.
- Keep verification scoped to changed behavior.
- Do not claim full product coverage unless the relevant feature tests or real
  smoke checks were actually run.
- `tests/A9950/` is reserved future real test data. Do not modify, stage, or
  depend on it unless explicitly approved.


## Agent skills

### Issue tracker

Issues and PRDs are tracked in GitHub Issues for
`dreamofrui/auto_yolo_label` using the `gh` CLI. See
`docs/agents/issue-tracker.md`.

### Triage labels

The repo uses the five canonical triage labels without overrides. See
`docs/agents/triage-labels.md`.

### Domain docs

This is a single-context repo with optional root `CONTEXT.md` and
`docs/adr/`. See `docs/agents/domain.md`.

<!-- gitnexus:start -->
# GitNexus — Code Intelligence

This project is indexed by GitNexus as **auto_yolo_label** (4551 symbols, 8048 relationships, 290 execution flows). Use the GitNexus MCP tools to understand code, assess impact, and navigate safely.

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
