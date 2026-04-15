# system-skills

`houmao-mgr system-skills` is the operator-facing surface for installing the current Houmao-owned `houmao-*` skills into resolved Claude, Codex, or Gemini homes.

> **Looking for the narrative tour?** See the [System Skills Overview](../../getting-started/system-skills-overview.md) getting-started guide for a 5-minute walkthrough of every packaged skill, when each one fires, and how managed-home auto-install differs from explicit CLI-default install.

This is the same packaged skill system used internally by:

- `houmao-mgr brains build` when it creates a managed home,
- `houmao-mgr agents join` when it adopts an existing session and auto-installs Houmao-owned skills into the adopted tool home.

The current implementation is still intentionally narrow. It covers the packaged Houmao-owned skills declared in `src/houmao/agents/assets/system_skills/catalog.toml`:

- `houmao-process-emails-via-gateway` for round-oriented gateway mailbox workflow
- `houmao-agent-email-comms` for ordinary shared-mailbox operations and the no-gateway fallback path
- `houmao-adv-usage-pattern` for supported multi-skill mailbox and gateway workflow compositions such as self-wakeup through self-mail plus notifier-driven rounds
- `houmao-touring` for a manual guided tour that helps first-time or re-orienting users branch across project setup, mailbox setup, specialist/profile authoring, live-agent operations, and lifecycle follow-up
- `houmao-mailbox-mgr` for mailbox-root lifecycle, mailbox account lifecycle, structural mailbox inspection, and late filesystem mailbox binding on existing local managed agents
- `houmao-memory-mgr` for supported managed-agent memory edits to the fixed `houmao-memo.md` file and contained `pages/` files
- `houmao-project-mgr` for project overlay lifecycle, `.houmao/` layout explanation, project-aware command effects, explicit launch-profile management, and project-scoped easy-instance inspection or stop routing
- `houmao-specialist-mgr` for reusable specialist and easy-profile authoring plus easy-workflow launch and stop entry
- `houmao-credential-mgr` for project-local and plain-agent-definition-directory credential management
- `houmao-agent-definition` for low-level role and recipe definition management (canonical `project agents recipes ...` plus the compatibility `project agents presets ...` alias)
- `houmao-agent-instance` for live managed-agent instance lifecycle
- `houmao-agent-inspect` for generic read-only managed-agent inspection across liveness, screen posture, mailbox posture, logs, runtime artifacts, and bounded local tmux peeking
- `houmao-agent-messaging` for communication and control of already-running managed agents across prompt, gateway, raw-input, mailbox routing, and reset-context workflows
- `houmao-agent-gateway` for live gateway lifecycle, manifest-first discovery, gateway-only control, ranked reminders, and gateway mail-notifier behavior
- `houmao-agent-loop-pairwise` for the restored stable pairwise loop surface: authoring master-owned pairwise loop plans and operating accepted runs through `start`, `status`, and `stop` while the user agent stays outside the execution loop
- `houmao-agent-loop-pairwise-v2` for the versioned enriched pairwise workflow: authoring master-owned pairwise loop plans plus `initialize`, `start`, `peek`, `ping`, `pause`, `resume`, `stop`, and `hard-kill` while the user agent stays outside the execution loop
- `houmao-agent-loop-generic` for decomposing generic loop graphs into typed pairwise and relay components and operating accepted root-owned runs through start, status, and stop

The two pairwise skill names are distinct packaged choices, not aliases. `houmao-agent-loop-pairwise` is the restored stable `start|status|stop` surface, while `houmao-agent-loop-pairwise-v2` preserves the enriched authoring, prestart, and expanded run-control workflow.

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
- `agent-memory`
- `advanced-usage`
- `touring`
- `user-control`
- `agent-instance`
- `agent-inspect`
- `agent-messaging`
- `agent-gateway`

Current fixed auto-install selections:

- managed launch: `mailbox-full`, `agent-memory`, `advanced-usage`, `touring`, `user-control`, `agent-inspect`, `agent-messaging`, `agent-gateway`
- managed join: `mailbox-full`, `agent-memory`, `advanced-usage`, `touring`, `user-control`, `agent-inspect`, `agent-messaging`, `agent-gateway`
- CLI default: `mailbox-full`, `agent-memory`, `advanced-usage`, `touring`, `user-control`, `agent-instance`, `agent-inspect`, `agent-messaging`, `agent-gateway`

