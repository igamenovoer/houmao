# houmao-mgr

Houmao pair CLI with native server and managed-agent command families.

`houmao-mgr` is the primary management CLI for local lifecycle, managed agents, mailbox administration, packaged Houmao-owned system-skill installation, repo-local project overlays, and `houmao-server` control. It provides native command groups for agent orchestration, filesystem mailbox administration, brain construction, explicit tool-home skill installation, project bootstrap, server management, and administrative tasks.

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

### `agents` — Agent lifecycle

```
houmao-mgr agents [OPTIONS] COMMAND [ARGS]...
```

Agent lifecycle: launch, stop, observe, send-prompt, mail, join, gateway operations.

For dedicated coverage of complex nested command families, see:

- [agents gateway](agents-gateway.md) — gateway lifecycle and explicit live-gateway request commands
- [agents turn](agents-turn.md) — managed headless turn submission and inspection
- [agents mail](agents-mail.md) — managed-agent mailbox follow-up
- [agents mailbox](agents-mailbox.md) — late filesystem mailbox registration for local managed agents

#### Subcommands

| Subcommand | Description |
|---|---|
| `launch` | Start a managed agent. Provisions a runtime home, builds the brain, and launches a live session. Accepts either `--agents <selector>` for a direct recipe selector or `--launch-profile <name>` to resolve a stored explicit launch profile (mutually exclusive). |
| `join` | Adopt an existing tmux-backed TUI or native headless logical session into Houmao managed-agent control. |
| `list`, `state` | Inspect locally discovered or pair-backed managed agents. |
| `prompt` | Send a prompt to a running agent session. |
| `stop`, `interrupt`, `relaunch` | Control the current managed-agent runtime posture. |
| `mail` | Resolve live mailbox bindings, inspect status, check, send, reply, or mark messages read. |
| `mailbox` | Register, unregister, or inspect late filesystem mailbox bindings on an existing local managed agent. |
| `cleanup session|logs|mailbox` | Clean one stopped managed-session envelope, session-local log artifacts, or session-local mailbox secret material without calling `houmao-server`. |
| `gateway attach` | Attach a gateway to an agent session. |
| `gateway status` | Show gateway status for a session. |
| `gateway prompt` | Send a prompt through the gateway. |
| `gateway interrupt` | Interrupt the current gateway operation. |
| `gateway send-keys` | Send raw control input through the live gateway. |
| `gateway tui state|history|watch|note-prompt` | Inspect or annotate the raw gateway-owned TUI tracking surface. |
| `gateway mail-notifier status|enable|disable` | Inspect or control live unread-mail reminder behavior on the gateway. |

Gateway targeting rules:

- Outside tmux, gateway commands require an explicit `--agent-id` or `--agent-name`.
- Inside a managed tmux session, omitting the selector resolves the current session from `HOUMAO_MANIFEST_PATH` first and falls back to `HOUMAO_AGENT_ID` plus shared registry when needed.
- `--current-session` forces same-session resolution and cannot be combined with `--agent-id`, `--agent-name`, or `--port`.
- `--port` is only supported with an explicit selector, because current-session mode uses the manifest-declared pair authority instead of retargeting another server.

Gateway TUI notes:

- `gateway tui state` and `gateway tui watch` read the exact raw gateway-owned tracked state rather than the transport-neutral `agents state` payload.
- `gateway tui history` returns bounded in-memory snapshot history from the live gateway tracker, not coarse managed-agent `/history`.
- `gateway tui note-prompt` records explicit prompt provenance on the live gateway tracker without enqueueing a gateway prompt request.

Mail targeting rules:

- Outside tmux, `agents mail` requires an explicit `--agent-id` or `--agent-name`.
- Inside a managed tmux session, omitting those selectors resolves the current session from `HOUMAO_MANIFEST_PATH` first and `HOUMAO_AGENT_ID` plus shared-registry metadata second.
- `--port` on `agents mail` is only supported with an explicit selector.

The preferred local serverless mailbox workflow is:

1. `houmao-mgr mailbox init --mailbox-root <path>`
2. `houmao-mgr agents launch ...` or `houmao-mgr agents join ...`
3. `houmao-mgr agents mailbox register --agent-name <name> --mailbox-root <path>`
4. `houmao-mgr agents mail ...`

