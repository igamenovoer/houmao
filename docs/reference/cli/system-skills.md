# system-skills

`houmao-mgr system-skills` is the operator-facing surface for installing, removing, and inspecting the current Houmao-owned `houmao-*` skills in resolved Claude, Codex, Kimi, Gemini, or Copilot homes.

> **Looking for the narrative tour?** See the [System Skills Overview](../../getting-started/system-skills-overview.md) getting-started guide for a 5-minute walkthrough of every packaged skill, when each one fires, and how managed-home auto-install differs from explicit CLI-default install.

This page documents `houmao-mgr system-skills` command behavior: effective-home resolution, named sets, subset skill selection, copy versus symlink projection, status, uninstall, and retired-skill cleanup. When `npx` and internet access are available, users can alternatively install from Houmao's namespace in the small release-synced `igamenovoer/tool-skills` repository with:

```bash
npx skills add igamenovoer/tool-skills/houmao
```

That external Skills CLI path avoids cloning the full Houmao source repository and is adjacent install guidance; the detailed command behavior below applies to `houmao-mgr system-skills`.

Installed Houmao system skills can answer prompt-level read-only help such as `$houmao-touring help` or `$houmao-agent-email-comms help`. That help is handled by the installed skill's top-level `SKILL.md`; it is not a `houmao-mgr system-skills help` subcommand.

This is the same packaged skill system used internally by:

- managed launch or internal native-agent brain build when Houmao creates a managed home and resolves any stored source/profile managed system-skill policy,
- `houmao-mgr agents self join` when it adopts an existing session and auto-installs Houmao-owned skills into the adopted tool home.

The `system-skills` command group is still the explicit tool-home installer. Managed-launch policy is configured on specialists, recipes, and launch profiles with `system_skills` fields or `--system-skill*` profile options; it is not a one-shot `system-skills install` invocation.

The current implementation is still intentionally narrow. It covers the packaged Houmao-owned skills declared in `src/houmao/agents/assets/system_skills/catalog.toml`:

- `houmao-process-emails-via-gateway` for round-oriented gateway mailbox workflow
- `houmao-agent-email-comms` for ordinary shared-mailbox operations and the no-gateway fallback path
- `houmao-adv-usage-pattern` for supported multi-skill mailbox and gateway workflow compositions such as self-wakeup through self-mail plus notifier-driven rounds
- `houmao-utils-workspace-mgr` for explicit multi-agent workspace planning, creation, validation, and summary utilities: dry-run plans, untracked task-scoped in-repo workspace collections, out-of-repo standard workspace layouts, per-agent Git worktrees, local-only shared repos, tracked submodule materialization, launch-profile cwd updates, project-command readiness checks, and optional memo-seed workspace rules
- `houmao-ext-graphing` for extension-owned built-in Plotly.js `templated-graphics` and Vega-Lite `freeform-graphics` authoring, schema discovery, payload validation, implementation rendering, and graphing-specific repair
- `houmao-touring` for a manual guided tour that helps first-time or re-orienting users move through beginner agent creation, intermediate live operation, and advanced loop/workspace coordination when relevant
- `houmao-mailbox-mgr` for mailbox-root lifecycle, mailbox account lifecycle, structural mailbox inspection, and late filesystem mailbox binding on existing local managed agents
- `houmao-memory-mgr` for supported managed-agent memory edits to the fixed `houmao-memo.md` file and contained `pages/` files across relaunch, reset, and `recover_and_continue` flows
- `houmao-project-mgr` for project overlay lifecycle, `.houmao/` layout explanation, project-aware command effects, and project-scoped easy-instance inspection or stop routing
- `houmao-agent-definition` for subcommands `roles`, `recipes`, `launch-dossiers`, `specialists`, `profiles`, `create-agent-fast-forward`, `launch-agent`, and `stop-agent`; `launch-dossiers` maps to the underlying `internals native-agent launch-dossiers ...` CLI, while ordinary profile wording defaults to easy `profiles`
- `houmao-specialist-mgr` as a compatibility wrapper that redirects older specialist/profile/ready-profile prompts to `houmao-agent-definition`
- `houmao-credential-mgr` for project-local credential management plus direct internal native-agent credential management
- `houmao-agent-instance` for live managed-agent instance lifecycle
- `houmao-agent-inspect` for generic read-only managed-agent inspection across liveness, screen posture, mailbox posture, logs, runtime artifacts, and bounded local tmux peeking
- `houmao-operator-messaging` for manual operator intent clarification and dispatch to one or more managed agents by prompt by default, or by mailbox when requested
- `houmao-agent-messaging` for communication and control of already-running managed agents across prompt, gateway, raw-input, mailbox routing, and reset-context workflows
- `houmao-agent-gateway` for live gateway lifecycle, manifest-first discovery, gateway-only control, ranked reminders, and gateway mail-notifier behavior
- `houmao-interop-ag-ui` for AG-UI protocol event validation and framing, generic Houmao implementation rendering, gateway publishing, GUI delivery interpretation, and UI payload safety
- `houmao-agent-loop-lite` for lightweight Markdown/direct-SQL generated loop authoring and execution with typed Markdown templates and generated skills
- `houmao-agent-loop-pro` for schema-rich generated loop authoring and execution across `tree-loop` and `generic-loop` topology modes

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
- Kimi: `KIMI_CODE_HOME`
- Gemini: `GEMINI_CLI_HOME`
- Copilot: `COPILOT_HOME`

