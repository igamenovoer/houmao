# system-skills

`houmao-mgr system-skills` is the operator-facing surface for installing the current Houmao-owned `houmao-*` skills into explicit Claude, Codex, or Gemini homes.

This is the same packaged skill system used internally by:

- `houmao-mgr brains build` when it creates a managed home,
- `houmao-mgr agents join` when it adopts an existing session and auto-installs Houmao-owned skills into the adopted tool home.

The current implementation is intentionally narrow. It covers the existing mailbox-oriented Houmao-owned skills only. It does not yet generalize to other asset kinds or future skill families.

## Command Shape

```text
houmao-mgr system-skills
├── list
├── status --tool <tool> --home <path>
└── install --tool <tool> --home <path> [--default] [--set <name> ...] [--skill <name> ...]
```

## Packaged Catalog

The authoritative packaged catalog lives in the runtime package:

- `src/houmao/agents/assets/system_skills/catalog.toml`
- `src/houmao/agents/assets/system_skills/catalog.schema.json`

The catalog defines three things:

1. `skills`: the current installable Houmao-owned skills
2. `sets`: named sets of explicit skill names
3. `auto_install`: fixed set lists used for managed launch, managed join, and CLI default installation

The catalog is loaded by `src/houmao/agents/system_skills.py`, normalized, validated against the packaged JSON Schema, and then checked for cross-reference errors such as sets that mention unknown skills.

Current sets:

- `mailbox-core`
- `mailbox-full`

Current fixed auto-install selections:

- managed launch: `mailbox-full`
- managed join: `mailbox-full`
- CLI default: `mailbox-full`

## Current Skill Inventory

The current packaged Houmao-owned skills are:

- `houmao-process-emails-via-gateway`
- `houmao-email-via-agent-gateway`
- `houmao-email-via-filesystem`
- `houmao-email-via-stalwart`

These skill trees live under:

- `src/houmao/agents/assets/system_skills/mailbox/`

## Tool-Visible Projection Paths

The installer preserves the current visible tool-native skill paths:

| Tool | Visible projection root | Example |
| --- | --- | --- |
| `claude` | `skills/` | `skills/houmao-email-via-agent-gateway/SKILL.md` |
| `codex` | `skills/mailbox/` | `skills/mailbox/houmao-email-via-agent-gateway/SKILL.md` |
| `gemini` | `.agents/skills/` | `.agents/skills/houmao-email-via-agent-gateway/SKILL.md` |

That means mailbox prompts, runtime docs, and existing managed-session guidance keep the same visible skill names and paths even though installation is now catalog-driven.

## Install State And Ownership

Each target tool home stores Houmao-owned install state under:

```text
<tool-home>/.houmao/system-skills/install-state.json
```

That file records:

- target tool
- installed skill names
- packaged asset subpaths
- projected relative directories
- content digests

Houmao uses that state to make reinstall idempotent and to distinguish Houmao-owned paths from unrelated user-authored content already present in the same tool home.

Collision policy:

- if the projected Houmao-owned path does not exist, install it
- if it exists and is already recorded as Houmao-owned, replace it safely
- if it exists but is not recorded as Houmao-owned, fail closed rather than overwriting it

## `list`

Use `list` to inspect the packaged inventory, named sets, and fixed defaults:

```bash
pixi run houmao-mgr system-skills list
pixi run houmao-mgr --print-json system-skills list
```

This reports:

- current skill inventory
- named sets
- managed-launch set list
- managed-join set list
- CLI-default set list

## `status`

Use `status` to inspect one explicit tool home:

```bash
pixi run houmao-mgr system-skills status --tool codex --home ~/.codex
```

`status` reports:

- target tool
- resolved target home
- whether Houmao-owned install state exists
- installed Houmao-owned skill names recorded for that home

If the home has never been touched by the shared installer, `status` reports that install state is missing and does not claim any Houmao-owned skills are installed there.

## `install`

Use `install` when you want the current Houmao-owned skill surface in an explicit external tool home:

```bash
pixi run houmao-mgr system-skills install --tool codex --home ~/.codex --default
pixi run houmao-mgr system-skills install --tool codex --home ~/.codex --set mailbox-core
pixi run houmao-mgr system-skills install --tool codex --home ~/.codex --set mailbox-core --skill houmao-email-via-filesystem
```

Selection rules:

- `--default` expands the catalog's CLI-default set list
- repeatable `--set` expands named sets in the order given
- repeatable `--skill` appends explicit skill names after the expanded sets
- the final skill list is deduplicated by first occurrence
- omitting `--default`, `--set`, and `--skill` is an error
- unknown set names or skill names are errors

## Internal Auto-Install Behavior

Managed homes and joined homes use the same installer and catalog:

- `brains build` installs the skill list resolved from `auto_install.managed_launch_sets`
- `agents join` installs the skill list resolved from `auto_install.managed_join_sets`
- `agents join --no-install-houmao-skills` skips that default installer step

This removes the old mailbox-only special path while keeping the current visible mailbox skill contract unchanged.

## When To Use This Surface

Use `system-skills` when:

- you want to prepare an external Claude, Codex, or Gemini home before using `houmao-mgr`
- you want to inspect whether Houmao already installed its own skill set into a home
- you want the same Houmao-owned mailbox skill surface outside a Houmao-managed launch or join flow

Do not use it for:

- project-local user skills under `.houmao/agents/`
- easy specialists or preset-selected project skills
- mailbox registration itself; that still uses `houmao-mgr mailbox ...` and `houmao-mgr agents mailbox ...`

## Related References

- [houmao-mgr](houmao-mgr.md)
- [Mailbox Reference](../mailbox/index.md)
- [Agents And Runtime](../system-files/agents-and-runtime.md)

## Source References

- [`src/houmao/agents/system_skills.py`](../../../src/houmao/agents/system_skills.py)
- [`src/houmao/agents/assets/system_skills/catalog.toml`](../../../src/houmao/agents/assets/system_skills/catalog.toml)
- [`src/houmao/agents/assets/system_skills/catalog.schema.json`](../../../src/houmao/agents/assets/system_skills/catalog.schema.json)
- [`src/houmao/srv_ctrl/commands/system_skills.py`](../../../src/houmao/srv_ctrl/commands/system_skills.py)
- [`src/houmao/agents/brain_builder.py`](../../../src/houmao/agents/brain_builder.py)
- [`src/houmao/srv_ctrl/commands/runtime_artifacts.py`](../../../src/houmao/srv_ctrl/commands/runtime_artifacts.py)