For supported tmux-backed managed sessions, including sessions adopted through `houmao-mgr agents join`, `agents mailbox register` and `agents mailbox unregister` update the durable manifest-backed mailbox binding without requiring relaunch solely for mailbox attachment. That remains true even when a joined session is controllable but non-relaunchable because no launch options were recorded, as long as Houmao can still update the session manifest and validate the resulting mailbox binding. When a direct mailbox workflow needs the current binding set explicitly, resolve it through `pixi run houmao-mgr agents mail resolve-live`. Inside the owning tmux session, selectors may be omitted. Outside tmux, or when targeting a different agent, use an explicit `--agent-id` or `--agent-name`. The resolver returns structured mailbox fields plus optional live `gateway.base_url` data for attached `/v1/mail/*` work.

If `agents mailbox register` would replace existing shared mailbox state, the command prompts before destructive replacement on interactive terminals and accepts `--yes` for non-interactive overwrite confirmation.

Cleanup targeting rules:

- `agents cleanup session|logs|mailbox` accept exactly one of `--agent-id`, `--agent-name`, `--manifest-path`, or `--session-root`.
- Inside the target tmux session, omitting those options resolves the current session from `HOUMAO_MANIFEST_PATH` first and `HOUMAO_AGENT_ID` plus fresh shared-registry metadata second.
- Every cleanup command supports `--dry-run` and reports `planned_actions`, `applied_actions`, `blocked_actions`, and `preserved_actions` in one normalized payload. Plain and fancy modes print populated action buckets line by line, while `--print-json` preserves the machine-readable JSON shape.

`agents launch` source-selector and launch-profile rules:

- `agents launch` accepts exactly one of `--agents <selector>` and `--launch-profile <name>`. The two are mutually exclusive and one is required.
- `--agents` is the direct recipe selector form. The effective provider defaults to `claude_code` when `--provider` is omitted.
- `--launch-profile` resolves the named launch profile from the active project overlay and rejects easy `project easy profile ...` selections; only explicit recipe-backed launch profiles (`profile_lane=launch_profile`) are accepted.
- A launch-profile-backed launch derives the source recipe from the stored profile, then composes effective inputs in the precedence order: source recipe defaults → launch-profile defaults → direct CLI overrides.
- Direct overrides such as `--agent-name`, `--agent-id`, `--auth`, and `--workdir` apply to one launch and never rewrite the stored launch profile.
- `--provider` defaults from the resolved launch-profile recipe when one tool family is determined by that source. Supplying `--provider` together with `--launch-profile` is accepted only when it matches the resolved source; otherwise the command fails clearly before build.
- Launch-profile-stored fields that flow through the manifest into runtime launch resolution include managed-agent identity defaults, working directory, auth override by name, prompt-mode override, durable env records, declarative mailbox config, headless and gateway posture, and the prompt overlay (composed into the effective role prompt before backend-specific role injection).
- For the conceptual model that ties `agents launch --launch-profile` to easy `project easy profile` and to the broader launch-profile object family, see [Launch Profiles](../../getting-started/launch-profiles.md).

### `mailbox` — Local filesystem mailbox administration

```
houmao-mgr mailbox [OPTIONS] COMMAND [ARGS]...
```

Local operator commands for filesystem mailbox roots and address lifecycle. This surface does not require `houmao-server`.

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

`mailbox register` keeps the existing `safe`, `force`, and `stash` mode vocabulary. When a requested registration would replace existing durable mailbox state or an occupying mailbox entry artifact, the command prompts before destructive replacement on interactive terminals and accepts `--yes` for non-interactive overwrite confirmation.

`mailbox messages list|get` is structural inspection over canonical message metadata plus address-scoped projection metadata. Participant-local mutable state such as `read`, `starred`, `archived`, and `deleted` belongs on actor-scoped `houmao-mgr agents mail ...` workflows rather than this operator/admin surface.

### `brains` — Local brain-construction commands

```
houmao-mgr brains [OPTIONS] COMMAND [ARGS]...
```

Local brain-construction commands; these do not call houmao-server.

#### `brains build`

Build one local brain home from `BuildRequest`-aligned inputs.

```
houmao-mgr brains build [OPTIONS]
```

**Options:**

