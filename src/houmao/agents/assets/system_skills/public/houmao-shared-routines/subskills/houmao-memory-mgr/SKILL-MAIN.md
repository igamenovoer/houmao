---
name: houmao-memory-mgr
description: "Use when reading, writing, appending, or clearing a Houmao-managed agent's live houmao-memo.md or pages/ entries, or configuring a project profile or launch dossier memo seed when memo is explicitly referenced."
license: MIT
metadata:
  skill_invocation_notation: >
    Top-level skill entrypoints use SKILL.md. Parent-scoped subskill entrypoints use
    SKILL-MAIN.md and are loaded explicitly through their parent; nested SKILL.md is
    accepted only as legacy input when SKILL-MAIN.md is absent.
    Skill and subskill entrypoints use bare object paths: `X` invokes skill X and
    `X->Y->Z` invokes subskill Z. Subcommands use parenthesized components:
    `X->cmd()` invokes a direct subcommand, `X->Y->cmd()` invokes a subcommand of
    subskill Y, and `X->parent()->child()` invokes child subcommand child exposed
    by parent subcommand parent. Intermediate subcommands act as object generators.
    Forms such as `X()` and `X->Y()` are invalid for skill or subskill entrypoints.
---

# Houmao Memory Manager

## Overview

Manage live Houmao-managed agent memory (`houmao-memo.md` and `pages/`) under `MANAGED_PROMPT_HEADER_VERSION = 2` `<memo_cue>` discipline, or configure birth-time memo seeds on reusable project profiles and launch dossiers.

## Workflow

1. **Answer explicit `help` first** from **Help** without running commands or mutating live or profile state.
2. **Enforce the Actor Frame Gate and Trigger Rule**: verify the inherited `admin` or `agent` frame and confirm the necessary trigger (`memo` mentioned) plus a sufficient trigger (`houmao memo`, `houmao-memo.md`, managed `agent memo`, or a profile/launch-dossier memo seed).
3. **Separate target kinds up front**:
   - Birth-time reusable profile (`project profile` or `launch-dossiers` / future launches): never touch any live agent's `houmao-memo.md`.
   - Live managed-agent memory: default to verified self (`HOUMAO_AGENT_MEMO_FILE` / `HOUMAO_AGENT_PAGES_DIR` or `agents self memory`) in `agent` posture; require explicit `--agent-id` or `--agent-name` in `admin` or peer posture.
4. **Select one subcommand** from **Subcommands** (`read`, `write`, or `remove`), resolve one `houmao-mgr` launcher (`command -v houmao-mgr`, then `uv tool run --from houmao houmao-mgr`, or repo `pixi run houmao-mgr`), and execute its page workflow.
5. **Confirm compact write receipts** (`success`, `action`, `memo_file`) on live mutations and run `memory memo show` when the resulting memo text is needed.

If the request does not map cleanly to these steps, use the native planning tool to build a step-by-step plan from **Subcommands**, **Prompt Header v2 `<memo_cue>` Contract**, and the user request, then execute the plan.

## Actor Frame Gate

This parent-scoped routine loads only through `houmao-shared-routines` and requires an immutable `admin` or verified `agent` frame; missing or mismatched frames fail closed. Admin callers require an explicit agent or profile target and never treat the operator shell as self; agent callers default live memory to verified self and require an explicit target for peers or profiles. Route non-memory profile authoring to `houmao-shared-routines->houmao-agent-definition`, runtime/log/mailbox inspection to `houmao-shared-routines->houmao-agent-inspect`, and gateway reminders to `houmao-shared-routines->houmao-agent-gateway`.

## Subcommands

| Subcommand | Use For | Detail |
| --- | --- | --- |
| `read` | Resolve live memory paths, show `houmao-memo.md`, list/read `pages/`, or inspect a profile/launch-dossier memo seed. | [commands/read.md](commands/read.md) |
| `write` | Append or set live `houmao-memo.md` (with compact receipts), write/append `pages/`, or set a birth-time memo seed. | [commands/write.md](commands/write.md) |
| `remove` | Delete a contained `pages/` entry, prune live memo text via smallest-edit `memo set`, or `--clear-memo-seed` on a profile. | [commands/remove.md](commands/remove.md) |
| `help` | Read-only summary of `<memo_cue>` discipline, live vs birth-time seed boundaries, and supported operations. | **Help** |

## Prompt Header v2 `<memo_cue>` Contract and Help

Under `MANAGED_PROMPT_HEADER_VERSION = 2`, `<memo_cue>` instructs managed agents to read `houmao-memo.md` every turn before planning or acting, open linked `pages/` notes when relevant, apply rules directly without merely announcing that the memo was read, keep `houmao-memo.md` brief (current facts, standing rules, `[label](pages/...)` links), and update it sparingly (only when asked or clearly outdated). Birth-time seeds (`--memo-seed-text`, `--memo-seed-file`, `--memo-seed-dir`, `--clear-memo-seed`) configure future launches only (`--memo-seed-text ''` sets an intentional empty seed) and are never passed to `internals config-drafts generate`. Explicit `help` explains these boundaries read-only; concrete memo requests execute `read`, `write`, or `remove`.

## Guardrails

- DO NOT run live `agents self|single ... memory` commands when the target is a reusable project profile or launch dossier, or pass memo seeds to `internals config-drafts generate`.
- DO NOT use absolute paths or `..` in `--path`; all page operations stay strictly inside `pages/`, and no arbitrary files may be written beside `houmao-memo.md` at the memory root.
- DO NOT auto-generate, sort, or rewrite page indexes inside `houmao-memo.md` unless the user explicitly asks for that edit.
- DO NOT pass arbitrary directories to `--memo-seed-dir` (only `houmao-memo.md` and `pages/` entries are allowed) or hand-edit `.houmao/agents/launch-profiles/<name>.yaml`.
- DO NOT store runtime bookkeeping, retry counters, mailbox receipts, gateway state, or provider-native memory inside Houmao memory.
