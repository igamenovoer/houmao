# houmao-mgr

Houmao manager CLI for local projects and managed-agent workflows.

`houmao-mgr` is the primary management CLI for local lifecycle, managed agents, mailbox administration, packaged Houmao-owned system-skill installation, repo-local project overlays, and administrative tasks. API-backed coordination is handled by `houmao-passive-server`.

## Synopsis

```
houmao-mgr [--version] [--print-plain | --print-json | --print-fancy] COMMAND [ARGS]...
```

The root help surface for `houmao-mgr --help` and bare `houmao-mgr` invocation includes a direct pointer to the published detailed docs site at `https://igamenovoer.github.io/houmao/`.

## Root Options

| Option | Description |
|---|---|
| `--version` | Print the packaged Houmao version and exit successfully without requiring a subcommand. |
| `--print-plain` | Human-readable aligned text (default). |
| `--print-json` | Machine-readable JSON with stable formatting (`indent=2`, `sort_keys=True`). |
| `--print-fancy` | Rich-formatted output with tables, panels, and colors (requires a terminal that supports ANSI escape codes). |

`--version` is a root CLI reporting option. It prints the packaged Houmao version for the current `houmao-mgr` binary and exits successfully without running a subcommand.

## Output Style

All `houmao-mgr` commands support three output modes controlled by root-level flags:

| Flag | Description |
|---|---|
| `--print-plain` | Human-readable aligned text (default). |
| `--print-json` | Machine-readable JSON with stable formatting (`indent=2`, `sort_keys=True`). |
| `--print-fancy` | Rich-formatted output with tables, panels, and colors (requires a terminal that supports ANSI escape codes). |

The flags are mutually exclusive. When none is provided, the `HOUMAO_CLI_PRINT_STYLE` environment variable selects the active mode. Valid values are `plain`, `json`, and `fancy` (case-insensitive). When neither a flag nor the environment variable is set, the default is `plain`.

Resolution precedence: explicit CLI flag → `HOUMAO_CLI_PRINT_STYLE` → `plain`.

Scripts and automation that previously relied on JSON-by-default output must add `--print-json` or set `HOUMAO_CLI_PRINT_STYLE=json` to preserve machine-readable output.

## Command Groups

### `admin` — Administrative commands

```
houmao-mgr admin [OPTIONS] COMMAND [ARGS]...
```

Administrative utilities for the Houmao environment.

For dedicated coverage, see [admin cleanup](admin-cleanup.md).

The canonical cleanup tree is `houmao-mgr admin cleanup registry` plus `houmao-mgr admin cleanup runtime {sessions,builds,logs,mailbox-credentials}`. Registry cleanup probes tmux-backed records locally by default and accepts `--no-tmux-check` for lease-only cleanup. Human-oriented cleanup output prints each populated action bucket line by line; use `--print-json` when you need the structured payload.

### `agents` — Scoped managed-agent operations

```
houmao-mgr agents [OPTIONS] COMMAND [ARGS]...
```

`agents` is a namespace with four explicit scopes. The root no longer exposes direct action commands such as `launch`, `list`, `join`, `prompt`, `gateway`, `mail`, `mailbox`, `turn`, `cleanup`, `stop`, or `relaunch`.

For dedicated coverage of complex nested command families, see:

- [agents gateway](agents-gateway.md) - `agents single ... gateway` and `agents self gateway`
- [agents external](agents-external.md) - external-agent registry/reference onboarding
- [agents turn](agents-turn.md) - `agents single ... turn` and `agents self turn`
- [agents mail](agents-mail.md) - `agents single ... mail` and `agents self mail`
- [agents mailbox](agents-mailbox.md) - `agents single ... mailbox` and `agents self mailbox`

#### Subcommands

| Subcommand | Description |
|---|---|
| `global` | Zero-or-many local managed-agent registry/fleet operations. Maintained command: `list`. |
| `single --agent-id <id>` | Exactly one explicitly selected local managed-agent identity by authoritative id. |
| `single --agent-name <name>` | Exactly one explicitly selected local managed-agent identity by friendly name. |
| `self` | Exactly one current managed agent: the caller's registered tmux session. Includes current-session adoption through `join`. |
| `external` | External-agent registry/reference onboarding: `register`, `list`, `get`, `verify`, and `remove`. External lifecycle stays with the remote owner. |

#### Target Cardinality And Authority

- `agents global` does not target exactly one agent and does not accept `--agent-id` or `--agent-name`. `agents global list` reads the shared local registry and may include local managed agents from multiple project overlays.
- `agents single` requires exactly one group-level selector, either `--agent-id <id>` or `--agent-name <name>`. Nested commands consume that group selector; leaf commands do not repeat it.
- `agents single` does not fall back to the current tmux session. Use `agents self ...` for the current managed session.
- `agents single` owns selected-agent lifecycle controls: `state`, `prompt`, `interrupt`, `stop`, `relaunch`, `gateway`, `mail`, `mailbox`, `memory`, `turn`, and `cleanup`.
- `agents single relaunch` has selected-agent recovery authority. It may refresh an active tmux-backed surface, revive stopped relaunchable records, and recover degraded or stale active records where the runtime supports those paths.
- `agents self join` adopts the current tmux session as one managed-agent identity. `join` may accept identity creation fields such as `--agent-name`; those fields do not select another existing agent.
- `agents self` follow-up commands resolve the target from the caller's current managed tmux session and do not accept `--agent-id`, `--agent-name`, or `--current-session`.
- `agents self` exposes `identity`, `state`, `prompt`, `interrupt`, `relaunch`, `gateway`, `mail`, `mailbox`, `memory`, and `turn`. It intentionally does not expose `stop` or `cleanup`.
- `agents self relaunch` is active-current-session refresh only. Selected-agent stopped-record revival and degraded/stale recovery remain under `agents single --agent-id <id> relaunch` or `agents single --agent-name <name> relaunch`.
- `agents external` manages remotely owned or communication-only references. It does not expose local lifecycle commands such as `prompt`, `interrupt`, `stop`, `relaunch`, `gateway`, `turn`, or `cleanup` under the `external` group.

Managed-agent birth is source-scoped. Public project-backed launch is `houmao-mgr project [--project-dir <dir>] agents launch --specialist <name>` or `houmao-mgr project [--project-dir <dir>] agents launch --profile <name>`. Root/global/single `agents launch` paths are not maintained public commands.

#### Common Scoped Paths