Project-scoped default homes:

- Claude: `<cwd>/.claude`
- Codex: `<cwd>/.codex`
- Kimi: `<cwd>/.kimi-code`
- Gemini: `<cwd>`
- Copilot: `<cwd>/.github`

Gemini is intentionally different from Claude and Codex. The effective Gemini home root is the project root, which means omitted-home Gemini installs land under `<cwd>/.gemini/skills/` while Gemini provider state remains under `<cwd>/.gemini/`.

Kimi uses the same home-relative `skills/` projection as Claude and Codex. With the project default, omitted-home Kimi installs land under `<cwd>/.kimi-code/skills/`, which Kimi Code discovers when it runs from that project. Explicit `--home` or `KIMI_CODE_HOME` projections are file-placement, status, and uninstall targets; current Kimi Code does not automatically discover arbitrary `<KIMI_CODE_HOME>/skills` unless `config.toml` includes that path in `extra_skill_dirs`. Managed Kimi brain builds add the managed projected skill root to `extra_skill_dirs` without overwriting unrelated Kimi config, and local-interactive Kimi launches rely on that config rather than receiving a Houmao-injected `--skills-dir`.

Copilot uses the same home-relative `skills/` projection as Claude and Codex, but its project-scoped default home is `<cwd>/.github`. That means omitted-home Copilot installs land under `<cwd>/.github/skills/`. To install the same Houmao-owned skills into a personal Copilot CLI home, pass an explicit home such as `--home ~/.copilot` or set `COPILOT_HOME`; no separate scope flag is required.

## Packaged Catalog

The authoritative packaged catalog lives in the runtime package:

- `src/houmao/agents/assets/system_skills/catalog.toml`
- `src/houmao/agents/assets/system_skills/catalog.schema.json`

The catalog defines four things:

1. `skills`: the current installable Houmao-owned skills
2. `sets`: named sets of explicit skill names
3. `auto_install`: fixed set lists used for managed launch, managed join, and CLI default installation
4. `retired_skill_names`: known retired Houmao-owned projection names that supported install/status/uninstall workflows clean or report, but never install

The catalog is loaded by `src/houmao/agents/system_skills.py`, normalized, validated against the packaged JSON Schema, and then checked for cross-reference errors such as sets that mention unknown skills.

Current sets:

- `core`
- `extensions`
- `all`

Current fixed auto-install selections:

- managed launch: `core`, `extensions`
- managed join: `core`, `extensions`
- CLI default: `all`

Managed launch can override the managed-launch default per source/profile. Source recipes and specialists support `default`, `extend`, `replace`, and `none`; launch profiles support `inherit`, `extend`, `replace`, and `none`. The shared managed-home sync removes unselected current Houmao-owned skill paths from reused managed homes and leaves unrelated user skills alone.

## Current Skill Inventory

The current packaged Houmao-owned skills are:

