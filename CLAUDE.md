# CLAUDE.md

> Canonical agent rules are in `AGENTS.md`. Read that file first.
> This file documents only Claude-specific differences from the common rules.

## Trellis Disabled

Trellis is disabled for this repository by owner direction.

- Do not invoke any Trellis skill, command, agent, hook, or workflow unless the
  owner explicitly requests Trellis in the current message.
- Do not read `.trellis*`, `.agents/skills/trellis-*`,
  `.codex/agents/trellis-*`, or other Trellis-related files unless that same
  explicit request is present.
- This rule applies in every Claude/agent window even when the owner does not
  repeat the prohibition.

## Direction

- Desktop-first.
- GUI is the formal first-version product surface.
- Core logic stays stable and framework-free.
- `legacy/` is read-only.
