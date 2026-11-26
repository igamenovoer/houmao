---
name: houmao-credential-mgr
description: Use when an admin needs to list, inspect, add, update, log in, rename, or remove Houmao credentials (`claude`, `codex`, `dsh`, `kimi`) for a project overlay or internal native-agent root.
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

# Houmao Credential Manager

## Overview

Manage Houmao provider credentials across project overlays (`houmao-mgr project [--project-dir <dir>] credentials <tool> ...`) and native-agent roots (`houmao-mgr internals native-agent credentials <tool> ... --native-agent-root <path>`) without exposing secrets or hand-editing auth directories.

## Workflow

1. **Answer explicit `help` first** from **Help** without probing files, listing credentials, or mutating storage.
2. **Enforce the Actor Frame Gate**: require `actor_kind=admin` and an explicit project or `--native-agent-root` target; reject `agent` frames.
3. **Check scope boundaries**: if the caller wants to repoint a profile or launch dossier `--auth` reference, or manage specialists, instances, or mailboxes, stop and route to `houmao-shared-routines->houmao-agent-definition`, `houmao-shared-routines->houmao-agent-instance`, or `houmao-shared-routines->houmao-mailbox-mgr`.
4. **Select one operation** from **Subcommands** (`list`, `get`, `add`, `set`, `login`, `rename`, or `remove`) and confirm the tool family:
   - Credential CRUD (`list`, `get`, `add`, `set`, `rename`, `remove`): `claude`, `codex`, `dsh`, or `kimi`.
   - Maintained login helper (`login`): `claude` or `codex` only. Route fresh default Kimi Code OAuth login requests to [references/kimi-code-login-handling.md](references/kimi-code-login-handling.md) ending in `kimi add|set --code-home`; `dsh` uses explicit API credentials (`--adapter deepseek|pi-ai`) via `add` or `set`.
5. **Resolve one `houmao-mgr` launcher** (`command -v houmao-mgr`, then `uv tool run --from houmao houmao-mgr`, or repo `pixi run houmao-mgr`, honoring an explicit user launcher) and ask for any missing required target, tool, name, or mutation input before running commands.
6. **Load the selected command page** (and matching tool reference in **References** when choosing credential flags), execute the command, and report redacted results without printing secret values.

If the request does not map cleanly to these steps, use the native planning tool to build a step-by-step plan from **Subcommands**, **References**, and the user request, then execute the plan.

## Actor Frame Gate

This parent-scoped routine is `admin`-only under `houmao-shared-routines`. Require `actor_kind=admin` and an explicit project or native-agent root; reject `agent` frames and never disclose secret values or raw auth files. Project-backed credential names are mutable catalog display names backed by opaque bundle directories, whereas direct native-agent `rename` (`tools/<tool>/auth/<name>/`) also rewrites maintained auth references in `presets/*.yaml` and `launch-profiles/*.yaml`.

## Subcommands

| Subcommand | Use For | Detail |
| --- | --- | --- |
| `list` | List credential names for `claude`, `codex`, `dsh`, or `kimi` in the selected lane. | [commands/list.md](commands/list.md) |
| `get` | Inspect one credential safely as structured redacted metadata. | [commands/get.md](commands/get.md) |
| `add` | Create one new `claude`, `codex`, `dsh`, or `kimi` credential from explicit inputs. | [commands/add.md](commands/add.md) |
| `set` | Patch or clear fields on one existing `claude`, `codex`, `dsh`, or `kimi` credential. | [commands/set.md](commands/set.md) |
| `login` | Run the maintained tmux-backed provider login helper for `claude` or `codex` (or route Kimi OAuth to `kimi-code-login-handling.md`). | [commands/login.md](commands/login.md) |
| `rename` | Rename one credential (`--name <old> --to <new>`) with lane-appropriate reference handling. | [commands/rename.md](commands/rename.md) |
| `remove` | Delete one existing credential through the maintained CLI. | [commands/remove.md](commands/remove.md) |
| `help` | Read-only overview of supported tools, dual lanes, login boundaries, and out-of-scope surfaces. | **Help** |

## References and Out-of-Scope Surfaces

- **Tool credential references**: [references/claude-credential-kinds.md](references/claude-credential-kinds.md), [references/codex-credential-kinds.md](references/codex-credential-kinds.md), [references/dsh-credential-kinds.md](references/dsh-credential-kinds.md), [references/kimi-credential-kinds.md](references/kimi-credential-kinds.md), and [references/kimi-code-login-handling.md](references/kimi-code-login-handling.md).
- **Explicitly out of scope**: `project specialist create|list|get|remove`, `project profile ...`, `project agents launch|list|get|stop`, `agents global|single|self|external ...`, `internals native-agent tools <tool> setups ...`, `internals native-agent roles|launch-dossiers ...`, `project mailbox ...` / `mailbox cleanup ...` / `agents single ... cleanup ...` / `admin cleanup runtime ...`, and direct hand-editing under `.houmao/content/auth/`, `.houmao/agents/tools/`, or `tools/<tool>/auth/`.

## Help

Summarize CRUD support for `claude`, `codex`, `dsh`, and `kimi` across `project credentials` and `internals native-agent credentials`, maintained `login` helpers for `claude` and `codex`, the Kimi `--code-home` OAuth workflow, DSH `--adapter [deepseek|pi-ai]` explicit API credentials, and safe redacted `get` inspection. Concrete credential requests execute the matching subcommand.

## Guardrails

- DO NOT print raw API keys, tokens, proxy credentials, `vars.env` values, or auth JSON/TOML secrets when inspecting or updating credentials.
- DO NOT scan ambient env vars, home directories, or vendor tool homes to synthesize missing credential inputs unasked.
- DO NOT invent `credentials kimi login` or `credentials dsh login` commands, or hand-roll temp homes for `claude`/`codex` when `credentials <login-tool> login` owns that flow.
- DO NOT hand-edit `.houmao/content/auth/`, `.houmao/agents/tools/`, or `tools/<tool>/auth/`, or treat profile/dossier `--auth` overrides as credential CRUD.
- DO NOT conflate project-backed metadata-only `rename` with direct-dir `rename` (which rewrites `presets/*.yaml` and `launch-profiles/*.yaml`).