- `houmao-process-emails-via-gateway`
- `houmao-agent-email-comms`
- `houmao-adv-usage-pattern`
- `houmao-utils-workspace-mgr`
- `houmao-ext-graphing`
- `houmao-touring`
- `houmao-mailbox-mgr`
- `houmao-memory-mgr`
- `houmao-project-mgr`
- `houmao-specialist-mgr` (compatibility wrapper; canonical specialist/profile guidance is `houmao-agent-definition`)
- `houmao-credential-mgr`
- `houmao-agent-definition`
- `houmao-agent-loop-pro`
- `houmao-agent-loop-lite`
- `houmao-agent-instance`
- `houmao-agent-inspect`
- `houmao-operator-messaging`
- `houmao-agent-messaging`
- `houmao-agent-gateway`
- `houmao-interop-ag-ui`

These skill trees live directly under:

- `src/houmao/agents/assets/system_skills/<houmao-skill>/`

## Tool-Visible Projection Paths

The installer preserves the current visible tool-native skill roots with flat Houmao-owned skill directories:

| Tool | Visible projection root | Example |
| --- | --- | --- |
| `claude` | `skills/` | `skills/houmao-agent-email-comms/SKILL.md` |
| `codex` | `skills/` | `skills/houmao-agent-messaging/SKILL.md` |
| `kimi` | `skills/` | `.kimi-code/skills/houmao-agent-email-comms/SKILL.md` for the project default, or `<KIMI_CODE_HOME>/skills/houmao-agent-email-comms/SKILL.md` with env redirection |
| `gemini` | `.gemini/skills/` | `.gemini/skills/houmao-agent-email-comms/SKILL.md` |
| `copilot` | `skills/` | `.github/skills/houmao-agent-messaging/SKILL.md` for the project default, or `~/.copilot/skills/houmao-agent-messaging/SKILL.md` with `--home ~/.copilot` |

That means Houmao-owned skills stay grouped by reserved skill names and closed named sets rather than by family-specific path segments.

## Human-Readable Projection Output

Plain `install`, `status`, and `uninstall` output distinguishes the effective tool home from the skill projection location. The effective home is the root used for tool-home resolution and later status/uninstall targeting. The projection location is where Houmao-owned skill directories actually appear under that home.

For Claude, Codex, Kimi, and Copilot, the projection root is usually `<effective-home>/skills/`. For Gemini, the effective home may be the project root while the projection root is `<effective-home>/.gemini/skills/`. For example, if omitted-home Gemini resolution chooses `/workspace/repo`, the installed Houmao-owned Gemini skill files live under `/workspace/repo/.gemini/skills/`.

Kimi plain output also prints a discovery caveat. It reports where files were projected, but it does not claim that an arbitrary explicit Kimi home's `skills/` directory is automatically visible to Kimi Code unless that home's `config.toml` includes the path in `extra_skill_dirs`.

The plain output reports projection roots or projected paths so an operator can locate installed, discovered, removed, or absent skill paths without switching to JSON output.

## Stateless Selected-Skill Replacement

The shared installer does not create or require `.houmao/system-skills/install-state.json` in target tool homes.

For each selected current Houmao-owned skill, reinstall computes the exact current tool-native destination path, removes that path if it already exists as a directory, file, or symlink, and then projects the packaged skill with the requested mode.

Replacement policy:

- selected current Houmao-owned skill paths are explicit overwrite targets
- exact known retired skill projection paths, including old loop names and `houmao-utils-graphing`, are removed from the selected target home during install/reinstall
- copied projection materializes the packaged skill tree into the selected destination
- symlink projection replaces the selected destination with a directory symlink to the packaged asset root
- unselected skill directories, parent skill roots, legacy family-namespaced paths, unrelated tool-home content, and stale install-state files are not removed
- old install-state files are ignored rather than migrated

## Stateless All-Known-Skill Removal

`system-skills uninstall` uses the same catalog and projection rules, but it is intentionally not selective. It targets every current Houmao-owned skill listed in the packaged catalog for the resolved tool home.

Removal policy:

