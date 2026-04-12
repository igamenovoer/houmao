## Context

Three doc entry points are stale after `specialist set` and Codex CLI config overrides landed. The detailed docs (easy-specialists.md, houmao-mgr.md) are already current. These are small, mechanical fixes to high-visibility tables.

## Goals / Non-Goals

**Goals:**

- Add "set" verb to two `houmao-specialist-mgr` skill table cells (README and system-skills-overview).
- Add `codex.append_unattended_cli_overrides` row to the launch-policy Codex hooks table.

**Non-Goals:**

- Adding any new sections or expanding existing prose.
- Updating the deprecated Codex troubleshooting page.
- Documenting the full Codex CLI config override implementation (that's internal build-phase machinery, not user-facing).

## Decisions

**Decision 1: Minimal verb insertion, no restructuring.**
Both skill tables already have the right structure. We add "set" to the verb list in the natural position (after "Create") and leave everything else untouched.

**Decision 2: Hook table row describes the user-visible effect.**
The new hook row describes what `codex.append_unattended_cli_overrides` does from the operator's perspective (prevents project-local config from overriding unattended posture) rather than implementation details (TOML dotted-key `-c` args).

## Risks / Trade-offs

- [Minimal] These are one-word and one-row additions. No meaningful risk.
