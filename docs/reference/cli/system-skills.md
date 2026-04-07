# system-skills

`houmao-mgr system-skills` is the operator-facing surface for installing the current Houmao-owned `houmao-*` skills into resolved Claude, Codex, or Gemini homes.

This is the same packaged skill system used internally by:

- `houmao-mgr brains build` when it creates a managed home,
- `houmao-mgr agents join` when it adopts an existing session and auto-installs Houmao-owned skills into the adopted tool home.

The current implementation is still intentionally narrow. It currently covers the mailbox-oriented Houmao-owned skills plus six packaged non-mailbox Houmao skills:

- `houmao-manage-specialist` for reusable specialist and easy-profile authoring plus easy-workflow launch and stop entry
- `houmao-manage-credentials` for project-local credential management
- `houmao-manage-agent-definition` for low-level role and recipe definition management (canonical `project agents recipes ...` plus the compatibility `project agents presets ...` alias)
- `houmao-manage-agent-instance` for live managed-agent instance lifecycle
- `houmao-agent-messaging` for communication and control of already-running managed agents across prompt, gateway, raw-input, mailbox, and reset-context workflows
- `houmao-agent-gateway` for live gateway lifecycle, manifest-first discovery, gateway-only control, wakeups, and gateway mail-notifier behavior

It does not yet generalize to non-skill asset kinds.

## Command Shape

```text
houmao-mgr system-skills
├── list
├── status --tool <tool> [--home <path>]
└── install --tool <tool> [--home <path>] [--set <name> ...] [--skill <name> ...] [--symlink]
```

## Effective Home Resolution

When `--home` is omitted, both `status` and `install` resolve the effective tool home with this precedence:

1. explicit `--home`
2. tool-native home env var
3. project-scoped default home

Supported tool-native home env vars:

- Claude: `CLAUDE_CONFIG_DIR`
- Codex: `CODEX_HOME`
- Gemini: `GEMINI_CLI_HOME`

Project-scoped default homes:

- Claude: `<cwd>/.claude`
- Codex: `<cwd>/.codex`
- Gemini: `<cwd>`

Gemini is intentionally different from Claude and Codex. The effective Gemini home root is the project root, which means omitted-home Gemini installs land under `<cwd>/.gemini/skills/` while Gemini provider state remains under `<cwd>/.gemini/`.

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
- `user-control`
- `agent-instance`
- `agent-messaging`
- `agent-gateway`

Current fixed auto-install selections:

- managed launch: `mailbox-full`, `user-control`, `agent-messaging`, `agent-gateway`
- managed join: `mailbox-full`, `user-control`, `agent-messaging`, `agent-gateway`
- CLI default: `mailbox-full`, `user-control`, `agent-instance`, `agent-messaging`, `agent-gateway`

## Current Skill Inventory

The current packaged Houmao-owned skills are:

- `houmao-process-emails-via-gateway`
- `houmao-agent-email-comms`
- `houmao-manage-specialist`
- `houmao-manage-credentials`
- `houmao-manage-agent-definition`
- `houmao-manage-agent-instance`
- `houmao-agent-messaging`
- `houmao-agent-gateway`

These skill trees live directly under:

- `src/houmao/agents/assets/system_skills/<houmao-skill>/`

## Tool-Visible Projection Paths

The installer preserves the current visible tool-native skill roots with flat Houmao-owned skill directories:

| Tool | Visible projection root | Example |
| --- | --- | --- |
| `claude` | `skills/` | `skills/houmao-agent-email-comms/SKILL.md` |
| `codex` | `skills/` | `skills/houmao-agent-messaging/SKILL.md` |
| `gemini` | `.gemini/skills/` | `.gemini/skills/houmao-agent-email-comms/SKILL.md` |

That means Houmao-owned mailbox and user-control skills stay grouped by reserved skill names and named sets rather than by family-specific path segments.

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
- projection modes
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

Use `status` to inspect one resolved tool home:

```bash
pixi run houmao-mgr system-skills status --tool codex
pixi run houmao-mgr system-skills status --tool codex --home ~/.codex
```

`status` reports:

- target tool
- resolved target home
- whether Houmao-owned install state exists
- installed Houmao-owned skill names recorded for that home
- the recorded projection mode for each installed skill

If the home has never been touched by the shared installer, `status` reports that install state is missing and does not claim any Houmao-owned skills are installed there.

## `install`

Use `install` when you want the current Houmao-owned skill surface in a resolved external or project-scoped tool home:

```bash
pixi run houmao-mgr system-skills install --tool codex
pixi run houmao-mgr system-skills install --tool codex --home ~/.codex
pixi run houmao-mgr system-skills install --tool codex --home ~/.codex --set mailbox-core
pixi run houmao-mgr system-skills install --tool codex --home ~/.codex --set mailbox-core --skill houmao-agent-email-comms
pixi run houmao-mgr system-skills install --tool codex --home ~/.codex --set user-control
pixi run houmao-mgr system-skills install --tool codex --home ~/.codex --set agent-instance
pixi run houmao-mgr system-skills install --tool codex --home ~/.codex --set agent-messaging
pixi run houmao-mgr system-skills install --tool codex --home ~/.codex --set agent-gateway
pixi run houmao-mgr system-skills install --tool gemini --set user-control
pixi run houmao-mgr system-skills install --tool codex --home ~/.codex --skill houmao-manage-specialist --symlink
```

Selection rules:

- omitting both `--set` and `--skill` expands the catalog's CLI-default set list
- repeatable `--set` expands named sets in the order given
- repeatable `--skill` appends explicit skill names after the expanded sets
- `--symlink` switches the install from copied projection to directory symlink projection
- the final skill list is deduplicated by first occurrence
- unknown set names or skill names are errors