- every current catalog-known Houmao-owned skill path is an explicit removal target
- every known retired skill projection path, including old loop names and `houmao-utils-graphing`, is also an explicit removal target
- copied directories, symlinks, and files at those exact current paths are removed
- missing current skill paths are reported as absent rather than errors
- missing retired projection paths are reported separately from current absent skills
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
pixi run houmao-mgr system-skills status --tool kimi
pixi run houmao-mgr system-skills status --tool kimi --home ~/.kimi-code
```

`status` reports:

- target tool
- resolved target home
- installed current Houmao-owned skill names discovered in that home
- the projected relative path for each discovered current skill
- the inferred projection mode for each installed current skill (`copy` or `symlink`)
- retired loop skill leftovers when exact known retired projection paths are still present

If the home has never been touched by the shared installer, `status` reports no installed current Houmao-owned skills. `status` discovers current packaged skill paths and retired leftovers from the filesystem and ignores old install-state files.

## `install`

Use `install` when you want the current Houmao-owned skill surface in a resolved external or project-scoped tool home:

```bash
pixi run houmao-mgr system-skills install --tool codex
pixi run houmao-mgr system-skills install --tool claude,codex,kimi,gemini,copilot
pixi run houmao-mgr system-skills install --tool codex --home ~/.codex
pixi run houmao-mgr system-skills install --tool codex --home ~/.codex --skill-set core
pixi run houmao-mgr system-skills install --tool codex --home ~/.codex --skill-set extensions
pixi run houmao-mgr system-skills install --tool codex --home ~/.codex --skill-set all
pixi run houmao-mgr system-skills install --tool copilot
pixi run houmao-mgr system-skills install --tool copilot --home ~/.copilot
pixi run houmao-mgr system-skills install --tool copilot --home ~/.copilot --skill-set core
pixi run houmao-mgr system-skills install --tool gemini --skill-set core
pixi run houmao-mgr system-skills install --tool kimi
pixi run houmao-mgr system-skills install --tool kimi --skill-set core
pixi run houmao-mgr system-skills install --tool kimi --home ~/.kimi-code
pixi run houmao-mgr system-skills install --tool codex --skill houmao-utils-workspace-mgr
pixi run houmao-mgr system-skills install --tool codex --skill houmao-ext-graphing
pixi run houmao-mgr system-skills install --tool codex --home ~/.codex --skill houmao-agent-definition --symlink
```

Selection rules:

- omitting both `--skill-set` and `--skill` expands the catalog's CLI-default set list
- the CLI-default set list is `all`; managed launch and join resolve `core` plus `extensions`
- use `--skill-set core` when you want the non-extension baseline without extension skills
- use `--skill-set extensions` when you want only default-installed extension skills such as `houmao-ext-graphing`
- repeatable `--skill-set` expands named sets in the order given
- repeatable `--skill` appends explicit skill names after the expanded sets, and can also be used alone for a small named subset
- `--symlink` switches the install from copied projection to directory symlink projection
- the final skill list is deduplicated by first occurrence
- unknown set names or skill names are errors
- `--set` is no longer a supported install flag; use `--skill-set` for named system-skill sets

Home-resolution rules:

- `--home` is optional for single-tool install commands
- `--home` cannot be combined with comma-separated multi-tool install commands
- when omitted, the command resolves the effective home using tool-native env redirection first and project-scoped defaults second
- omitted-home Gemini installs use the project root as the effective home, so Houmao-owned skills land under `.gemini/skills/`
- omitted-home Kimi installs use `<cwd>/.kimi-code` as the effective home, so Houmao-owned skills land under `.kimi-code/skills/`

Structured output rules:

- single-tool JSON output keeps the existing scalar payload shape with `tool`, `home_path`, `selected_sets`, `explicit_skills`, `resolved_skills`, `projected_relative_dirs`, and `projection_mode`
- multi-tool JSON output returns `tools` plus one single-tool-shaped record per selected tool under `installations`

Plain output rules:

- single-tool output reports the effective home plus the installed projected skill path or projection root
- multi-tool output reports each selected tool's effective home plus skill projection root
- Gemini output reports `.gemini/skills` paths rather than implying that skills were installed directly into the effective home root
- Kimi output reports the projected `skills/` path and includes the discovery caveat for explicit or env-redirected Kimi homes

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
pixi run houmao-mgr system-skills uninstall --tool claude,codex,kimi,gemini,copilot
pixi run houmao-mgr system-skills uninstall --tool copilot --home ~/.copilot
pixi run houmao-mgr system-skills uninstall --tool gemini
pixi run houmao-mgr system-skills uninstall --tool kimi
pixi run houmao-mgr system-skills uninstall --tool kimi --home ~/.kimi-code
```