| Option | Description |
|---|---|
| `--agent-def-dir PATH` | Path to the agent definition directory. |
| `--tool TEXT` | Tool identifier for the brain (e.g. `codex`, `claude`, `gemini`). |
| `--skill TEXT` | Skill name to include. May be specified multiple times. |
| `--setup TEXT` | Setup bundle to materialize. |
| `--auth TEXT` | Auth bundle to project. |
| `--preset TEXT` | Preset path or bare preset name resolved from the agent root. |
| `--runtime-root PATH` | Root directory for runtime homes. |
| `--home-id TEXT` | Explicit home identifier for the runtime home directory. |
| `--reuse-home` | Reuse an existing runtime home if one matches, instead of creating a new one. |
| `--launch-overrides TEXT` | Secret-free launch overrides to pass through to the tool adapter. |
| `--agent-name TEXT` | Human-readable agent name. |
| `--agent-id TEXT` | Explicit agent identifier. |

`brains build` resolves the effective agent-definition root with this precedence:

1. `--agent-def-dir`
2. `HOUMAO_AGENT_DEF_DIR`
3. `HOUMAO_PROJECT_OVERLAY_DIR`
4. ambient project-overlay discovery under `HOUMAO_PROJECT_OVERLAY_DISCOVERY_MODE`
5. default `<pwd>/.houmao/agents`

`HOUMAO_PROJECT_OVERLAY_DIR` must be an absolute path and selects the overlay directory directly for CI or controlled automation. `HOUMAO_PROJECT_OVERLAY_DISCOVERY_MODE` affects ambient discovery only when no explicit overlay root is set: `ancestor` is the default nearest-ancestor lookup bounded by the Git repository, while `cwd_only` restricts lookup to `<cwd>/.houmao/houmao-config.toml`. When env selection or discovery wins, `houmao-config.toml` inside that overlay is the discovery anchor and `agents/` under the same overlay is the compatibility projection that current file-tree consumers read from the catalog-backed overlay.

When `--preset` resolves to a recipe that carries `launch.env_records`, `brains build` projects those records as durable non-credential launch env alongside the selected auth bundle. Those env records come from specialist launch config, not from one-off instance launch input.

### `system-skills` — Packaged Houmao-owned skill installation for resolved tool homes

```
houmao-mgr system-skills [OPTIONS] COMMAND [ARGS]...
```

Install or inspect the packaged current Houmao-owned `houmao-*` skill set for resolved Claude, Codex, or Gemini homes.

#### Subcommands

| Subcommand | Description |
|---|---|
| `list` | Show the packaged skill inventory, named sets, and fixed auto-install set lists. |
| `status` | Show whether one resolved tool home has Houmao-owned install state and which skills are recorded there. |
| `install` | Install the CLI-default set list, explicit named sets, explicit skills, or any combination of those into one resolved tool home. |

Operational notes:

- `system-skills install` requires `--tool` and accepts optional `--home`
- `system-skills status` requires `--tool` and accepts optional `--home`
- when `--home` is omitted, the effective home resolves with precedence `--home` override, tool-native home env var (`CLAUDE_CONFIG_DIR`, `CODEX_HOME`, `GEMINI_CLI_HOME`), then the project-scoped default home
- the project-scoped defaults are `<cwd>/.claude` for Claude, `<cwd>/.codex` for Codex, and `<cwd>` for Gemini
- omitting both `--set` and `--skill` selects the packaged CLI-default set list
- optional `--symlink` installs the selected packaged skills as absolute-target directory symlinks instead of copied trees
- repeated sets expand in order, explicit skills append after sets, and the final list is deduplicated by first occurrence
- the installer preserves flat visible Houmao-owned skill paths: Claude uses `skills/houmao-...`, Codex uses `skills/houmao-...`, and Gemini uses `.gemini/skills/houmao-...`
- each target home records Houmao-owned install state under `.houmao/system-skills/install-state.json`
- managed brain build and `agents join` use the same packaged catalog and installer internally

For the detailed catalog, projection, and ownership contract, see [system-skills](system-skills.md).

### `project` — Repo-local Houmao project overlays

```
houmao-mgr project [OPTIONS] COMMAND [ARGS]...
```

Local operator workflow for bootstrapping and inspecting one repo-local overlay. By default the overlay root is `<pwd>/.houmao`. Set `HOUMAO_PROJECT_OVERLAY_DIR=/abs/path` to target a different overlay directory directly.