| Intent | Maintained path |
|---|---|
| List local managed agents across project overlays | `houmao-mgr agents global list` |
| Inspect one selected agent | `houmao-mgr agents single --agent-id <id> state` |
| Prompt one selected agent | `houmao-mgr agents single --agent-name <name> prompt --prompt <text>` |
| Prompt the current managed session | `houmao-mgr agents self prompt --prompt <text>` |
| Stop one selected agent | `houmao-mgr agents single --agent-id <id> stop` |
| Relaunch one selected stopped/degraded agent | `houmao-mgr agents single --agent-id <id> relaunch` |
| Refresh the current managed session | `houmao-mgr agents self relaunch` |
| Adopt the current tmux session | `houmao-mgr agents self join --agent-name <name>` |
| Selected-agent gateway operation | `houmao-mgr agents single --agent-id <id> gateway status` |
| Current-session gateway operation | `houmao-mgr agents self gateway status` |
| Selected-agent mail operation | `houmao-mgr agents single --agent-name <name> mail read --message-ref <ref>` |
| Current-session mail operation | `houmao-mgr agents self mail read --message-ref <ref>` |
| Selected-agent mailbox binding | `houmao-mgr agents single --agent-name <name> mailbox register` |
| Current-session mailbox binding | `houmao-mgr agents self mailbox status` |
| Selected-agent headless turn | `houmao-mgr agents single --agent-id <id> turn submit --prompt <text>` |
| Current-session headless turn inspection | `houmao-mgr agents self turn status <turn-id>` |
| Selected-agent cleanup | `houmao-mgr agents single --agent-id <id> cleanup session --dry-run` |
| Register an external reference | `houmao-mgr agents external register --name <local-name> --api-base-url <url> --agent-ref <remote-ref>` |
| Project-backed launch | `houmao-mgr project agents launch --profile <name>` |

#### Migration Examples

| Old ambiguous path | New maintained path |
|---|---|
| `houmao-mgr agents list` | `houmao-mgr agents global list` |
| `houmao-mgr agents stop --agent-id <id>` | `houmao-mgr agents single --agent-id <id> stop` |
| `houmao-mgr agents prompt --agent-name <name> --prompt <text>` | `houmao-mgr agents single --agent-name <name> prompt --prompt <text>` |
| `houmao-mgr agents join --agent-name <name>` | `houmao-mgr agents self join --agent-name <name>` |
| `houmao-mgr agents prompt --prompt <text>` from inside the managed session | `houmao-mgr agents self prompt --prompt <text>` |
| `houmao-mgr agents interrupt` from inside the managed session | `houmao-mgr agents self interrupt` |
| `houmao-mgr agents relaunch` from inside the managed session | `houmao-mgr agents self relaunch` |
| `houmao-mgr agents gateway prompt --agent-id <id> --prompt <text>` | `houmao-mgr agents single --agent-id <id> gateway prompt --prompt <text>` |
| `houmao-mgr agents gateway prompt --prompt <text>` from inside the managed session | `houmao-mgr agents self gateway prompt --prompt <text>` |
| `houmao-mgr agents mail read --message-ref <ref>` from inside the managed session | `houmao-mgr agents self mail read --message-ref <ref>` |
| `houmao-mgr agents launch --launch-profile <name>` | `houmao-mgr project [--project-dir <dir>] agents launch --profile <name>` |
| `houmao-mgr agents external register ...` | unchanged: `houmao-mgr agents external register ...` |

#### Gateway, Mail, Mailbox, Memory, And Turn

Gateway commands live under both selected-agent and current-session surfaces: `agents single --agent-id <id> gateway ...`, `agents single --agent-name <name> gateway ...`, and `agents self gateway ...`. The gateway family includes `attach`, `detach`, `status`, `prompt`, `interrupt`, `send-keys`, `tui state|history|watch|note-prompt`, `mail-notifier status|enable|disable`, and `reminders list|get|create|set|remove`. The single surface is explicit selected-agent authority; the self surface is current-session authority and does not expose explicit selectors.

Mail commands also live under both selected-agent and current-session surfaces. The maintained subcommands are `resolve-live`, `status`, `list`, `peek`, `read`, `send`, `post`, `reply`, `mark`, `move`, and `archive`. `resolve-live` returns structured mailbox binding data plus optional `gateway.base_url`; mailbox-specific shell export is not part of the supported contract. Verified pair-owned and manager-owned execution returns authoritative results, while local live-TUI fallback is non-authoritative submission-only. Use `status`, `list`, gateway `/v1/mail/*`, filesystem mailbox inspection, or transport-native mailbox state to verify non-authoritative outcomes.

Mailbox commands (`register`, `unregister`, and `status`) update or inspect late filesystem mailbox bindings for an existing managed agent. Selected-agent binding uses `agents single --agent-name <name> mailbox ...`; current-session binding uses `agents self mailbox ...`.

Memory commands live under `agents single ... memory ...` and `agents self memory ...`. The memo is a free-form `houmao-memo.md` file; page writes under `pages/` do not edit it. Use the scoped `memory resolve --path <page>` command to return page-relative, memo-relative, absolute, existence, and kind data when an operator or agent wants to author a link manually.

Headless turn commands live under `agents single ... turn ...` and `agents self turn ...`. The submit path accepts request-scoped `--model` and `--reasoning-level` overrides for that turn only; they do not rewrite stored manifests, profiles, specialists, or future turns.

Cleanup is selected-agent lifecycle authority and is maintained under `agents single ... cleanup session|logs|mailbox`. `agents self cleanup` is not a maintained public path.

### `mailbox` — Local filesystem mailbox administration

```
houmao-mgr mailbox [OPTIONS] COMMAND [ARGS]...
```

Local operator commands for filesystem mailbox roots and address lifecycle. This surface does not require a running server.

#### Subcommands

| Subcommand | Description |
|---|---|
| `init` | Bootstrap or validate one filesystem mailbox root. |
| `status` | Inspect mailbox-root health plus active, inactive, and stashed registration counts. |
| `register` | Create or reuse one filesystem mailbox registration for a full mailbox address. |
| `unregister` | Deactivate or purge one filesystem mailbox registration. |
| `accounts list|get` | Inspect mailbox registrations as operator-facing mailbox accounts. |
| `messages list|get` | Inspect structural message projections for one registered mailbox address. |
| `repair` | Rebuild one filesystem mailbox root's shared index state locally. |
| `cleanup` | Remove inactive or stashed mailbox registrations while preserving active registrations and canonical `messages/` history. |
| `clear-messages` | Clear delivered message content and derived message state while preserving mailbox registrations. |
| `export` | Export selected mailbox accounts and indexed messages into a portable archive directory. |