Uninstall rules:

- `uninstall` always targets every current skill in the packaged catalog
- selection flags such as `--skill`, `--skill-set`, `--set`, `--default`, and `--symlink` are not part of the uninstall surface
- `--home` is optional for single-tool uninstall commands
- `--home` cannot be combined with comma-separated multi-tool uninstall commands
- when omitted, the command resolves the effective home using tool-native env redirection first and project-scoped defaults second
- omitted-home Gemini uninstalls use the project root as the effective home, so Houmao-owned skills are removed from `.gemini/skills/`
- omitted-home Kimi uninstalls use `<cwd>/.kimi-code` as the effective home, so Houmao-owned skills are removed from `.kimi-code/skills/`

Structured output rules:

- single-tool JSON output uses scalar `tool` and `home_path` fields and reports `removed_skills`, `removed_projected_relative_dirs`, `absent_skills`, and `absent_projected_relative_dirs`
- multi-tool JSON output returns `tools` plus one single-tool-shaped record per selected tool under `uninstallations`

Plain output rules:

- single-tool output reports the effective home plus removed or absent projected paths
- multi-tool output reports each selected tool's effective home plus removed or absent projection roots when paths share a root
- Gemini output reports `.gemini/skills` removal or absence paths rather than implying that current Houmao-owned skills were removed directly from the effective home root
- Kimi output reports `skills/` removal or absence paths and repeats the discovery caveat for explicit or env-redirected Kimi homes

Removal boundary:

- exact current Houmao-owned skill paths are removed whether they are copied directories, symlinks, or files
- missing current paths are reported as absent or skipped
- missing homes are not created
- parent skill roots, unrelated user skills, unrecognized `houmao-*` paths, legacy family-namespaced paths, and obsolete install-state files are preserved

## Internal Auto-Install Behavior

Managed homes and joined homes use the same installer and catalog:

- managed launch and internal native-agent brain build install the skill list resolved from `auto_install.managed_launch_sets`
- `agents self join` installs the skill list resolved from `auto_install.managed_join_sets`
- `agents self join --no-install-houmao-skills` skips that default installer step

Those managed flows continue to use copied projection in this change even though explicit `system-skills install` now supports `--symlink`.

This removes the old mailbox-only special path and family-specific Codex subtrees while keeping logical grouping in the `core`, `extensions`, and `all` sets. The smaller `core` set is the non-extension baseline. The `extensions` set contains default-installed extension guidance that users can ignore without breaking non-extension skill behavior. Non-extension skills do not route, delegate, or require work through extension skills.

The conceptual groups are:

- automation: mailbox rounds, ordinary mailbox operations, managed memory, advanced workflow patterns, read-only inspection, operator messaging, managed-agent messaging, and gateway/reminder control
- control: touring, project overlays, agent definitions and profiles, credentials, live-agent lifecycle, and loop orchestration
- utils: `houmao-utils-workspace-mgr`
- extensions: `houmao-ext-graphing`

CLI-default installation expands `all`, which installs every packaged Houmao system skill. Managed launch and managed join expand `core` followed by `extensions`, so extension skills are available by default without becoming core dependencies. Explicit `--skill-set core` excludes `houmao-ext-graphing`.

## When To Use This Surface

Use `system-skills` when:

- you want to prepare an external Claude, Codex, Kimi, Gemini, or Copilot home before using `houmao-mgr`
- you want to inspect whether Houmao already installed its own skill set into a home
- you want the same Houmao-owned guided touring, project-management, mailbox administration, ordinary mailbox participation, low-level definition-management, specialist-management, credential-management, managed-agent inspection, operator message clarification/dispatch, messaging/control, gateway-management, graphing authoring, AG-UI delivery, loop/workspace coordination, or instance-lifecycle skill surface outside a Houmao-managed launch or join flow

Do not use it for:

- project-local user skills under `.houmao/agents/`
- specialists or recipe-selected project skills
- mailbox registration itself; that still uses `houmao-mgr mailbox ...`, `houmao-mgr agents single ... mailbox ...`, or `houmao-mgr agents self mailbox ...`

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