## Current Skill Inventory

The current packaged Houmao-owned skills are:

- `houmao-process-emails-via-gateway`
- `houmao-agent-email-comms`
- `houmao-adv-usage-pattern`
- `houmao-touring`
- `houmao-mailbox-mgr`
- `houmao-memory-mgr`
- `houmao-project-mgr`
- `houmao-specialist-mgr`
- `houmao-credential-mgr`
- `houmao-agent-definition`
- `houmao-agent-loop-pairwise`
- `houmao-agent-loop-pairwise-v2`
- `houmao-agent-loop-generic`
- `houmao-agent-instance`
- `houmao-agent-inspect`
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

That means Houmao-owned mailbox, touring, and user-control skills stay grouped by reserved skill names and named sets rather than by family-specific path segments.

## Stateless Ownership And Legacy Cleanup

The shared installer no longer treats `.houmao/system-skills/install-state.json` as the ownership contract.

Instead, Houmao treats an explicit path set as replaceable for each selected current skill:

- the current tool-native target path for that skill
- known flat legacy aliases for that current skill
- documented retired family or Gemini alias paths for that current skill

That keeps reinstall idempotent without reserving every `houmao-*` directory in the target home.

Collision policy:

- if the current or legacy Houmao-owned path is part of the selected skill's explicit replaceable set, install may remove and replace it
- unrelated content outside that explicit current and legacy path set is preserved
- successful reinstall removes an obsolete `.houmao/system-skills/install-state.json` file if one is still present from older versions

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
- installed current Houmao-owned skill names discovered in that home
- the inferred projection mode for each installed current skill (`copy` or `symlink`)

If the home has never been touched by the shared installer, `status` reports no installed current Houmao-owned skills. If a stale legacy install-state file exists but the current packaged skill paths do not, `status` ignores that file.

## `install`

Use `install` when you want the current Houmao-owned skill surface in a resolved external or project-scoped tool home:

```bash
pixi run houmao-mgr system-skills install --tool codex
pixi run houmao-mgr system-skills install --tool codex --home ~/.codex
pixi run houmao-mgr system-skills install --tool codex --home ~/.codex --set mailbox-core
pixi run houmao-mgr system-skills install --tool codex --home ~/.codex --set agent-memory
pixi run houmao-mgr system-skills install --tool codex --home ~/.codex --set advanced-usage
pixi run houmao-mgr system-skills install --tool codex --home ~/.codex --set mailbox-core --skill houmao-agent-email-comms
pixi run houmao-mgr system-skills install --tool codex --home ~/.codex --set user-control
pixi run houmao-mgr system-skills install --tool codex --home ~/.codex --set touring
pixi run houmao-mgr system-skills install --tool codex --home ~/.codex --set agent-instance
pixi run houmao-mgr system-skills install --tool codex --home ~/.codex --set agent-inspect
pixi run houmao-mgr system-skills install --tool codex --home ~/.codex --set agent-messaging
pixi run houmao-mgr system-skills install --tool codex --home ~/.codex --set agent-gateway
pixi run houmao-mgr system-skills install --tool gemini --set user-control
pixi run houmao-mgr system-skills install --tool codex --home ~/.codex --skill houmao-specialist-mgr --symlink
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
- reinstall may also remove exact legacy Houmao-owned skill aliases for the selected current skills and delete an obsolete legacy install-state file

## Internal Auto-Install Behavior

Managed homes and joined homes use the same installer and catalog:

- `brains build` installs the skill list resolved from `auto_install.managed_launch_sets`
- `agents join` installs the skill list resolved from `auto_install.managed_join_sets`
- `agents join --no-install-houmao-skills` skips that default installer step

Those managed flows continue to use copied projection in this change even though explicit `system-skills install` now supports `--symlink`.

This removes the old mailbox-only special path and family-specific Codex subtrees while keeping logical grouping in named sets such as `mailbox-full`, `agent-memory`, `advanced-usage`, `touring`, `user-control`, `agent-instance`, `agent-inspect`, and `agent-messaging`.

Today the packaged mailbox sets are intentionally compact:

- `mailbox-core` installs `houmao-process-emails-via-gateway` plus `houmao-agent-email-comms`
- `mailbox-full` installs that mailbox worker pair plus `houmao-mailbox-mgr`
- `agent-memory` installs `houmao-memory-mgr`
- `advanced-usage` installs `houmao-adv-usage-pattern`
- `touring` installs `houmao-touring`

For the `touring` set, the packaged skill is `houmao-touring`. Its top-level `SKILL.md` is a manual-only guided touring index that starts from current Houmao state, explains the next likely branches in plain language, and routes execution to the maintained Houmao-owned project, mailbox, specialist, messaging, gateway, email, and lifecycle skills instead of flattening those direct-operation surfaces into one broad guide.

For the `user-control` set, the packaged skills are `houmao-project-mgr`, `houmao-specialist-mgr`, `houmao-credential-mgr`, `houmao-agent-definition`, `houmao-agent-loop-pairwise`, `houmao-agent-loop-pairwise-v2`, and `houmao-agent-loop-generic`. `houmao-project-mgr` is the packaged router for `project init`, `project status`, `project agents launch-profiles ...`, and project-scoped `project easy instance list|get|stop`, plus the explanatory material for overlay resolution, `.houmao/` layout, and project-aware effects on other command families. `houmao-specialist-mgr` is the packaged router for `project easy specialist create|list|get|remove`, `project easy profile create|list|get|remove`, and easy-workflow `project easy instance launch|stop` from either source kind. After those easy-instance runtime actions, it tells the user to continue broader live-agent management through `houmao-agent-instance`. `houmao-credential-mgr` is the packaged router for `project credentials <tool> list|get|add|set|rename|remove` plus `credentials <tool> ... --agent-def-dir <path>`, and it keeps specialist CRUD, profile CRUD, instance lifecycle, mailbox cleanup, direct auth-file editing, and filesystem-path inference outside that packaged skill scope. `houmao-agent-definition` is the packaged router for `project agents roles list|get|init|set|remove` plus canonical `project agents recipes list|get|add|set|remove` while preserving `project agents presets ...` as the compatibility alias, and it keeps credential content mutation on `houmao-credential-mgr` while using `roles get --include-prompt` for explicit prompt inspection. `houmao-agent-loop-pairwise` is the restored stable pairwise choice for `start|status|stop` control. `houmao-agent-loop-pairwise-v2` is the versioned enriched choice for authoring plus `initialize|start|peek|ping|pause|resume|stop|hard-kill`. `houmao-agent-loop-generic` is the generic graph-planning choice for decomposing mixed pairwise/relay component graphs and operating accepted root-owned runs through `start|status|stop`. The stable and versioned pairwise skills are distinct packaged choices rather than aliases.

For the `agent-instance` set, the packaged skill is `houmao-agent-instance`. Its top-level `SKILL.md` is an index/router for managed-agent instance lifecycle work across `agents launch`, `project easy instance launch`, `agents join`, `agents list`, `agents stop`, `agents relaunch`, and `agents cleanup session|logs`. It remains the canonical follow-up lifecycle skill even though `houmao-specialist-mgr` now also covers easy-workflow `launch` and `stop`, `houmao-project-mgr` owns project-scoped `project easy instance list|get|stop`, and it keeps mailbox surfaces, specialist/profile CRUD, prompt/gateway control, and mailbox cleanup outside that packaged skill scope.

For the `agent-inspect` set, the packaged skill is `houmao-agent-inspect`. Its top-level `SKILL.md` is the Houmao-owned router for generic read-only managed-agent inspection across `agents list|state`, `GET /houmao/agents/{agent_ref}/state/detail`, gateway TUI tracker inspection, mailbox posture, durable headless turn evidence, runtime artifacts, and bounded local tmux peeking. It keeps prompt submission, gateway mutation, mailbox mutation, lifecycle mutation, and recorder workflows outside that packaged inspection scope.

For the `agent-messaging` set, the packaged skill is `houmao-agent-messaging`. Its top-level `SKILL.md` is the Houmao-owned router for communication with already-running managed agents across `agents prompt`, `agents interrupt`, `agents gateway prompt|interrupt`, `agents gateway send-keys`, `agents gateway tui state|history|note-prompt`, `agents mail resolve-live`, and the matching `/houmao/agents/*` HTTP routes. It routes by communication intent rather than by one hardcoded transport path, prefers the managed-agent seam for ordinary prompt and interrupt work, uses `agents mail resolve-live` for mailbox discovery and handoff, keeps queue-specific tracker inspection and prompt provenance available, documents direct gateway HTTP only for lower-level gateway-only control such as the current reset-context APIs, and delegates generic managed-agent inspection to `houmao-agent-inspect`.

For the `agent-gateway` set, the packaged skill is `houmao-agent-gateway`. Its top-level `SKILL.md` is the Houmao-owned router for live gateway lifecycle and gateway-only services across `agents gateway attach|detach|status`, current-session manifest-first discovery, explicit gateway control, direct `/v1/reminders`, and `agents gateway mail-notifier ...`. It is explicit about the supported discovery boundary: current-session targeting resolves through `HOUMAO_MANIFEST_PATH` first and `HOUMAO_AGENT_ID` second, shared mailbox work should still obtain the exact current `gateway.base_url` through `agents mail resolve-live`, `/v1/reminders` remains non-durable live gateway state rather than a persisted recovery queue, there is no supported `agents gateway reminders ...` CLI family or managed-agent `/houmao/agents/{agent_ref}/gateway/reminders` projection, and generic managed-agent inspection belongs on `houmao-agent-inspect` instead.

For the `agent-memory` set, the packaged skill is `houmao-memory-mgr`. Its top-level `SKILL.md` is the Houmao-owned router for supported managed-agent memory operations across `agents memory path|status`, `agents memory memo show|set|append`, and `agents memory tree|resolve|read|write|append|delete`. It keeps the fixed `houmao-memo.md` file free-form, treats `pages/` links as authored Markdown, rejects traversal outside `pages/`, and keeps live runtime bookkeeping out of managed memory pages.

For the mailbox sets, the packaged mailbox-admin skill is `houmao-mailbox-mgr`. It is the Houmao-owned entrypoint for `houmao-mgr mailbox ...`, `houmao-mgr project mailbox ...`, and `houmao-mgr agents mailbox ...`, covering filesystem mailbox root lifecycle, mailbox account lifecycle, structural mailbox inspection, and late filesystem mailbox binding on existing local managed agents. The packaged ordinary mailbox skill remains `houmao-agent-email-comms`, which is the unified router for shared `/v1/mail/*` work, mailbox transport-aware fallback, and mailbox binding inspection after `agents mail resolve-live`, while `houmao-process-emails-via-gateway` remains the separate notifier-round workflow skill. The dedicated `advanced-usage` set adds `houmao-adv-usage-pattern` as the supported workflow-composition layer above those direct mailbox and gateway skills.

CLI-default installation now includes the full three-skill mailbox set, the `agent-memory` set, the dedicated `advanced-usage` and `touring` skills, the `user-control` set (project-mgr, specialist-mgr, credential-mgr, agent-definition, the restored stable pairwise skill, the versioned enriched pairwise-v2 skill, and the generic loop graph-planning skill), and the dedicated `agent-instance`, `agent-inspect`, `agent-messaging`, and `agent-gateway` skills. Managed launch and managed join auto-install `mailbox-full`, `agent-memory`, `advanced-usage`, `touring`, `user-control`, `agent-inspect`, `agent-messaging`, and `agent-gateway`, which means they install every packaged skill in the catalog except the lifecycle-only `houmao-agent-instance` and pick up both pairwise variants plus the generic loop planner through the shared `user-control` set.

## When To Use This Surface

Use `system-skills` when:

- you want to prepare an external Claude, Codex, or Gemini home before using `houmao-mgr`
- you want to inspect whether Houmao already installed its own skill set into a home
- you want the same Houmao-owned guided touring, project-management, mailbox administration, ordinary mailbox participation, low-level definition-management, specialist-management, credential-management, managed-agent inspection, messaging/control, gateway-management, or instance-lifecycle skill surface outside a Houmao-managed launch or join flow

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