`mailbox register` keeps the existing `safe`, `force`, and `stash` mode vocabulary. When a requested registration would replace existing durable mailbox state or an occupying mailbox entry artifact, the command prompts before destructive replacement on interactive terminals and accepts `--yes` for non-interactive overwrite confirmation.

`mailbox messages list|get` is structural inspection over canonical message metadata plus address-scoped projection metadata. Participant-local mutable state such as `read`, `starred`, `archived`, and `deleted` belongs on actor-scoped `houmao-mgr agents single ... mail ...` or `houmao-mgr agents self mail ...` workflows rather than this operator/admin surface.

`mailbox clear-messages` is the destructive whole-root message reset. It clears delivered filesystem mail, message projections, mailbox-local message/thread state, and mailbox-owned managed-copy attachments while preserving mailbox registrations and account directories. Use `--dry-run` to preview and `--yes` for non-interactive confirmation; external `path_ref` attachment targets are not deleted.

`mailbox export` is the maintained archive path for filesystem mailbox roots. It requires `--output-dir <dir>` plus an explicit account scope: either `--all-accounts` or one or more `--address <full-address>` values. The output directory must not already exist. The default `--symlink-mode materialize` writes regular files and directories, including materialized projection links and symlink-backed private account directories, and verifies the archive contains no symlinks. Use `--symlink-mode preserve` only when you explicitly want archive-internal relative projection symlinks and the target filesystem supports symlink creation. The archive root contains `manifest.json`, canonical messages under `messages/`, selected account metadata and mailbox-local state under `accounts/`, and copied mailbox-owned managed-copy attachments under `attachments/managed/`; external `path_ref` targets are recorded in the manifest instead of copied. Prefer this command over raw recursive mailbox-root copying when preparing an archive.

Direct brain-build and direct native-agent credential CRUD are internal native-agent plumbing. The maintained direct paths are documented under [`internals`](internals.md):

```text
houmao-mgr internals native-agent brain build --native-agent-root <path> ...
houmao-mgr internals native-agent credentials <tool> <verb> --native-agent-root <path> ...
```

Ordinary project users manage credentials through `houmao-mgr project [--project-dir <dir>] credentials <tool> ...` and launch through `houmao-mgr project agents launch`.

### `system-skills` — Packaged Houmao-owned skill management for resolved tool homes

```
houmao-mgr system-skills [OPTIONS] COMMAND [ARGS]...
```

Install, remove, or inspect the packaged current Houmao-owned `houmao-*` skill set for resolved Claude, Codex, Copilot, or Gemini homes.

#### Subcommands

| Subcommand | Description |
|---|---|
| `list` | Show the packaged skill inventory, named sets, and fixed auto-install set lists. |
| `status` | Show which current Houmao-owned system skills are installed in one resolved tool home by scanning the live filesystem. |
| `install` | Install the CLI-default set list, explicit named skill sets, explicit skills, or any combination of those into one or more resolved tool homes. |
| `uninstall` | Remove all current catalog-known Houmao system skills from one or more resolved tool homes. |

Operational notes:

- `system-skills install` requires `--tool`; the value may be one supported tool or a comma-separated list such as `claude,codex,copilot,gemini`
- `system-skills uninstall` also requires `--tool` and accepts the same single-tool or comma-separated tool syntax
- `system-skills install --home` and `system-skills uninstall --home` are valid only when `--tool` names one tool; comma-separated multi-tool operations resolve each home independently
- `system-skills status` requires `--tool` and accepts optional `--home`
- when `--home` is omitted, the effective home resolves with precedence tool-native home env var (`CLAUDE_CONFIG_DIR`, `CODEX_HOME`, `COPILOT_HOME`, `GEMINI_CLI_HOME`), then the project-scoped default home
- the project-scoped defaults are `<cwd>/.claude` for Claude, `<cwd>/.codex` for Codex, `<cwd>/.github` for Copilot, and `<cwd>` for Gemini
- omitting both `--skill-set` and `--skill` selects the packaged CLI-default set list
- repeatable `--skill-set` expands named system-skill sets; `--set` is no longer a supported install flag
- optional `--symlink` installs the selected packaged skills as absolute-target directory symlinks instead of copied trees
- `system-skills uninstall` does not accept install-selection flags; it removes all current known Houmao skill paths for the resolved home
- repeated skill sets expand in order, explicit skills append after sets, and the final list is deduplicated by first occurrence
- the installer preserves flat visible Houmao-owned skill paths: Claude, Codex, and Copilot use `skills/houmao-...`, and Gemini uses `.gemini/skills/houmao-...`
- uninstall removes exact current Houmao skill paths and preserves unrelated user skills, parent roots, legacy paths, and obsolete install-state files
- `status` discovers current packaged skill paths in the resolved home; `install` replaces selected current Houmao-owned skill destinations directly without install-state ownership checks
- managed brain build and `agents self join` use the same packaged catalog internally; `agents self join` keeps the fixed managed-join selection, while managed brain build may use stored source/profile managed system-skill policy instead of the plain managed-launch default

For the detailed catalog, projection, and ownership contract, see [system-skills](system-skills.md).

Startup note:

- `houmao-mgr` builds one root Click command tree at process startup, so a stale import in any registered command group can block `houmao-mgr --version`, root help, and unrelated subcommands before dispatch

### `project` — Repo-local Houmao project overlays

```
houmao-mgr project [OPTIONS] COMMAND [ARGS]...
```

Local operator workflow for bootstrapping, inspecting, authoring, and launching from one Houmao project. By default project commands discover the nearest initialized `.houmao/` overlay from the current working directory. Use `houmao-mgr project --project-dir <dir> ...` to select a human-facing project directory explicitly; the selected overlay root is `<dir>/.houmao`.

Group options:

| Option | Description |
|---|---|
| `--project-dir DIRECTORY` | Human-facing project directory. Resolves the project overlay as `<project-dir>/.houmao` and applies to every nested project subcommand. |

Command shape:

```text
houmao-mgr project
├── init | status | migrate
├── skills
│   ├── add | set | list | get | remove
├── credentials <tool>
│   ├── list | get | add | set | login | rename | remove
├── specialist
│   ├── create | set | list | get | remove
├── profile
│   ├── create | set | list | get | remove
├── agents
│   ├── launch | stop | list | get
└── mailbox
    ├── init | status | register | unregister | repair | cleanup
    ├── accounts list|get
    └── messages list|get
```