Home-resolution rules:

- `--home` is optional
- when omitted, the command resolves the effective home using explicit tool-native env redirection first and project-scoped defaults second
- omitted-home Gemini installs use the project root as the effective home, so Houmao-owned skills land under `.gemini/skills/`

Projection rules:

- without `--symlink`, Houmao copies the packaged skill tree into the target home
- with `--symlink`, Houmao creates one directory symlink per selected skill in the tool-native skill root
- symlink installs use the absolute filesystem path of the packaged skill asset as the symlink target
- if the packaged skill asset is not backed by a stable real filesystem directory, `--symlink` fails explicitly instead of falling back to copied projection
- `--symlink` is a local-machine convenience mode; if the Python environment or installed package path moves, reinstall the skills to refresh the symlink targets

## Internal Auto-Install Behavior

Managed homes and joined homes use the same installer and catalog:

- `brains build` installs the skill list resolved from `auto_install.managed_launch_sets`
- `agents join` installs the skill list resolved from `auto_install.managed_join_sets`
- `agents join --no-install-houmao-skills` skips that default installer step

Those managed flows continue to use copied projection in this change even though explicit `system-skills install` now supports `--symlink`.

This removes the old mailbox-only special path and family-specific Codex subtrees while keeping logical grouping in named sets such as `mailbox-full`, `user-control`, `agent-instance`, and `agent-messaging`.

Today the packaged mailbox sets are intentionally compact:

- `mailbox-core` installs `houmao-process-emails-via-gateway` plus `houmao-agent-email-comms`
- `mailbox-full` currently resolves to the same two-skill mailbox pair

For the `user-control` set, the packaged skills are `houmao-manage-specialist`, `houmao-manage-credentials`, and `houmao-manage-agent-definition`. `houmao-manage-specialist` is the packaged router for `project easy specialist create|list|get|remove`, `project easy profile create|list|get|remove`, and easy-workflow `project easy instance launch|stop` from either source kind. After those easy-instance runtime actions, it tells the user to continue broader live-agent management through `houmao-manage-agent-instance`. `houmao-manage-credentials` is the packaged router for `project agents tools <tool> auth list|get|add|set|remove`, and it keeps specialist CRUD, profile CRUD, instance lifecycle, mailbox cleanup, and direct auth-file editing outside that packaged skill scope. `houmao-manage-agent-definition` is the packaged router for `project agents roles list|get|init|set|remove` plus canonical `project agents recipes list|get|add|set|remove` while preserving `project agents presets ...` as the compatibility alias, and it keeps auth-bundle content mutation on `houmao-manage-credentials` while using `roles get --include-prompt` for explicit prompt inspection.

For the `agent-instance` set, the packaged skill is `houmao-manage-agent-instance`. Its top-level `SKILL.md` is an index/router for managed-agent instance lifecycle work across `agents launch`, `project easy instance launch`, `agents join`, `agents list`, `agents stop`, and `agents cleanup session|logs`. It remains the canonical follow-up lifecycle skill even though `houmao-manage-specialist` now also covers easy-workflow `launch` and `stop`, and it keeps mailbox surfaces, specialist/profile CRUD, prompt/gateway control, and mailbox cleanup outside that packaged skill scope.

For the `agent-messaging` set, the packaged skill is `houmao-agent-messaging`. Its top-level `SKILL.md` is the Houmao-owned router for communication with already-running managed agents across `agents prompt`, `agents interrupt`, `agents gateway prompt|interrupt`, `agents gateway send-keys`, `agents gateway tui state|history|note-prompt`, `agents mail resolve-live|status|check|send|reply|mark-read`, and the matching `/houmao/agents/*` HTTP routes. It routes by communication intent rather than by one hardcoded transport path, prefers the managed-agent seam for ordinary prompt and interrupt work, documents direct gateway HTTP only for lower-level gateway-only control such as the current reset-context APIs, and keeps transport-specific mailbox detail in the mailbox skill family rather than in the generic messaging skill.

For the `agent-gateway` set, the packaged skill is `houmao-agent-gateway`. Its top-level `SKILL.md` is the Houmao-owned router for live gateway lifecycle and gateway-only services across `agents gateway attach|detach|status`, current-session manifest-first discovery, explicit gateway control, direct `/v1/wakeups`, and `agents gateway mail-notifier ...`. It is explicit about the supported discovery boundary: current-session targeting resolves through `HOUMAO_MANIFEST_PATH` first and `HOUMAO_AGENT_ID` second, shared mailbox work should still obtain the exact current `gateway.base_url` through `agents mail resolve-live`, and `/v1/wakeups` remains non-durable live gateway state rather than a persisted recovery queue.

For the mailbox sets, the packaged ordinary mailbox skill is `houmao-agent-email-comms`. It is the unified router for shared `/v1/mail/*` work, mailbox transport-aware fallback, and mailbox binding inspection after `agents mail resolve-live`, while `houmao-process-emails-via-gateway` remains the separate notifier-round workflow skill.

CLI-default installation now includes all six packaged non-mailbox Houmao skills. Managed launch and managed join auto-install the full `user-control` set plus `agent-messaging` and `agent-gateway`, but they still do not automatically add the separate `agent-instance` lifecycle set.

## When To Use This Surface

Use `system-skills` when:

- you want to prepare an external Claude, Codex, or Gemini home before using `houmao-mgr`
- you want to inspect whether Houmao already installed its own skill set into a home
- you want the same Houmao-owned mailbox, low-level definition-management, specialist-management, credential-management, messaging/control, gateway-management, or instance-lifecycle skill surface outside a Houmao-managed launch or join flow

Do not use it for:

- project-local user skills under `.houmao/agents/`
- easy specialists or recipe-selected project skills
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
