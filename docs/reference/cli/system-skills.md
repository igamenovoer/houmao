# system-skills

`houmao-mgr system-skills` is the operator-facing surface for installing, removing, and inspecting the current Houmao-owned `houmao-*` skills in resolved Claude, Codex, Copilot, or Gemini homes.

> **Looking for the narrative tour?** See the [System Skills Overview](../../getting-started/system-skills-overview.md) getting-started guide for a 5-minute walkthrough of every packaged skill, when each one fires, and how managed-home auto-install differs from explicit CLI-default install.

This is the same packaged skill system used internally by:

- `houmao-mgr brains build` when it creates a managed home,
- `houmao-mgr agents join` when it adopts an existing session and auto-installs Houmao-owned skills into the adopted tool home.

The current implementation is still intentionally narrow. It covers the packaged Houmao-owned skills declared in `src/houmao/agents/assets/system_skills/catalog.toml`:

- `houmao-process-emails-via-gateway` for round-oriented gateway mailbox workflow
- `houmao-agent-email-comms` for ordinary shared-mailbox operations and the no-gateway fallback path
- `houmao-adv-usage-pattern` for supported multi-skill mailbox and gateway workflow compositions such as self-wakeup through self-mail plus notifier-driven rounds
- `houmao-utils-llm-wiki` for explicit persistent Markdown LLM Wiki knowledge-base utilities: scaffold, ingest, compile, query, lint, audit, and local viewer workflows
- `houmao-utils-workspace-mgr` for explicit multi-agent workspace planning and execution utilities: dry-run plans, in-repo and out-of-repo workspace layouts, per-agent Git worktrees, local-only shared repos, tracked submodule materialization, launch-profile cwd updates, and optional memo-seed workspace rules
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
├── install --tool <tool>[,<tool>...] [--home <path>] [--skill-set <name> ...] [--skill <name> ...] [--symlink]
└── uninstall --tool <tool>[,<tool>...] [--home <path>]
```

## Effective Home Resolution

For single-tool `install`, `uninstall`, and `status` commands, explicit `--home` overrides all other home selection. When `--home` is omitted, the command resolves the effective tool home with this precedence:

1. tool-native home env var
2. project-scoped default home

For comma-separated multi-tool `install` and `uninstall`, omit `--home`; each selected tool resolves through its own tool-native env var and project-scoped default home. If you need explicit home overrides, run separate single-tool commands.

Supported tool-native home env vars:

- Claude: `CLAUDE_CONFIG_DIR`
- Codex: `CODEX_HOME`
- Copilot: `COPILOT_HOME`
- Gemini: `GEMINI_CLI_HOME`

Project-scoped default homes:

- Claude: `<cwd>/.claude`
- Codex: `<cwd>/.codex`
- Copilot: `<cwd>/.github`
- Gemini: `<cwd>`

Gemini is intentionally different from Claude and Codex. The effective Gemini home root is the project root, which means omitted-home Gemini installs land under `<cwd>/.gemini/skills/` while Gemini provider state remains under `<cwd>/.gemini/`.

Copilot uses the same home-relative `skills/` projection as Claude and Codex, but its project-scoped default home is `<cwd>/.github`. That means omitted-home Copilot installs land under `<cwd>/.github/skills/`. To install the same Houmao-owned skills into a personal Copilot CLI home, pass an explicit home such as `--home ~/.copilot` or set `COPILOT_HOME`; no separate scope flag is required.

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

- `core`
- `all`

Current fixed auto-install selections:

- managed launch: `core`
- managed join: `core`
- CLI default: `all`

## Current Skill Inventory

The current packaged Houmao-owned skills are:

- `houmao-process-emails-via-gateway`
- `houmao-agent-email-comms`
- `houmao-adv-usage-pattern`
- `houmao-utils-llm-wiki`
- `houmao-utils-workspace-mgr`
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
| `copilot` | `skills/` | `.github/skills/houmao-agent-messaging/SKILL.md` for the project default, or `~/.copilot/skills/houmao-agent-messaging/SKILL.md` with `--home ~/.copilot` |
| `gemini` | `.gemini/skills/` | `.gemini/skills/houmao-agent-email-comms/SKILL.md` |

That means Houmao-owned skills stay grouped by reserved skill names and closed named sets rather than by family-specific path segments.

## Human-Readable Projection Output

Plain `install`, `status`, and `uninstall` output distinguishes the effective tool home from the skill projection location. The effective home is the root used for tool-home resolution and later status/uninstall targeting. The projection location is where Houmao-owned skill directories actually appear under that home.

For Claude, Codex, and Copilot, the projection root is usually `<effective-home>/skills/`. For Gemini, the effective home may be the project root while the projection root is `<effective-home>/.gemini/skills/`. For example, if omitted-home Gemini resolution chooses `/workspace/repo`, the installed Houmao-owned Gemini skill files live under `/workspace/repo/.gemini/skills/`.

The plain output reports projection roots or projected paths so an operator can locate installed, discovered, removed, or absent skill paths without switching to JSON output.

## Stateless Selected-Skill Replacement

The shared installer does not create or require `.houmao/system-skills/install-state.json` in target tool homes.

For each selected current Houmao-owned skill, reinstall computes the exact current tool-native destination path, removes that path if it already exists as a directory, file, or symlink, and then projects the packaged skill with the requested mode.

Replacement policy:

- selected current Houmao-owned skill paths are explicit overwrite targets
- copied projection materializes the packaged skill tree into the selected destination
- symlink projection replaces the selected destination with a directory symlink to the packaged asset root
- unselected skill directories, parent skill roots, legacy family-namespaced paths, unrelated tool-home content, and stale install-state files are not removed
- old install-state files are ignored rather than migrated

## Stateless All-Known-Skill Removal

`system-skills uninstall` uses the same catalog and projection rules, but it is intentionally not selective. It targets every current Houmao-owned skill listed in the packaged catalog for the resolved tool home.

Removal policy:

- every current catalog-known Houmao-owned skill path is an explicit removal target
- copied directories, symlinks, and files at those exact current paths are removed
- missing current skill paths are reported as absent rather than errors
- missing target homes are not created just to uninstall
- parent skill roots, unrelated user skills, unrecognized `houmao-*` paths, legacy family-namespaced paths, and stale install-state files are not removed

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
- the projected relative path for each discovered current skill
- the inferred projection mode for each installed current skill (`copy` or `symlink`)

If the home has never been touched by the shared installer, `status` reports no installed current Houmao-owned skills. `status` discovers current packaged skill paths from the filesystem and ignores old install-state files.

## `install`

Use `install` when you want the current Houmao-owned skill surface in a resolved external or project-scoped tool home:

```bash
pixi run houmao-mgr system-skills install --tool codex
pixi run houmao-mgr system-skills install --tool claude,codex,copilot,gemini
pixi run houmao-mgr system-skills install --tool codex --home ~/.codex
pixi run houmao-mgr system-skills install --tool codex --home ~/.codex --skill-set core
pixi run houmao-mgr system-skills install --tool codex --home ~/.codex --skill-set all
pixi run houmao-mgr system-skills install --tool copilot
pixi run houmao-mgr system-skills install --tool copilot --home ~/.copilot
pixi run houmao-mgr system-skills install --tool copilot --home ~/.copilot --skill-set core
pixi run houmao-mgr system-skills install --tool gemini --skill-set core
pixi run houmao-mgr system-skills install --tool codex --skill houmao-utils-llm-wiki
pixi run houmao-mgr system-skills install --tool codex --skill houmao-utils-workspace-mgr
pixi run houmao-mgr system-skills install --tool codex --home ~/.codex --skill houmao-specialist-mgr --symlink
```

Selection rules:

- omitting both `--skill-set` and `--skill` expands the catalog's CLI-default set list
- the CLI-default set list is `all`; use `--skill-set core` when utility skills should be omitted
- repeatable `--skill-set` expands named sets in the order given
- repeatable `--skill` appends explicit skill names after the expanded sets; use explicit utility skills on homes that already have `core` when you do not want the rest of `all`
- `--symlink` switches the install from copied projection to directory symlink projection
- the final skill list is deduplicated by first occurrence
- unknown set names or skill names are errors
- `--set` is no longer a supported install flag; use `--skill-set` for named system-skill sets

Home-resolution rules:

- `--home` is optional for single-tool install commands
- `--home` cannot be combined with comma-separated multi-tool install commands
- when omitted, the command resolves the effective home using tool-native env redirection first and project-scoped defaults second
- omitted-home Gemini installs use the project root as the effective home, so Houmao-owned skills land under `.gemini/skills/`

Structured output rules:

- single-tool JSON output keeps the existing scalar payload shape with `tool`, `home_path`, `selected_sets`, `explicit_skills`, `resolved_skills`, `projected_relative_dirs`, and `projection_mode`
- multi-tool JSON output returns `tools` plus one single-tool-shaped record per selected tool under `installations`

Plain output rules:

- single-tool output reports the effective home plus the installed projected skill path or projection root
- multi-tool output reports each selected tool's effective home plus skill projection root
- Gemini output reports `.gemini/skills` paths rather than implying that skills were installed directly into the effective home root

Projection rules:

- without `--symlink`, Houmao copies the packaged skill tree into the target home
- with `--symlink`, Houmao creates one directory symlink per selected skill in the tool-native skill root
- symlink installs use the absolute filesystem path of the packaged skill asset as the symlink target
- if the packaged skill asset is not backed by a stable real filesystem directory, `--symlink` fails explicitly instead of falling back to copied projection
- `--symlink` is a local-machine convenience mode; if the Python environment or installed package path moves, reinstall the skills to refresh the symlink targets
- reinstall replaces existing destinations for selected current skills without install-state ownership checks
- legacy skill aliases, old family-namespaced paths, and obsolete install-state files are ignored and are not deleted automatically before 1.0

## `uninstall`

Use `uninstall` when you want to remove the current Houmao-owned skill surface from a resolved external or project-scoped tool home:

```bash
pixi run houmao-mgr system-skills uninstall --tool codex
pixi run houmao-mgr system-skills uninstall --tool codex --home ~/.codex
pixi run houmao-mgr system-skills uninstall --tool claude,codex,copilot,gemini
pixi run houmao-mgr system-skills uninstall --tool copilot --home ~/.copilot
pixi run houmao-mgr system-skills uninstall --tool gemini
```

Uninstall rules:

- `uninstall` always targets every current skill in the packaged catalog
- selection flags such as `--skill`, `--skill-set`, `--set`, `--default`, and `--symlink` are not part of the uninstall surface
- `--home` is optional for single-tool uninstall commands
- `--home` cannot be combined with comma-separated multi-tool uninstall commands
- when omitted, the command resolves the effective home using tool-native env redirection first and project-scoped defaults second
- omitted-home Gemini uninstalls use the project root as the effective home, so Houmao-owned skills are removed from `.gemini/skills/`

Structured output rules:

- single-tool JSON output uses scalar `tool` and `home_path` fields and reports `removed_skills`, `removed_projected_relative_dirs`, `absent_skills`, and `absent_projected_relative_dirs`
- multi-tool JSON output returns `tools` plus one single-tool-shaped record per selected tool under `uninstallations`

Plain output rules:

- single-tool output reports the effective home plus removed or absent projected paths
- multi-tool output reports each selected tool's effective home plus removed or absent projection roots when paths share a root
- Gemini output reports `.gemini/skills` removal or absence paths rather than implying that current Houmao-owned skills were removed directly from the effective home root

Removal boundary:

- exact current Houmao-owned skill paths are removed whether they are copied directories, symlinks, or files
- missing current paths are reported as absent or skipped
- missing homes are not created
- parent skill roots, unrelated user skills, unrecognized `houmao-*` paths, legacy family-namespaced paths, and obsolete install-state files are preserved

## Internal Auto-Install Behavior

Managed homes and joined homes use the same installer and catalog:

- `brains build` installs the skill list resolved from `auto_install.managed_launch_sets`
- `agents join` installs the skill list resolved from `auto_install.managed_join_sets`
- `agents join --no-install-houmao-skills` skips that default installer step

Those managed flows continue to use copied projection in this change even though explicit `system-skills install` now supports `--symlink`.

This removes the old mailbox-only special path and family-specific Codex subtrees while keeping logical grouping in the closed `core` and `all` sets. The smaller `core` set is deliberately closed over the current internal skill-routing graph, so skills installed through `core` do not direct agents to another Houmao system skill that was left out. The `all` set adds utility skills to that same closed core surface.

The conceptual groups are:

- automation: mailbox rounds, ordinary mailbox operations, managed memory, advanced workflow patterns, read-only inspection, managed-agent messaging, and gateway/reminder control
- control: touring, project overlays, specialists, credentials, definitions, live-agent lifecycle, and loop orchestration
- utils: `houmao-utils-llm-wiki` and `houmao-utils-workspace-mgr`

CLI-default installation expands `all`, which installs every packaged Houmao system skill. Managed launch and managed join expand `core`, which installs automation plus control and excludes only the utility workflows.

## When To Use This Surface

Use `system-skills` when:

- you want to prepare an external Claude, Codex, Copilot, or Gemini home before using `houmao-mgr`
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