#### Subcommands

| Subcommand | Description |
|---|---|
| `init` | Create or validate the selected overlay root, default `<pwd>/.houmao`, write `houmao-config.toml`, write `.gitignore`, create `catalog.sqlite`, and create managed `content/` roots. |
| `status` | Report whether a project overlay was discovered under the selected overlay root, which catalog was found, and which agent-definition root is effective. |
| `migrate` | Inspect or apply one supported project-structure migration into the current overlay layout. |
| `skills` | Maintain canonical project-local custom skills under `.houmao/content/skills/`. |
| `credentials` | Manage project-backed credentials for Claude, Codex, and Gemini in the selected project overlay. |
| `specialist` | Higher-level specialist workflow persisted in `.houmao/catalog.sqlite` with file-backed payloads under `.houmao/content/`. |
| `profile` | Specialist-backed reusable project profiles. |
| `agents` | Launch, inspect, and stop project-managed agents from specialists or profiles. |
| `mailbox` | Project-scoped wrapper over the generic mailbox-root CLI targeting `mailbox/` under the active overlay root. |

Project overlay notes:

- `project init` bootstraps `<pwd>/.houmao` by default.
- `project --project-dir /repo init` bootstraps `/repo/.houmao` even when invoked from another directory.
- `project --project-dir /repo status` reports `/repo/.houmao` with `overlay_root_source: project_dir` and does not use cwd discovery.
- `HOUMAO_PROJECT_OVERLAY_DIR=/abs/path` selects `/abs/path` as the overlay root directly and must be absolute.
- `HOUMAO_PROJECT_OVERLAY_DISCOVERY_MODE=ancestor` is the default ambient lookup mode; `cwd_only` restricts ambient lookup to `<pwd>/.houmao/houmao-config.toml`.
- The selected overlay root gets a local `.gitignore` containing `*`, so the whole overlay stays local-only without editing the repo root `.gitignore`.
- Without `--project-dir`, `project status` resolves the active overlay root from `HOUMAO_PROJECT_OVERLAY_DIR` first, then ambient discovery under `HOUMAO_PROJECT_OVERLAY_DISCOVERY_MODE`, and reports the effective discovery mode in its JSON payload.
- `project status` also reports a `migration` payload when an overlay is present so operators can tell whether legacy structure still needs explicit conversion.
- `project init` creates `catalog.sqlite` plus managed `content/prompts/`, `content/auth/`, `content/skills/`, and `content/setups/` under the selected overlay root.
- `project init` does not create `agents/`, `mailbox/`, or `easy/` under the selected overlay root by default.
- `project skills add|set|list|get|remove` is the maintained project-local custom-skill registry. Canonical custom-skill storage lives under `.houmao/content/skills/`; `.houmao/agents/skills/` is derived projection only. Operator-provided source directories are treated as read-only inputs.
- `project migrate` is the explicit upgrade path for supported older overlay layouts. Ordinary project commands do not silently migrate known legacy specialist metadata or compatibility-tree-first project skills in place.

#### `project skills`

`project skills` manages the canonical project-local skill registry rooted at `.houmao/content/skills/`.

| Subcommand | Description |
|---|---|
| `add` | Register one new project skill from a source directory. |
| `set` | Replace the source binding and storage mode for an existing project skill. |
| `list` | List registered project skills. |
| `get` | Inspect one registered project skill, including canonical and derived projection paths. |
| `remove` | Remove one unreferenced project skill registration. |

`project skills` notes:

- `add` and `set` require `--name` plus `--source <dir>` pointing at a skill directory containing `SKILL.md`. Houmao reads from that source directory but must not delete, move, or rewrite it.
- `--mode copy|symlink` controls the canonical project binding. `copy` is the default and snapshots the source tree into `.houmao/content/skills/<name>`. `symlink` makes `.houmao/content/skills/<name>` a symlink to the source directory.
- Successful `add|set|remove` rematerializes `.houmao/agents/skills/<name>` as derived symlinks from the canonical project registry. Operators should treat `.houmao/agents/skills/` as compatibility projection only, not as hand-edited project state.
- `remove` fails clearly while any specialist still references the target skill name.

#### `project migrate`

`project migrate` is the only supported writer for legacy-to-current project-structure upgrades.

| Option | Description |
|---|---|
| _none_ | Show the detected migration plan without mutating the overlay. |
| `--apply` | Apply the supported migration plan in place. |

`project migrate` notes:

- The command targets the active overlay selected through `HOUMAO_PROJECT_OVERLAY_DIR` or ambient discovery.
- Successful apply rewrites supported legacy project structure into the current catalog-backed layout and removes the replaced legacy files after import.
- Ordinary `project`, `project`, and catalog-backed workflows do not silently upgrade known legacy easy-specialist metadata or compatibility-tree-first project skills in place.
- Unsupported legacy layouts fail with explicit guidance instead of partial mutation.

#### `project agents`

`project agents` is the low-level maintenance surface for the compatibility projection tree under `agents/` in the active overlay root.

| Subcommand | Description |
|---|---|
| `roles list|get|init|set|remove` | Inspect, create, update, or delete prompt-only role roots under `agents/roles/`. Use `roles get --include-prompt` when you explicitly need prompt text in CLI output. |
| `recipes list|get|add|set|remove` | **Canonical** low-level recipe administration. Manages named recipe files projected under `agents/presets/<name>.yaml`, including role selection, tool lane, skills, prompt mode, and selected auth bundle reference. |
| `presets list|get|add|set|remove` | Compatibility alias for `recipes`. Operates on the same files under `agents/presets/<name>.yaml` and accepts the same flags. |
| `launch-profiles list|get|add|set|remove` | Manage explicit recipe-backed reusable birth-time launch profiles projected under `agents/launch-profiles/<name>.yaml`. See the dedicated section below for the field set. |
| `tools <tool> get` | Inspect one tool subtree, including adapter, setup, and auth bundle summaries. |
| `tools <tool> setups list|get|add|remove` | Inspect or clone setup bundles under `agents/tools/<tool>/setups/`. |

Low-level boundary notes:

- `roles ...` owns the canonical low-level role prompt.
- `recipes ...` (canonical) and `presets ...` (compatibility alias) own named recipe structure, including role selection, tool lane, skills, prompt mode, and selected auth bundle reference. Both surfaces administer the same `.houmao/agents/presets/<name>.yaml` files.
- `launch-profiles ...` owns reusable recipe-backed birth-time launch configuration, including managed-agent identity defaults, working directory, auth override by display name, prompt-mode override, durable env records, declarative mailbox config, launch posture, an optional prompt overlay, an optional gateway mail-notifier appendix default, and an optional memo seed. The stored auth relationship resolves through auth-profile identity, so later auth rename does not break existing launch profiles. For the shared semantic model that ties these to project profiles, see [Launch Profiles](../../getting-started/launch-profiles.md).
- Managed launches prepend a short Houmao-owned prompt header by default. `houmao-mgr` is the canonical direct Houmao interface named by that header, and the stored launch-profile policy plus launch-time flags determine whether the header is enabled for a given launch. See [Managed Launch Prompt Header](../run-phase/managed-prompt-header.md) for what the header contains and the prompt composition order.
- Credential CRUD is no longer part of `internals native-agent tools <tool> ...`. Use `project [--project-dir <dir>] credentials <tool> ...` for project-backed credentials, and `internals native-agent credentials <tool> ... --native-agent-root <dir>` for direct native-agent credentials. `internals native-agent tools <tool> get` and `tools <tool> setups ...` remain focused on tool subtree inspection and setup bundle maintenance.

`internals native-agent recipes` notes:

- `recipes add` requires `--name`, `--role`, `--tool`, accepts repeatable `--skill`, optional `--auth`, optional `--setup` (defaults to `default`), and optional `--prompt-mode` (`unattended` or `as_is`; defaults to `unattended` when omitted).
- `recipes set` patches without dropping advanced blocks. It supports `--role`, `--tool`, `--setup`, `--auth`, `--clear-auth`, repeatable `--add-skill` and `--remove-skill`, `--clear-skills`, `--prompt-mode`, and `--clear-prompt-mode`. `mailbox` and `extra` blocks already present in a recipe are preserved.
- The system rejects creation or mutation that would make two recipes share the same `(role, tool, setup)` tuple.
- `recipes remove` deletes the named recipe file but does not delete any launch profile that references it; remove referencing launch profiles separately when needed.

`internals native-agent launch-dossiers` notes:

- `launch-profiles add` requires `--name` and `--recipe`. It accepts: `--agent-name`, `--agent-id`, `--workdir`, `--auth`, `--prompt-mode {unattended|as_is}`, repeatable `--env-set NAME=value`, managed system-skill flags (`--system-skill-set`, `--system-skill`, `--system-skills-mode {inherit|extend|replace|none}`, `--no-system-skills`), mailbox flags (`--mail-transport {filesystem|stalwart}`, `--mail-principal-id`, `--mail-address`, `--mail-root`, `--mail-base-url`, `--mail-jmap-url`, `--mail-management-url`), launch posture flags (`--headless`, `--no-gateway`, `--gateway-port`), relaunch chat-session flags (`--relaunch-chat-session-mode {new|tool_last_or_new|exact}`, `--relaunch-chat-session-id`), prompt-overlay flags (`--prompt-overlay-mode {append|replace}`, `--prompt-overlay-text`, `--prompt-overlay-file`), `--gateway-mail-notifier-appendix-text`, and memo-seed flags (`--memo-seed-text`, `--memo-seed-file`, `--memo-seed-dir`).
- `launch-profiles add` rejects an existing profile name by default. Passing `--yes` confirms same-lane replacement of an existing explicit launch profile; replacement uses create semantics, so omitted optional fields are cleared instead of preserved. `--yes` does not allow replacing an project profile with an explicit launch profile.
- `launch-profiles add` also accepts `--managed-header` or `--no-managed-header` to store explicit managed-header whole-header policy, plus repeatable `--managed-header-section SECTION=enabled|disabled` to store section policy. Omitting whole-header flags stores `inherit`; omitting section flags stores no section entries. For the conceptual model behind these flags, see [Managed Launch Prompt Header](../run-phase/managed-prompt-header.md).
- `launch-profiles set` patches without dropping unspecified advanced blocks and exposes matching `--clear-*` flags for nullable fields (`--clear-agent-name`, `--clear-agent-id`, `--clear-workdir`, `--clear-auth`, `--clear-prompt-mode`, `--clear-env`, `--clear-system-skills`, `--clear-mailbox`, `--clear-headless`, `--clear-relaunch-chat-session`, `--clear-managed-header`, `--clear-managed-header-section`, `--clear-managed-header-sections`, `--clear-prompt-overlay`, `--clear-gateway-mail-notifier-appendix`, `--clear-memo-seed`).
- Managed system-skill selectors without `--system-skills-mode` infer `extend`. Profile mode `inherit` uses the source recipe's effective selection, `extend` adds selectors to that source selection, `replace` uses exactly the selected system-skill sets/skills, and `none` installs no current Houmao-owned system skills for future launches.
- Supplying `--gateway-mail-notifier-appendix-text` on `launch-profiles add|set` stores a default appended to future runtime notifier prompts. Launching from the profile seeds that text into gateway notifier state without enabling notifier polling. Later live `agents single ... gateway mail-notifier enable --appendix-text ...` or `agents self gateway mail-notifier enable --appendix-text ...` edits runtime state only and do not rewrite the stored profile.
- Stored relaunch chat-session policy is applied only by future selected-agent `agents single ... relaunch` operations. `--relaunch-chat-session-mode exact` requires `--relaunch-chat-session-id`; ids are omitted for `new` and `tool_last_or_new`.
- Supplying a new `--memo-seed-text`, `--memo-seed-file`, or `--memo-seed-dir` source on `launch-profiles set` replaces the stored seed. `--clear-memo-seed` cannot be combined with a new memo seed source.
- Memo seeds always replace only the managed-memory components represented by the seed source. `--memo-seed-text` and `--memo-seed-file` touch only `houmao-memo.md`; `--memo-seed-dir` touches `houmao-memo.md` only when that file is present and touches pages only when `pages/` is present. `--memo-seed-text ''` stores an intentional empty memo seed without clearing pages. `--clear-memo-seed` removes stored seed configuration instead of writing an empty memo.
- `launch-profiles set` also accepts `--managed-header` or `--no-managed-header` and repeatable `--managed-header-section SECTION=enabled|disabled`. Whole-header flags are mutually exclusive, `--clear-managed-header` returns the stored whole-header field to `inherit`, `--clear-managed-header-section SECTION` removes one stored section entry, and `--clear-managed-header-sections` removes all stored section entries.
- `launch-profiles list` accepts optional `--recipe` and `--tool` filters when those identities are derivable from the referenced recipe.
- `launch-profiles remove` deletes one launch-profile resource without deleting the referenced recipe.
- Launch profiles authored here are recipe-backed and explicit. They are stored as the same kind of catalog object that backs easy `project profile ...`, but the explicit lane keeps the lower-level launch contract visible by intent.