Command shape:

```text
houmao-mgr project
├── init | status
├── agents
│   ├── roles ...
│   ├── recipes ...                # canonical low-level source recipes
│   ├── presets ...                # compatibility alias for `recipes`
│   ├── launch-profiles ...        # explicit recipe-backed birth-time launch profiles
│   └── tools <tool> ...
├── easy
│   ├── specialist ...
│   ├── profile ...                # specialist-backed easy birth-time profiles
│   └── instance ...
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
| `agents` | Low-level filesystem-oriented management for the `.houmao/agents/` compatibility projection. |
| `easy` | Higher-level specialist and instance workflow persisted in `.houmao/catalog.sqlite` with file-backed payloads under `.houmao/content/`. |
| `mailbox` | Project-scoped wrapper over the generic mailbox-root CLI targeting `mailbox/` under the active overlay root. |

Project overlay notes:

- `project init` bootstraps `<pwd>/.houmao` by default.
- `HOUMAO_PROJECT_OVERLAY_DIR=/abs/path` selects `/abs/path` as the overlay root directly and must be absolute.
- `HOUMAO_PROJECT_OVERLAY_DISCOVERY_MODE=ancestor` is the default ambient lookup mode; `cwd_only` restricts ambient lookup to `<pwd>/.houmao/houmao-config.toml`.
- The selected overlay root gets a local `.gitignore` containing `*`, so the whole overlay stays local-only without editing the repo root `.gitignore`.
- `project status` resolves the active overlay root from `HOUMAO_PROJECT_OVERLAY_DIR` first, then ambient discovery under `HOUMAO_PROJECT_OVERLAY_DISCOVERY_MODE`, and reports the effective discovery mode in its JSON payload.
- `project init` creates `catalog.sqlite` plus managed `content/prompts/`, `content/auth/`, `content/skills/`, and `content/setups/` under the selected overlay root.
- `project init` does not create `agents/`, `agents/compatibility-profiles/`, `mailbox/`, or `easy/` under the selected overlay root by default.
- `project init --with-compatibility-profiles` opts into pre-creating `agents/compatibility-profiles/` under the selected overlay root.

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
| `tools <tool> auth list|get|add|set|remove` | Manage project-local auth bundles under `agents/tools/<tool>/auth/<name>/`, including env vars and auth files stored inside those bundles. |

Low-level boundary notes:

- `roles ...` owns the canonical low-level role prompt.
- `recipes ...` (canonical) and `presets ...` (compatibility alias) own named recipe structure, including role selection, tool lane, skills, prompt mode, and selected auth bundle reference. Both surfaces administer the same `.houmao/agents/presets/<name>.yaml` files.
- `launch-profiles ...` owns reusable recipe-backed birth-time launch configuration, including managed-agent identity defaults, working directory, auth override by name, prompt-mode override, durable env records, declarative mailbox config, launch posture, and an optional prompt overlay. For the shared semantic model that ties these to easy profiles, see [Launch Profiles](../../getting-started/launch-profiles.md).
- `tools <tool> auth ...` owns auth-bundle contents. Use that surface when the task is changing env vars or auth files inside the bundle rather than which bundle a recipe selects.

`project agents recipes` notes:

- `recipes add` requires `--name`, `--role`, `--tool`, accepts repeatable `--skill`, optional `--auth`, optional `--setup` (defaults to `default`), and optional `--prompt-mode` (`unattended` or `as_is`; defaults to `unattended` when omitted).
- `recipes set` patches without dropping advanced blocks. It supports `--role`, `--tool`, `--setup`, `--auth`, `--clear-auth`, repeatable `--add-skill` and `--remove-skill`, `--clear-skills`, `--prompt-mode`, and `--clear-prompt-mode`. `mailbox` and `extra` blocks already present in a recipe are preserved.
- The system rejects creation or mutation that would make two recipes share the same `(role, tool, setup)` tuple.
- `recipes remove` deletes the named recipe file but does not delete any launch profile that references it; remove referencing launch profiles separately when needed.

`project agents launch-profiles` notes:

- `launch-profiles add` requires `--name` and `--recipe`. It accepts: `--agent-name`, `--agent-id`, `--workdir`, `--auth`, `--prompt-mode {unattended|as_is}`, repeatable `--env-set NAME=value`, mailbox flags (`--mail-transport {filesystem|stalwart}`, `--mail-principal-id`, `--mail-address`, `--mail-root`, `--mail-base-url`, `--mail-jmap-url`, `--mail-management-url`), launch posture flags (`--headless`, `--no-gateway`, `--gateway-port`), and prompt-overlay flags (`--prompt-overlay-mode {append|replace}`, `--prompt-overlay-text`, `--prompt-overlay-file`).
- `launch-profiles set` patches without dropping unspecified advanced blocks and exposes matching `--clear-*` flags for nullable fields (`--clear-agent-name`, `--clear-agent-id`, `--clear-workdir`, `--clear-auth`, `--clear-prompt-mode`, `--clear-env`, `--clear-mailbox`, `--clear-headless`, `--clear-prompt-overlay`).
- `launch-profiles list` accepts optional `--recipe` and `--tool` filters when those identities are derivable from the referenced recipe.
- `launch-profiles remove` deletes one launch-profile resource without deleting the referenced recipe.
- Launch profiles authored here are recipe-backed and explicit. They are stored as the same kind of catalog object that backs easy `project easy profile ...`, but the explicit lane keeps the lower-level launch contract visible by intent.

`project agents tools claude auth add|set` notes:

- Claude supports maintained auth inputs `--api-key`, `--auth-token`, `--oauth-token`, optional `--config-dir`, optional `--base-url`, and optional model-selection env values.
- `--config-dir` imports Claude vendor login state from a maintained Claude config root by copying `.credentials.json` and companion `.claude.json` when present.
- `--state-template-file` remains optional Claude bootstrap state only and is not a credential-providing method.
- See [Claude Vendor Login Files](../claude-vendor-login-files.md) for the file-handling rules and the local smoke-validation workflow.

#### `project easy`

`project easy` is the higher-level project authoring and runtime-instance path.

| Subcommand | Description |
|---|---|
| `specialist create` | Persist one specialist in `catalog.sqlite`, snapshot prompt/auth/skill payloads into `content/`, and materialize the needed `agents/` compatibility projection under the active overlay root. |
| `specialist list|get|remove` | Inspect or remove persisted specialist definitions without forcing manual tree inspection; `get` reports stored launch config such as `launch.prompt_mode` and `launch.env_records`. |
| `profile create` | Persist one specialist-backed easy profile that captures reusable birth-time launch defaults over exactly one specialist. Stored in the shared launch-profile catalog family with `profile_lane=easy_profile`. |
| `profile list|get|remove` | Inspect or remove persisted easy profiles. `get` reports the source specialist plus the stored easy-profile launch defaults. `remove` deletes the easy profile without removing the specialist it referenced. |
| `instance launch` | Launch one managed agent from either a compiled specialist (`--specialist`) or a stored easy profile (`--profile`). The two selectors are mutually exclusive and exactly one is required. |
| `instance stop` | Stop one managed agent through the project-aware easy instance surface. |
| `instance list|get` | View existing managed-agent runtime state as project-local specialist instances. `list` and `get` also report the originating easy-profile identity when runtime-backed state makes it resolvable. |

`project easy specialist create` notes:

- `--name` and `--tool` are required.
- `--credential` is optional; when omitted, Houmao uses `<specialist-name>-creds`.
- `--system-prompt` and `--system-prompt-file` are both optional; provide at most one.
- `--no-unattended` opts out of the easy unattended default and persists `launch.prompt_mode: as_is` for that specialist.
- repeatable `--env-set NAME=value` stores durable specialist-owned launch env under `launch.env_records`.
- `--model` and `--reasoning-level` are the supported launch-owned model-selection surfaces. `--reasoning-level` uses Houmao's normalized `1..10` scale rather than a vendor-native knob.
- when the selected specialist name already exists, `specialist create` prompts before replacing the specialist-owned prompt and recipe projection and accepts `--yes` for non-interactive replacement.
- If neither system-prompt option is supplied, the compiled role remains valid and the runtime treats it as having no startup prompt content.
- maintained easy launch paths persist `launch.prompt_mode: unattended` by default in both the catalog-backed specialist launch payload and the generated compatibility recipe projected under `.houmao/agents/presets/`, including Gemini's headless-only easy lane.
- specialist `--env-set` is separate from credential env and rejects auth-owned or Houmao-owned reserved env names.
- Claude credential lanes use the same credential semantics in both `project agents tools claude auth add|set` and `project easy specialist create --tool claude`, but the flag names differ: the tools surface uses unprefixed names (`--api-key`, `--auth-token`, `--oauth-token`, `--config-dir`, `--base-url`) while the easy-specialist surface uses prefixed names (`--api-key`, `--claude-auth-token`, `--claude-oauth-token`, `--claude-config-dir`, `--base-url`). Model selection on the easy surface is now unified under `--model` plus optional `--reasoning-level`, with `--claude-model` retained only as a compatibility alias for `--model`.
- Claude auth bundle updates are patch-preserving: setting `--claude-oauth-token`, `--claude-config-dir`, or `--base-url` does not implicitly delete other stored Claude auth inputs, and refreshing `--claude-config-dir` replaces the imported vendor login files as one maintained set. `--claude-model` no longer writes auth-owned model env; it resolves into launch-owned model selection.
- `--claude-state-template-file` remains optional Claude bootstrap state and is not itself a credential-providing method on the easy-specialist surface.
- The maintained vendor-login lane is still directory-based. Pass `--config-dir` or `--claude-config-dir`, not separate `.credentials.json` or `.claude.json` file flags.
- Detailed vendor-native model tuning belongs in the relevant specialist or credential skill documentation rather than the core CLI reference.
- Gemini credential lanes use the same project-tool contract in both `project agents tools gemini auth add|set` and `project easy specialist create --tool gemini`: `--api-key`, optional `--base-url`, and optional `--oauth-creds` or `--gemini-oauth-creds`.
- Gemini auth bundle updates are patch-preserving: setting `--base-url` or `--oauth-creds` does not implicitly delete other Gemini auth inputs that were already stored.
- The project-local catalog is the source of truth; `agents/` under the active overlay root is a compatibility projection that is materialized as needed.

`project easy profile create` notes:

- `--name` and `--specialist` are required. The named profile targets exactly one existing specialist.
- Optional birth-time defaults: `--agent-name`, `--agent-id`, `--workdir`, `--auth`, `--prompt-mode {unattended|as_is}`, `--model`, `--reasoning-level`, repeatable `--env-set NAME=value`, mailbox flags (`--mail-transport {filesystem|stalwart}`, `--mail-principal-id`, `--mail-address`, `--mail-root`, `--mail-base-url`, `--mail-jmap-url`, `--mail-management-url`), launch posture flags (`--headless`, `--no-gateway`, `--gateway-port`), and prompt-overlay flags (`--prompt-overlay-mode {append|replace}`, `--prompt-overlay-text`, `--prompt-overlay-file`).
- The persisted easy profile lives in the shared catalog launch-profile family with `profile_lane=easy_profile` and `source_kind=specialist`. It projects into the same compatibility tree (`.houmao/agents/launch-profiles/<name>.yaml`) used by explicit launch profiles.
- When no active project overlay exists for the caller, `project easy profile create` ensures `<cwd>/.houmao` exists before persisting the profile (matching the `project easy specialist create` bootstrap behavior).
- `project easy profile remove` removes only the profile definition. It does not remove the specialist that the profile referenced.
- For the conceptual model that ties easy profiles to explicit launch profiles, see [Launch Profiles](../../getting-started/launch-profiles.md).

`project easy instance launch` notes:

- Exactly one of `--specialist` or `--profile` is required. The two selectors are mutually exclusive.
- `--specialist` selects a compiled specialist definition to launch from directly. `--name` is required when launching from `--specialist`.
- `--profile` selects a stored easy profile. The command derives the source specialist from that profile, applies easy-profile-stored defaults (managed-agent identity, workdir, auth override, prompt mode, durable env records, declarative mailbox config, headless/gateway posture, and prompt overlay), and uses the active project overlay as the authoritative source context. `--name` may be omitted when the selected profile stores a default managed-agent name; otherwise it remains required.
- Direct launch-time overrides such as `--auth`, `--workdir`, `--name`, `--mail-transport`, `--mail-root`, and `--mail-account-dir` win over easy-profile defaults but never rewrite the stored easy profile. The next launch from the same profile will see the original stored defaults again.
- Easy-instance inspection (`project easy instance list` and `project easy instance get`) reports the originating easy-profile identity in addition to the originating specialist when runtime-backed state makes both resolvable.
- `--name` is the managed-agent instance name and also seeds the default filesystem mailbox identity when mailbox association is enabled.
- unless `--no-gateway` is supplied, the easy surface now requests launch-time gateway attach by default on loopback (`127.0.0.1`) with a system-assigned port.
- `--gateway-port <port>` keeps the default easy gateway attach enabled for that launch, but requests the specified loopback listener port instead of a system-assigned port.
- `--no-gateway` and `--gateway-port` are mutually exclusive.
- `--workdir` overrides only the launched agent runtime cwd; the selected project overlay, specialist source, runtime root, jobs root, and default mailbox root remain pinned to the selected project.
- the command honors the stored specialist launch posture instead of injecting a separate prompt-mode policy at launch time.
- Gemini specialists remain headless-only here and fail fast unless `--headless` is supplied.
- repeatable `--env-set NAME=value|NAME` applies one-off env to the current live session, resolves inherited `NAME` bindings from the invoking shell, and does not survive relaunch.
- `--mail-transport filesystem` requires `--mail-root` and optionally accepts `--mail-account-dir` for a symlink-backed private mailbox directory.
- `--mail-account-dir` must resolve outside the shared mailbox root; safe launch fails if the address slot already exists as a real directory or as a symlink to a different target.
- `--mail-transport email` is reserved for a future real-email path and currently fails fast as not implemented.
- when the managed session starts but launch-time gateway attach fails afterward, the command still reports the live session identity and manifest path, includes `gateway_auto_attach_error`, and exits with degraded-success status code `2`.
- `agents launch` likewise accepts `--workdir`; when the launch source resolves from a Houmao project, that source project stays authoritative for overlay-local defaults even if the runtime cwd points somewhere else.
- `agents join` now uses `--workdir` instead of `--working-directory`; when omitted, the adopted cwd comes from tmux window `0`, pane `0`.

#### `project mailbox`

`project mailbox` mirrors the generic mailbox-root CLI, but automatically targets `mailbox/` under the active overlay root selected by `HOUMAO_PROJECT_OVERLAY_DIR` or ambient discovery under `HOUMAO_PROJECT_OVERLAY_DISCOVERY_MODE`.

| Subcommand | Description |
|---|---|
| `init`, `status`, `register`, `unregister`, `repair`, `cleanup` | Perform mailbox-root lifecycle operations against `.houmao/mailbox`. |
| `accounts list|get` | Inspect mailbox registrations under the project mailbox root. |
| `messages list|get` | Inspect structural message projections under the project mailbox root. |

`project mailbox register` mirrors the generic mailbox overwrite-confirmation contract, including interactive overwrite prompts and `--yes` for non-interactive replacement.

`project mailbox messages list|get` follows the same structural-only contract as `houmao-mgr mailbox messages list|get`; use `houmao-mgr agents mail ...` when the workflow needs actor-scoped unread/read follow-up state.

### `server` — Server lifecycle management

```
houmao-mgr server [OPTIONS] COMMAND [ARGS]...
```

Manage supported pair-authority lifecycle and houmao-server sessions.

#### `server start`

Start houmao-server in detached or explicit foreground mode.

```
houmao-mgr server start [OPTIONS]
```

**Options:**

| Option | Description |
|---|---|
| `--foreground` | Run the server in the foreground instead of detaching. |
| `--api-base-url TEXT` | Base URL for the server API. |
| `--runtime-root PATH` | Root directory for runtime state. |
| `--watch-poll-interval-seconds FLOAT` | Polling interval for the session watcher. |
| `--supported-tui-process TEXT` | TUI process name the server should recognize. May be specified multiple times. |
| `--startup-child TEXT` | Child process to launch on server startup. |

#### `server status`

Show server health and a compact active-session summary.

```
houmao-mgr server status [OPTIONS]
```

---

**Deprecated entrypoints:** `houmao-cli` and `houmao-cao-server` are deprecated compatibility entrypoints. Use `houmao-mgr` and `houmao-server`/`houmao-passive-server` instead.