`project credentials claude add|set` notes:

- Claude supports maintained auth inputs `--api-key`, `--auth-token`, `--oauth-token`, optional `--config-dir`, optional `--base-url`, and optional model-selection env values.
- `--config-dir` imports Claude vendor login state from a maintained Claude config root by copying `.credentials.json` and companion `.claude.json` when present.
- `--state-template-file` remains optional Claude bootstrap state only and is not a credential-providing method.
- See [Claude Vendor Login Files](../claude-vendor-login-files.md) for the file-handling rules and the local smoke-validation workflow.

#### `project`

`project` is the higher-level project authoring and runtime-instance path.

| Subcommand | Description |
|---|---|
| `specialist create` | Persist one specialist in `catalog.sqlite`, snapshot prompt/auth/skill payloads into `content/`, and materialize the needed `agents/` compatibility projection under the active overlay root. |
| `specialist set` | Patch one existing specialist without recreating it. Preserves unspecified prompt, skill, setup, credential, launch-model, prompt-mode, and env fields, then rematerializes the compatibility projection. |
| `specialist list|get|remove` | Inspect or remove persisted specialist definitions without forcing manual tree inspection; `get` reports stored launch config such as `launch.prompt_mode` and `launch.env_records`. |
| `profile create` | Persist one specialist-backed project profile that captures reusable birth-time launch defaults over exactly one specialist. Stored in the shared launch-profile catalog family with `profile_lane=easy_profile`. |
| `profile list|get|set|remove` | Inspect, patch, or remove persisted project profiles. `get` reports the source specialist plus the stored project-profile launch defaults. `set` patches stored defaults without dropping unspecified fields. `remove` deletes the project profile without removing the specialist it referenced. |
| `instance launch` | Launch one managed agent from either a compiled specialist (`--specialist`) or a stored project profile (`--profile`). The two selectors are mutually exclusive and exactly one is required. |
| `instance stop` | Stop one managed agent through the project-aware easy instance surface. |
| `instance list|get` | View existing managed-agent runtime state as project-local specialist instances. `list` and `get` also report the originating project-profile identity when runtime-backed state makes it resolvable. |

`project specialist create` notes:

- `--name` and `--tool` are required.
- `--credential` is optional; when omitted, Houmao uses `<specialist-name>-creds` as the auth display name.
- `--system-prompt` and `--system-prompt-file` are both optional; provide at most one.
- `--no-unattended` opts out of the easy unattended default and persists `launch.prompt_mode: as_is` for that specialist.
- repeatable `--env-set NAME=value` stores durable specialist-owned launch env under `launch.env_records`.
- `--model` and `--reasoning-level` are the supported launch-owned model-selection surfaces. `--reasoning-level` is a tool/model-specific preset index rather than a portable `1..10` knob.
- repeatable `--system-skill-set` and `--system-skill` store specialist-owned managed system-skill policy under `launch.system_skills`; selectors without `--system-skills-mode` infer `extend`, `--system-skills-mode replace` stores exact selection, and `--no-system-skills` stores disabled policy. Omitted policy keeps the managed-launch default.
- repeatable `--skill <name>` binds already registered project skills by name.
- repeatable `--with-skill <dir>` is a convenience path that registers or updates one canonical project skill entry and then binds it to the specialist. Houmao treats the provided source directory as read-only input.
- when the selected specialist name already exists, `specialist create` prompts before replacing the specialist-owned prompt and recipe projection and accepts `--yes` for non-interactive replacement.
- If neither system-prompt option is supplied, the compiled role remains valid and the runtime treats it as having no startup prompt content.
- maintained easy launch paths persist `launch.prompt_mode: unattended` by default in both the catalog-backed specialist launch payload and the generated compatibility recipe projected under `.houmao/agents/presets/`, including Gemini's headless-only easy lane.
- specialist `--env-set` is separate from credential env and rejects auth-owned or Houmao-owned reserved env names.
- Claude credential lanes use the same credential semantics in both `project credentials claude add|set` and `project specialist create --tool claude`, but the flag names differ: the dedicated credential surface uses unprefixed names (`--api-key`, `--auth-token`, `--oauth-token`, `--config-dir`, `--base-url`) while the easy-specialist surface uses prefixed names (`--api-key`, `--claude-auth-token`, `--claude-oauth-token`, `--claude-config-dir`, `--base-url`). Model selection on the easy surface is now unified under `--model` plus optional `--reasoning-level`, with `--claude-model` retained only as a compatibility alias for `--model`.
- Claude auth bundle updates are patch-preserving: setting `--claude-oauth-token`, `--claude-config-dir`, or `--base-url` does not implicitly delete other stored Claude auth inputs, and refreshing `--claude-config-dir` replaces the imported vendor login files as one maintained set. `--claude-model` no longer writes auth-owned model env; it resolves into launch-owned model selection.
- `--claude-state-template-file` remains optional Claude bootstrap state and is not itself a credential-providing method on the easy-specialist surface.
- The maintained vendor-login lane is still directory-based. Pass `--config-dir` or `--claude-config-dir`, not separate `.credentials.json` or `.claude.json` file flags.
- Detailed vendor-native model tuning belongs in the relevant specialist or credential skill documentation rather than the core CLI reference.
- Gemini credential lanes use the same contract in both `project credentials gemini add|set` and `project specialist create --tool gemini`: `--api-key`, optional `--base-url`, and optional `--oauth-creds` or `--gemini-oauth-creds`.
- Gemini auth bundle updates are patch-preserving: setting `--base-url` or `--oauth-creds` does not implicitly delete other Gemini auth inputs that were already stored.
- The project-local catalog is the source of truth; `agents/` under the active overlay root is a compatibility projection that is materialized as needed.

`project specialist set` notes:

- `--name` is required and must identify an existing specialist. At least one update or clear flag is required.
- Patchable fields include prompt (`--system-prompt`, `--system-prompt-file`, `--clear-system-prompt`), skills (`--with-skill`, `--add-skill`, `--remove-skill`, `--clear-skills`), setup (`--setup`), credential (`--credential`), prompt mode (`--prompt-mode`, `--clear-prompt-mode`), launch-owned model (`--model`, `--clear-model`, `--reasoning-level`, `--clear-reasoning-level`), persistent env (`--env-set`, `--clear-env`), and managed system-skill policy (`--system-skill-set`, `--system-skill`, `--system-skills-mode`, `--no-system-skills`, `--clear-system-skills`).
- `--env-set` replaces the stored specialist env mapping with the repeated `NAME=value` records supplied on that command. Use `--clear-env` to remove the mapping.
- `--with-skill <dir>` registers or updates one canonical project skill entry and then adds that skill to the specialist without mutating the provided source directory. `--add-skill <name>` adds an already registered project skill by name. `--remove-skill <name>` removes that skill from the specialist definition; shared project skill content is not deleted just because one specialist stops referencing it.
- `--setup <name>` switches to another setup bundle for the specialist's current tool lane. When the preset name changes, the old specialist-owned projected preset file is removed after the catalog projection is materialized.
- `--credential <name>` selects an existing credential display name for the specialist's current tool lane. It does not create or mutate credential bundles.
- `specialist set` does not rename specialists and does not change the tool lane; create a new specialist when either identity should change.
- Updates affect future launches and profile resolutions. Already-running easy instances are not mutated in place.

`project profile create` notes:

- `--name` and `--specialist` are required. The named profile targets exactly one existing specialist.
- Optional birth-time defaults: `--agent-name`, `--agent-id`, `--workdir`, `--auth`, `--prompt-mode {unattended|as_is}`, `--model`, `--reasoning-level`, repeatable `--env-set NAME=value`, managed system-skill flags (`--system-skill-set`, `--system-skill`, `--system-skills-mode {inherit|extend|replace|none}`, `--no-system-skills`), mailbox flags (`--mail-transport {filesystem|stalwart}`, `--mail-principal-id`, `--mail-address`, `--mail-root`, `--mail-base-url`, `--mail-jmap-url`, `--mail-management-url`), launch posture flags (`--headless`, `--no-gateway`, `--gateway-port`), relaunch chat-session flags (`--relaunch-chat-session-mode {new|tool_last_or_new|exact}`, `--relaunch-chat-session-id`), managed-header flags (`--managed-header`, `--no-managed-header`, repeatable `--managed-header-section SECTION=enabled|disabled`), prompt-overlay flags (`--prompt-overlay-mode {append|replace}`, `--prompt-overlay-text`, `--prompt-overlay-file`), `--gateway-mail-notifier-appendix-text`, and memo-seed flags (`--memo-seed-text`, `--memo-seed-file`, `--memo-seed-dir`).
- `project profile create` rejects an existing profile name by default. Passing `--yes` confirms same-lane replacement of an existing project profile; replacement uses create semantics, so omitted optional fields are cleared instead of preserved. `--yes` does not allow replacing an explicit launch profile with an project profile.
- `project profile set --name <profile>` patches stored defaults on an existing project profile while preserving unspecified fields. It accepts the same stored-default field families as explicit `launch-profiles set`, including clear flags such as `--clear-agent-name`, `--clear-agent-id`, `--clear-workdir`, `--clear-auth`, `--clear-prompt-mode`, `--clear-env`, `--clear-system-skills`, `--clear-mailbox`, `--clear-headless`, `--clear-relaunch-chat-session`, `--clear-managed-header`, `--clear-managed-header-section`, `--clear-managed-header-sections`, `--clear-prompt-overlay`, `--clear-gateway-mail-notifier-appendix`, and `--clear-memo-seed`.
- Easy-profile managed system-skill policy follows the shared launch-profile rules: omitted means inherit from the specialist/recipe source, selectors without mode infer `extend`, `replace` stores exact selection, and `none` disables current Houmao-owned system skills for future launches.
- Project profiles support the same stored notifier appendix default as native launch dossiers through `--gateway-mail-notifier-appendix-text`; launches seed it into runtime gateway notifier state without enabling polling.
- Easy-profile memo seed semantics match native launch dossiers: stored seeds replace only represented memo/pages components, and `--clear-memo-seed` removes stored seed configuration rather than seeding an empty memo.
- The persisted project profile lives in the shared catalog launch-profile family with `profile_lane=easy_profile` and `source_kind=specialist`. It projects into the same compatibility tree (`.houmao/agents/launch-profiles/<name>.yaml`) used by native launch dossiers.
- `--auth <name>` is display-name-oriented at the CLI, but the stored project-profile relationship resolves through auth-profile identity so later `project credentials <tool> rename` continues to work.
- Omitting both managed-header flags on `project profile create` stores `inherit`, which falls back to the default enabled managed-header behavior later at launch time.
- When no active project overlay exists for the caller, `project profile create` ensures `<cwd>/.houmao` exists before persisting the profile (matching the `project specialist create` bootstrap behavior).
- `project profile remove` removes only the profile definition. It does not remove the specialist that the profile referenced.
- For the conceptual model that ties project profiles to native launch dossiers, see [Launch Profiles](../../getting-started/launch-profiles.md).

`project agents launch` notes:

- Exactly one of `--specialist` or `--profile` is required. The two selectors are mutually exclusive.
- `--specialist` selects a compiled specialist definition to launch from directly. `--name` is required when launching from `--specialist`.
- `--profile` selects a stored project profile. The command derives the source specialist from that profile, applies project-profile-stored defaults (managed-agent identity, workdir, auth override, prompt mode, durable env records, declarative mailbox config, headless/gateway posture, prompt overlay, any gateway mail-notifier appendix default, and any stored memo seed), and uses the active project overlay as the authoritative source context. Auth is still rendered by display name even though the stored relationship is auth-profile-backed. `--name` may be omitted when the selected profile stores a default managed-agent name; otherwise it remains required.
- Stored project-profile memo seeds apply their represented memo/pages components before prompt composition and provider startup. Direct `project agents launch --specialist ...` launches do not apply one because no reusable project profile was selected, and there is no one-shot memo-seed override flag on the launch surface.
- Direct launch-time overrides such as `--auth`, `--workdir`, `--name`, `--mail-transport`, `--mail-root`, and `--mail-account-dir` win over project-profile defaults but never rewrite the stored project profile. The next launch from the same profile will see the original stored defaults again.
- `--reuse-home` reuses one compatible preserved home for the resolved managed identity, rebuilds current Houmao-managed launch inputs onto that home, and still creates fresh live session authority for the new project-backed launch. The flag never becomes part of specialist metadata or project-profile storage.
- `--reuse-home` alone does not replace a fresh live owner, and `--reuse-home --force clean` is rejected before cleanup begins because destructive clean mode would discard the preserved home contents.
- `--force [keep-stale|clean]` applies only to the current easy-instance launch. Bare `--force` means `keep-stale`, which stops the predecessor and reuses the predecessor managed home while leaving untouched stale artifacts alone.
- `--force clean` stops the predecessor and removes predecessor-owned replaceable launch artifacts before rebuilding. Shared mailbox message history and unrelated operator-owned paths are preserved.
- Force mode never becomes part of specialist metadata or project-profile storage.
- `--managed-header` and `--no-managed-header` are mutually exclusive one-shot overrides. They win over the stored project-profile managed-header policy for the current launch only and never rewrite the stored project profile.
- When neither managed-header flag is supplied, easy-instance launch inherits policy from the selected profile when one is present; otherwise it falls back to the default enabled behavior.
- `project agents launch` also accepts repeatable `--managed-header-section SECTION=enabled|disabled` one-shot section overrides. These win over stored project-profile section policy for the named section and never rewrite the stored project profile.
- `--append-system-prompt-text` and `--append-system-prompt-file` are mutually exclusive one-shot appendix inputs. They append after any resolved project-profile prompt overlay and never rewrite the stored specialist or project profile.
- Easy-instance inspection (`project agents list` and `project agents get`) reports the originating project-profile identity in addition to the originating specialist when runtime-backed state makes both resolvable.
- `--name` is the managed-agent instance name and also seeds the default filesystem mailbox identity when mailbox association is enabled.
- unless `--no-gateway` is supplied, the easy surface now requests launch-time gateway attach by default on loopback (`127.0.0.1`) with a system-assigned port.
- by default, that easy auto-attach uses same-session foreground gateway execution and reports `gateway_execution_mode` plus `gateway_tmux_window_index` when foreground attach succeeds.
- `--gateway-port <port>` keeps the default easy gateway attach enabled for that launch, but requests the specified loopback listener port instead of a system-assigned port.
- `--gateway-background` keeps easy auto-attach enabled for that launch, but requests detached background gateway execution instead of the default foreground auxiliary-window execution.
- `--gateway-tui-watch-poll-interval-seconds`, `--gateway-tui-stability-threshold-seconds`, `--gateway-tui-completion-stability-seconds`, `--gateway-tui-unknown-to-stalled-timeout-seconds`, `--gateway-tui-stale-active-recovery-seconds`, and `--gateway-tui-final-stable-active-recovery-seconds` are positive-second one-shot overrides for the gateway-owned TUI tracker. They affect the current launch-time gateway attach and are not stored in launch profiles or project profiles.
- `--no-gateway` is mutually exclusive with `--gateway-port`, `--gateway-background`, and any `--gateway-tui-*` override.
- `--workdir` overrides only the launched agent runtime cwd; the selected project overlay, specialist source, runtime root, jobs root, and default mailbox root remain pinned to the selected project.
- the command honors the stored specialist launch posture instead of injecting a separate prompt-mode policy at launch time.
- Gemini specialists remain headless-only here and fail fast unless `--headless` is supplied.
- repeatable `--env-set NAME=value|NAME` applies one-off env to the current live session, resolves inherited `NAME` bindings from the invoking shell, and does not survive relaunch.
- `--mail-transport filesystem` requires `--mail-root` and optionally accepts `--mail-account-dir` for a symlink-backed private mailbox directory.
- `--mail-account-dir` must resolve outside the shared mailbox root; safe launch fails if the address slot already exists as a real directory or as a symlink to a different target.
- `--mail-transport email` is reserved for a future real-email path and currently fails fast as not implemented.
- when the managed session starts but launch-time gateway attach fails afterward, the command still reports the live session identity and manifest path, includes `gateway_auto_attach_error`, and exits with degraded-success status code `2`.
- Project-backed launch also accepts `--workdir`; the selected project stays authoritative for overlay-local defaults even if the runtime cwd points somewhere else.
- `agents self join` uses `--workdir` instead of `--working-directory`; when omitted, the adopted cwd comes from tmux window `0`, pane `0`.

#### `project mailbox`

`project mailbox` mirrors the generic mailbox-root CLI, but automatically targets `mailbox/` under the active overlay root selected by `HOUMAO_PROJECT_OVERLAY_DIR` or ambient discovery under `HOUMAO_PROJECT_OVERLAY_DISCOVERY_MODE`.

| Subcommand | Description |
|---|---|
| `init`, `status`, `register`, `unregister`, `repair`, `cleanup`, `clear-messages`, `export` | Perform mailbox-root lifecycle operations against `.houmao/mailbox`. |
| `accounts list|get` | Inspect mailbox registrations under the project mailbox root. |
| `messages list|get` | Inspect structural message projections under the project mailbox root. |

`project mailbox register` mirrors the generic mailbox overwrite-confirmation contract, including interactive overwrite prompts and `--yes` for non-interactive replacement.

`project mailbox clear-messages` mirrors the generic delivered-message reset, but targets the selected overlay mailbox root automatically.

`project mailbox export --output-dir <dir> (--all-accounts | --address <full-address>...) [--symlink-mode materialize|preserve]` mirrors the generic export behavior, but targets `mailbox/` under the selected project overlay and includes the selected overlay details in the structured result.

`project mailbox messages list|get` follows the same structural-only contract as `houmao-mgr mailbox messages list|get`; use `houmao-mgr agents single ... mail ...` or `houmao-mgr agents self mail ...` when the workflow needs actor-scoped unread/read follow-up state.

### `internals` — Internal utility commands

```
houmao-mgr internals [OPTIONS] COMMAND [ARGS]...
```

Internal Houmao utility commands for agents and maintainers.

The primary subgroup is `internals graph`, which provides NetworkX-backed helpers for loop plan authoring, structural analysis, and low-level graph manipulation. All graph commands use NetworkX node-link JSON as their interchange format.

For the full subcommand reference, see [internals](internals.md).

---

**Removed entrypoints:** `houmao-cli`, standalone `houmao-server`, and `houmao-mgr server ...` are retired. Use `houmao-mgr` for local workflows and `houmao-passive-server` for the maintained server API surface.
