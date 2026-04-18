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
| `gateway mail-notifier status|enable|disable` | Inspect or control live gateway mail-notifier behavior. |

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
- Successful managed-agent stop responses include `manifest_path` and `session_root` when the resolved target exposes local manifest authority; prefer those path locators for explicit post-stop cleanup because the live shared-registry record may be gone.
- When `--agent-id` or `--agent-name` cleanup finds no fresh shared-registry record, it scans the effective local runtime root for exactly one stopped session manifest with the matching identity and fails explicitly on ambiguity or no match.
- Every cleanup command supports `--dry-run` and reports `planned_actions`, `applied_actions`, `blocked_actions`, and `preserved_actions` in one normalized payload. Plain and fancy modes print populated action buckets line by line, while `--print-json` preserves the machine-readable JSON shape.

`agents launch` source-selector and launch-profile rules:

- `agents launch` accepts exactly one of `--agents <selector>` and `--launch-profile <name>`. The two are mutually exclusive and one is required.
- `--agents` is the direct recipe selector form. The effective provider defaults to `claude_code` when `--provider` is omitted.
- `--launch-profile` resolves the named launch profile from the active project overlay and rejects easy `project easy profile ...` selections; only explicit recipe-backed launch profiles (`profile_lane=launch_profile`) are accepted.
- A launch-profile-backed launch derives the source recipe from the stored profile, then composes effective inputs in the precedence order: source recipe defaults → launch-profile defaults → direct CLI overrides.
- Direct overrides such as `--agent-name`, `--agent-id`, `--auth`, and `--workdir` apply to one launch and never rewrite the stored launch profile.
- `--force [keep-stale|clean]` is a launch-owned takeover flag for replacing an existing live local owner of the resolved managed identity. Omitting `--force` keeps the current owner in place and fails the new launch on that conflict.
- Bare `--force` means `keep-stale`. Houmao stops the predecessor first, reuses the predecessor managed home in place, and leaves untouched stale artifacts alone. If leftover stale files break the replacement launch, Houmao does not scrub or repair them automatically.
- `--force clean` is the explicit destructive mode. Houmao stops the predecessor, removes predecessor-owned replaceable launch artifacts such as the managed home, session root, job dir, and safe private mailbox paths, and then rebuilds from a clean managed-home state.
- Force takeover remains identity-scoped rather than tmux-name-scoped and never rewrites the stored launch profile.
- `--managed-header` and `--no-managed-header` are mutually exclusive one-shot overrides for the Houmao-managed prompt header. For what the header contains and the full prompt composition order, see [Managed Launch Prompt Header](../run-phase/managed-prompt-header.md).
- When neither managed-header flag is supplied, `agents launch` inherits managed-header policy from the selected launch profile when one is present; otherwise it falls back to the default enabled behavior.
- Direct managed-header override wins over stored launch-profile policy for the current launch only and does not rewrite the stored profile.
- `agents launch` also accepts repeatable `--managed-header-section SECTION=enabled|disabled` one-shot section overrides. These win over stored profile section policy for the named section and do not rewrite the stored profile. The supported section names are `identity`, `memo-cue`, `houmao-runtime-guidance`, `automation-notice`, `task-reminder`, and `mail-ack`.
- `--append-system-prompt-text` and `--append-system-prompt-file` are mutually exclusive one-shot prompt appendix inputs. They append after launch-profile overlay resolution for the current launch only and never rewrite the source role prompt or the stored launch profile.
- `agents launch` accepts `--workdir` to override the launched agent runtime cwd; when omitted, the runtime cwd defaults to the invocation cwd. When the launch source resolves from a Houmao project, that source project stays authoritative for overlay-local defaults even if the runtime cwd points somewhere else.
- `agents launch` accepts `--model` and `--reasoning-level` as launch-owned model-selection flags. `--model` is a tool-agnostic name that resolves through the provider mapping. `--reasoning-level` is a tool/model-specific preset index rather than a portable `1..10` knob. Both apply to the current launch only and do not rewrite the stored launch profile.
- `--provider` defaults from the resolved launch-profile recipe when one tool family is determined by that source. Supplying `--provider` together with `--launch-profile` is accepted only when it matches the resolved source; otherwise the command fails clearly before build.
- Launch-profile-stored fields that flow through the manifest into runtime launch resolution include managed-agent identity defaults, working directory, auth override selected by display name, prompt-mode override, durable env records, declarative mailbox config, headless and gateway posture, the managed-header whole-header policy, managed-header section policy, the prompt overlay, any stored memo seed, and secret-free relaunch chat-session policy. Stored memo seeds apply before prompt composition and provider startup; direct `agents launch --agents ...` launches do not apply one because no reusable launch profile was selected. Stored relaunch chat-session policy does not affect first launch; it is used by later `agents relaunch` unless that relaunch supplies a direct chat-session override. The stored auth relationship is catalog-backed, so later auth rename stays valid. Prompt composition order is source role prompt → prompt overlay resolution → launch appendix append when present → structured render into `<houmao_system_prompt>` → backend-specific role injection.
- For the conceptual model that ties `agents launch --launch-profile` to easy `project easy profile` and to the broader launch-profile object family, see [Launch Profiles](../../getting-started/launch-profiles.md).

`agents relaunch` chat-session selection:

- `agents relaunch` accepts optional `--chat-session-mode {new|tool_last_or_new|exact}` and `--chat-session-id <provider-session-id>`.
- When omitted, relaunch uses the stored launch-profile relaunch policy when the running agent was launched from one; otherwise it starts a fresh provider chat.
- `--chat-session-mode new` forces a fresh provider chat for this relaunch only.
- `--chat-session-mode tool_last_or_new` translates to provider-native latest-chat continuation for supported TUI and headless surfaces: Codex uses `resume --last`, Claude uses `--continue`, and Gemini uses `--resume latest`.
- `--chat-session-mode exact --chat-session-id <id>` resumes a provider session id exactly for this relaunch only. `--chat-session-id` is rejected unless the mode is `exact`.
- For TUI relaunch, Houmao starts the provider TUI with native continuation flags and suppresses replay of bootstrap-message role injection when the selected mode resumes an existing provider chat. For headless relaunch, Houmao records the selector for the next submitted prompt rather than starting a provider turn during relaunch.

`agents prompt` request-scoped headless execution overrides:

- `agents prompt` accepts optional `--model TEXT` and `--reasoning-level INTEGER` request-scoped headless execution overrides. `--model` is a tool-agnostic name that resolves through the provider mapping used by launch-owned model selection. `--reasoning-level` is a tool/model-specific preset index rather than a portable `1..10` knob.
- The override flags apply to exactly the submitted prompt. They do not mutate launch profiles, recipes, specialists, manifests, stored easy profiles, or any other live session defaults, and they do not persist beyond the submission.
- When the resolved target is a TUI-backed session, the command rejects `--model` and `--reasoning-level` clearly rather than silently dropping them. Only request-scoped headless prompt routes accept the overrides.
- Partial overrides are supported: supplying `--reasoning-level` without `--model` merges with the launch-resolved model defaults through the shared headless resolution helper rather than resetting fields that were not explicitly overridden. Supplying neither leaves the launch-resolved defaults in effect.
- Higher unused reasoning numbers saturate to the highest maintained Houmao preset for the resolved tool/model ladder. `0` means explicit off only for ladders that support it, such as non-Gemini-3 Gemini budget presets and any Codex model ladder that explicitly exposes off.
- Current maintained ladders are: Claude `1=low`, `2=medium`, `3=high`, optional `4=max`; current Codex coding models such as `gpt-5.4`, `gpt-5.3-codex`, and `gpt-5.2-codex` use `1=low`, `2=medium`, `3=high`, `4=xhigh`; Gemini uses documented Houmao preset tables per model family and may map one level to multiple native Gemini thinking settings together. Codex `minimal` is projected only when the resolved Codex model ladder explicitly includes it.
- If you need finer native control than those Houmao presets provide, omit `--reasoning-level` and manage native tool config or environment directly.
- The same override contract applies to `agents turn submit` and `agents gateway prompt`; for the dedicated per-command option tables, see [agents turn](agents-turn.md#submit) and [agents gateway](agents-gateway.md#prompt). The managed-agent HTTP payload shape is described in [Managed Agent API](../managed_agent_api.md).

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
| `clear-messages` | Clear delivered message content and derived message state while preserving mailbox registrations. |
| `export` | Export selected mailbox accounts and indexed messages into a portable archive directory. |

`mailbox register` keeps the existing `safe`, `force`, and `stash` mode vocabulary. When a requested registration would replace existing durable mailbox state or an occupying mailbox entry artifact, the command prompts before destructive replacement on interactive terminals and accepts `--yes` for non-interactive overwrite confirmation.

`mailbox messages list|get` is structural inspection over canonical message metadata plus address-scoped projection metadata. Participant-local mutable state such as `read`, `starred`, `archived`, and `deleted` belongs on actor-scoped `houmao-mgr agents mail ...` workflows rather than this operator/admin surface.

`mailbox clear-messages` is the destructive whole-root message reset. It clears delivered filesystem mail, message projections, mailbox-local message/thread state, and mailbox-owned managed-copy attachments while preserving mailbox registrations and account directories. Use `--dry-run` to preview and `--yes` for non-interactive confirmation; external `path_ref` attachment targets are not deleted.

`mailbox export` is the maintained archive path for filesystem mailbox roots. It requires `--output-dir <dir>` plus an explicit account scope: either `--all-accounts` or one or more `--address <full-address>` values. The output directory must not already exist. The default `--symlink-mode materialize` writes regular files and directories, including materialized projection links and symlink-backed private account directories, and verifies the archive contains no symlinks. Use `--symlink-mode preserve` only when you explicitly want archive-internal relative projection symlinks and the target filesystem supports symlink creation. The archive root contains `manifest.json`, canonical messages under `messages/`, selected account metadata and mailbox-local state under `accounts/`, and copied mailbox-owned managed-copy attachments under `attachments/managed/`; external `path_ref` targets are recorded in the manifest instead of copied. Prefer this command over raw recursive mailbox-root copying when preparing an archive.

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

### `credentials` — Dedicated credential management

```
houmao-mgr credentials [OPTIONS] COMMAND [ARGS]...
```

`houmao-mgr credentials` is the first-class top-level credential-management surface for Claude, Codex, and Gemini. It is the canonical entry point for managing credential contents and names, either through the active Houmao project overlay or through a plain agent-definition directory selected with `--agent-def-dir <path>`.

For a project-scoped view that always targets the active overlay without an explicit selector, use the [`project credentials`](#project-repo-local-houmao-project-overlays) wrapper — see `project credentials <tool> ...` below. Both surfaces share semantics, and the project-scoped wrapper is the preferred entry point when an active overlay is present.

#### Tool subcommands

| Subcommand | Description |
|---|---|
| `claude` | Manage Claude credentials through either the active project overlay or a selected plain agent-definition directory. |
| `codex` | Manage Codex credentials through either the active project overlay or a selected plain agent-definition directory. |
| `gemini` | Manage Gemini credentials through either the active project overlay or a selected plain agent-definition directory. |

Each tool subcommand exposes the same credential-management verbs:

| Verb | Description |
|---|---|
| `list` | List credential names for one supported tool. |
| `get` | Inspect one credential safely as structured data. `--name` is required. |
| `add` | Create one credential. `--name` is required plus the tool-specific credential input flags. |
| `set` | Update one existing credential. `--name` is required; only supplied input flags are updated, other stored fields are preserved. |
| `login` | Run the vendor CLI login flow in an isolated temporary provider home, then import the resulting auth file into Houmao storage. `--name` is required. |
| `remove` | Remove one credential by `--name`. |
| `rename` | Rename one credential from `--name` to `--to`. For project-overlay credentials the underlying auth-profile identity is preserved; stored launch-profile auth relationships remain valid after rename. |

#### Target selector

Every `credentials <tool> ...` verb accepts one selector:

| Option | Description |
|---|---|
| `--project` | Resolve credentials through the active Houmao project overlay. Default when no selector is supplied and an overlay is discoverable. |
| `--agent-def-dir DIRECTORY` | Manage credentials in the selected plain agent-definition directory instead of a project overlay. This is the escape hatch for tool homes that do not use a Houmao project overlay. |

`--project` and `--agent-def-dir` are mutually exclusive. When `--agent-def-dir` is supplied, the command operates on the filesystem-backed `tools/<tool>/auth/<name>/` layout inside that agent-definition directory. When `--project` is supplied (or defaulted), the command operates on the catalog-backed project overlay with display-name semantics and opaque bundle refs under `.houmao/content/auth/<tool>/<bundle-ref>/`.

#### Credential login helper

Use `login` when you need to obtain fresh provider auth files for a different Claude, Codex, or Gemini account and import them into Houmao:

```text
houmao-mgr credentials [--project|--agent-def-dir <path>] <tool> login --name <credential-name>
houmao-mgr project credentials <tool> login --name <credential-name>
```

By default, `login` creates a new credential and fails if that credential name already exists. Pass `--update` only when you intentionally want to replace the existing stored auth files through the same patch-preserving update path as `set`.

Common options:

| Option | Description |
|---|---|
| `--name TEXT` | Credential display name or direct-dir credential directory name. Required. |
| `--update` | Update an existing credential instead of creating a new one. |
| `--keep-temp-home` | Preserve the temporary provider home after a successful import and report its path. |
| `--inherit-auth-env` | Do not scrub common provider auth-related environment variables for the login process. The default is to scrub them so the provider CLI does not silently reuse the current API-key or token lane. |

Provider mapping:

| Tool | Isolated home | Default login command | Imported artifact |
|---|---|---|---|
| Claude | `CLAUDE_CONFIG_DIR=<temp-home>` | `claude auth login` | `<temp-home>/.credentials.json` plus `<temp-home>/.claude.json` when present |
| Codex | `CODEX_HOME=<temp-home>` | `codex login --device-auth` | `<temp-home>/auth.json` |
| Gemini | `GEMINI_CLI_HOME=<temp-home>` | interactive `gemini` OAuth flow | `<temp-home>/.gemini/oauth_creds.json` |

Provider-specific options:

| Tool | Options |
|---|---|
| Claude | `--claudeai`, `--console`, `--email TEXT`, and `--sso` are passed to `claude auth login`. |
| Codex | `--browser` uses ordinary `codex login` browser mode instead of the default device-auth mode. |
| Gemini | `--no-browser` sets `NO_BROWSER=true` for the Gemini OAuth flow. Gemini may require an interactive session; finish the browser or manual-code login and exit Gemini so Houmao can import `oauth_creds.json`. |

The helper invokes the installed provider CLI with inherited terminal I/O, so browser, device-code, console, and paste-back prompts remain owned by the provider tool. Houmao validates the expected auth artifact after the provider command exits, imports it through the existing credential storage contract, and deletes the temporary provider home after a successful import by default. If provider login fails, the expected artifact is missing, or Houmao import fails, the command preserves the temporary provider home and reports its path for diagnosis or manual recovery.

#### Per-tool credential input flags

The per-tool input flags on `credentials <tool> add` and `credentials <tool> set` mirror the Click decorators in `src/houmao/srv_ctrl/commands/credentials.py` and stay aligned with the corresponding `project credentials` surface.

**Claude (`credentials claude add|set`)**:

| Option | Description |
|---|---|
| `--api-key TEXT` | Value for `ANTHROPIC_API_KEY`. |
| `--auth-token TEXT` | Value for `ANTHROPIC_AUTH_TOKEN`. |
| `--oauth-token TEXT` | Value for `CLAUDE_CODE_OAUTH_TOKEN`. |
| `--base-url TEXT` | Value for `ANTHROPIC_BASE_URL`. |
| `--model TEXT` | Value for `ANTHROPIC_MODEL`. |
| `--small-fast-model TEXT` | Value for `ANTHROPIC_SMALL_FAST_MODEL`. |
| `--subagent-model TEXT` | Value for `CLAUDE_CODE_SUBAGENT_MODEL`. |
| `--default-opus-model TEXT`, `--default-sonnet-model TEXT`, `--default-haiku-model TEXT` | Vendor-native default-model env overrides for Claude. |
| `--config-dir DIRECTORY` | Optional Claude config dir to import vendor login state from (`.credentials.json` plus companion `.claude.json` when present). |
| `--state-template-file FILE` | Optional Claude bootstrap state template JSON stored alongside the credential bundle. This is bootstrap state, not a credential-providing method. |

Cross-reference: see [Claude Vendor Login Files](../claude-vendor-login-files.md) for the file-handling rules and the local smoke-validation workflow.

**Codex (`credentials codex add|set`)**:

| Option | Description |
|---|---|
| `--api-key TEXT` | Value for `OPENAI_API_KEY`. |
| `--base-url TEXT` | Value for `OPENAI_BASE_URL`. |
| `--org-id TEXT` | Value for `OPENAI_ORG_ID`. |
| `--auth-json FILE` | Optional Codex `auth.json` login-state file stored in the credential bundle. |

**Gemini (`credentials gemini add|set`)**:

| Option | Description |
|---|---|
| `--api-key TEXT` | Value for `GEMINI_API_KEY`. |
| `--google-api-key TEXT` | Value for `GOOGLE_API_KEY`. |
| `--base-url TEXT` | Value for `GOOGLE_GEMINI_BASE_URL`. |
| `--use-vertex-ai` | Store `GOOGLE_GENAI_USE_VERTEXAI=true` in the credential bundle env file. |
| `--oauth-creds FILE` | Optional Gemini CLI `oauth_creds.json` file stored in the credential bundle. |

Notes:

- `credentials` is the supported credential-management surface. The retired `project agents tools <tool> auth ...` CRUD subtree is no longer maintained; use `credentials ...` or `project credentials ...` instead.
- `add` and `set` are patch-preserving: setting one input flag does not implicitly delete other stored fields on the same credential. Refreshing `--config-dir` replaces the imported Claude vendor login files as one maintained set.
- `login` is the supported way to let Houmao own the temp-home lifecycle around provider login and import. Do not manually copy fresh vendor login files into `.houmao/content/auth/`, `.houmao/agents/tools/<tool>/auth/`, or `tools/<tool>/auth/<name>/` for this ordinary workflow.
- Auth-owned model env on Claude is separate from launch-owned model selection. Use `credentials claude add|set --model <value>` only when you need to pin `ANTHROPIC_MODEL` in the credential bundle; use the launch-owned `--model` on `agents launch` / `project easy specialist create|set` / `project easy profile create|set` / `project agents launch-profiles add|set` when you are selecting a Houmao launch-time model through the provider mapping.
- For the agent-driven workflow that wraps this surface, see the packaged [`houmao-credential-mgr`](../../getting-started/system-skills-overview.md) system skill. For the easy-lane credential notes exposed through `project easy specialist create` and `project credentials`, see the `project credentials claude add|set` notes under the [`project`](#project-repo-local-houmao-project-overlays) command group below.

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
- managed brain build and `agents join` use the same packaged catalog and installer internally

For the detailed catalog, projection, and ownership contract, see [system-skills](system-skills.md).

Startup note:

- `houmao-mgr` builds one root Click command tree at process startup, so a stale import in any registered command group can block `houmao-mgr --version`, root help, and unrelated subcommands before dispatch

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
- `project init` does not create `agents/`, `mailbox/`, or `easy/` under the selected overlay root by default.

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
- `launch-profiles ...` owns reusable recipe-backed birth-time launch configuration, including managed-agent identity defaults, working directory, auth override by display name, prompt-mode override, durable env records, declarative mailbox config, launch posture, an optional prompt overlay, and an optional memo seed. The stored auth relationship resolves through auth-profile identity, so later auth rename does not break existing launch profiles. For the shared semantic model that ties these to easy profiles, see [Launch Profiles](../../getting-started/launch-profiles.md).
- Managed launches prepend a short Houmao-owned prompt header by default. `houmao-mgr` is the canonical direct Houmao interface named by that header, and the stored launch-profile policy plus launch-time flags determine whether the header is enabled for a given launch. See [Managed Launch Prompt Header](../run-phase/managed-prompt-header.md) for what the header contains and the prompt composition order.
- Credential CRUD is no longer part of `project agents tools <tool> ...`. Use the dedicated [`credentials`](#credentials-dedicated-credential-management) and [`project credentials`](#project-repo-local-houmao-project-overlays) command families for add, set, rename, remove, get, and list on Claude, Codex, and Gemini credentials. `project agents tools <tool> get` and `tools <tool> setups ...` remain focused on tool subtree inspection and setup bundle maintenance.

`project agents recipes` notes:

- `recipes add` requires `--name`, `--role`, `--tool`, accepts repeatable `--skill`, optional `--auth`, optional `--setup` (defaults to `default`), and optional `--prompt-mode` (`unattended` or `as_is`; defaults to `unattended` when omitted).
- `recipes set` patches without dropping advanced blocks. It supports `--role`, `--tool`, `--setup`, `--auth`, `--clear-auth`, repeatable `--add-skill` and `--remove-skill`, `--clear-skills`, `--prompt-mode`, and `--clear-prompt-mode`. `mailbox` and `extra` blocks already present in a recipe are preserved.
- The system rejects creation or mutation that would make two recipes share the same `(role, tool, setup)` tuple.
- `recipes remove` deletes the named recipe file but does not delete any launch profile that references it; remove referencing launch profiles separately when needed.

`project agents launch-profiles` notes:

- `launch-profiles add` requires `--name` and `--recipe`. It accepts: `--agent-name`, `--agent-id`, `--workdir`, `--auth`, `--prompt-mode {unattended|as_is}`, repeatable `--env-set NAME=value`, mailbox flags (`--mail-transport {filesystem|stalwart}`, `--mail-principal-id`, `--mail-address`, `--mail-root`, `--mail-base-url`, `--mail-jmap-url`, `--mail-management-url`), launch posture flags (`--headless`, `--no-gateway`, `--gateway-port`), relaunch chat-session flags (`--relaunch-chat-session-mode {new|tool_last_or_new|exact}`, `--relaunch-chat-session-id`), prompt-overlay flags (`--prompt-overlay-mode {append|replace}`, `--prompt-overlay-text`, `--prompt-overlay-file`), and memo-seed flags (`--memo-seed-text`, `--memo-seed-file`, `--memo-seed-dir`).
- `launch-profiles add` rejects an existing profile name by default. Passing `--yes` confirms same-lane replacement of an existing explicit launch profile; replacement uses create semantics, so omitted optional fields are cleared instead of preserved. `--yes` does not allow replacing an easy profile with an explicit launch profile.
- `launch-profiles add` also accepts `--managed-header` or `--no-managed-header` to store explicit managed-header whole-header policy, plus repeatable `--managed-header-section SECTION=enabled|disabled` to store section policy. Omitting whole-header flags stores `inherit`; omitting section flags stores no section entries. For the conceptual model behind these flags, see [Managed Launch Prompt Header](../run-phase/managed-prompt-header.md).
- `launch-profiles set` patches without dropping unspecified advanced blocks and exposes matching `--clear-*` flags for nullable fields (`--clear-agent-name`, `--clear-agent-id`, `--clear-workdir`, `--clear-auth`, `--clear-prompt-mode`, `--clear-env`, `--clear-mailbox`, `--clear-headless`, `--clear-relaunch-chat-session`, `--clear-managed-header`, `--clear-managed-header-section`, `--clear-managed-header-sections`, `--clear-prompt-overlay`, `--clear-memo-seed`).
- Stored relaunch chat-session policy is applied only by future `agents relaunch` operations. `--relaunch-chat-session-mode exact` requires `--relaunch-chat-session-id`; ids are omitted for `new` and `tool_last_or_new`.
- Supplying a new `--memo-seed-text`, `--memo-seed-file`, or `--memo-seed-dir` source on `launch-profiles set` replaces the stored seed. `--clear-memo-seed` cannot be combined with a new memo seed source.
- Memo seeds always replace only the managed-memory components represented by the seed source. `--memo-seed-text` and `--memo-seed-file` touch only `houmao-memo.md`; `--memo-seed-dir` touches `houmao-memo.md` only when that file is present and touches pages only when `pages/` is present. `--memo-seed-text ''` stores an intentional empty memo seed without clearing pages. `--clear-memo-seed` removes stored seed configuration instead of writing an empty memo.
- `launch-profiles set` also accepts `--managed-header` or `--no-managed-header` and repeatable `--managed-header-section SECTION=enabled|disabled`. Whole-header flags are mutually exclusive, `--clear-managed-header` returns the stored whole-header field to `inherit`, `--clear-managed-header-section SECTION` removes one stored section entry, and `--clear-managed-header-sections` removes all stored section entries.
- `launch-profiles list` accepts optional `--recipe` and `--tool` filters when those identities are derivable from the referenced recipe.
- `launch-profiles remove` deletes one launch-profile resource without deleting the referenced recipe.
- Launch profiles authored here are recipe-backed and explicit. They are stored as the same kind of catalog object that backs easy `project easy profile ...`, but the explicit lane keeps the lower-level launch contract visible by intent.

`project credentials claude add|set` notes:

- Claude supports maintained auth inputs `--api-key`, `--auth-token`, `--oauth-token`, optional `--config-dir`, optional `--base-url`, and optional model-selection env values.
- `--config-dir` imports Claude vendor login state from a maintained Claude config root by copying `.credentials.json` and companion `.claude.json` when present.
- `--state-template-file` remains optional Claude bootstrap state only and is not a credential-providing method.
- See [Claude Vendor Login Files](../claude-vendor-login-files.md) for the file-handling rules and the local smoke-validation workflow.

#### `project easy`

`project easy` is the higher-level project authoring and runtime-instance path.

| Subcommand | Description |
|---|---|
| `specialist create` | Persist one specialist in `catalog.sqlite`, snapshot prompt/auth/skill payloads into `content/`, and materialize the needed `agents/` compatibility projection under the active overlay root. |
| `specialist set` | Patch one existing specialist without recreating it. Preserves unspecified prompt, skill, setup, credential, launch-model, prompt-mode, and env fields, then rematerializes the compatibility projection. |
| `specialist list|get|remove` | Inspect or remove persisted specialist definitions without forcing manual tree inspection; `get` reports stored launch config such as `launch.prompt_mode` and `launch.env_records`. |
| `profile create` | Persist one specialist-backed easy profile that captures reusable birth-time launch defaults over exactly one specialist. Stored in the shared launch-profile catalog family with `profile_lane=easy_profile`. |
| `profile list|get|set|remove` | Inspect, patch, or remove persisted easy profiles. `get` reports the source specialist plus the stored easy-profile launch defaults. `set` patches stored defaults without dropping unspecified fields. `remove` deletes the easy profile without removing the specialist it referenced. |
| `instance launch` | Launch one managed agent from either a compiled specialist (`--specialist`) or a stored easy profile (`--profile`). The two selectors are mutually exclusive and exactly one is required. |
| `instance stop` | Stop one managed agent through the project-aware easy instance surface. |
| `instance list|get` | View existing managed-agent runtime state as project-local specialist instances. `list` and `get` also report the originating easy-profile identity when runtime-backed state makes it resolvable. |

`project easy specialist create` notes:

- `--name` and `--tool` are required.
- `--credential` is optional; when omitted, Houmao uses `<specialist-name>-creds` as the auth display name.
- `--system-prompt` and `--system-prompt-file` are both optional; provide at most one.
- `--no-unattended` opts out of the easy unattended default and persists `launch.prompt_mode: as_is` for that specialist.
- repeatable `--env-set NAME=value` stores durable specialist-owned launch env under `launch.env_records`.
- `--model` and `--reasoning-level` are the supported launch-owned model-selection surfaces. `--reasoning-level` is a tool/model-specific preset index rather than a portable `1..10` knob.
- when the selected specialist name already exists, `specialist create` prompts before replacing the specialist-owned prompt and recipe projection and accepts `--yes` for non-interactive replacement.
- If neither system-prompt option is supplied, the compiled role remains valid and the runtime treats it as having no startup prompt content.
- maintained easy launch paths persist `launch.prompt_mode: unattended` by default in both the catalog-backed specialist launch payload and the generated compatibility recipe projected under `.houmao/agents/presets/`, including Gemini's headless-only easy lane.
- specialist `--env-set` is separate from credential env and rejects auth-owned or Houmao-owned reserved env names.
- Claude credential lanes use the same credential semantics in both `project credentials claude add|set` and `project easy specialist create --tool claude`, but the flag names differ: the dedicated credential surface uses unprefixed names (`--api-key`, `--auth-token`, `--oauth-token`, `--config-dir`, `--base-url`) while the easy-specialist surface uses prefixed names (`--api-key`, `--claude-auth-token`, `--claude-oauth-token`, `--claude-config-dir`, `--base-url`). Model selection on the easy surface is now unified under `--model` plus optional `--reasoning-level`, with `--claude-model` retained only as a compatibility alias for `--model`.
- Claude auth bundle updates are patch-preserving: setting `--claude-oauth-token`, `--claude-config-dir`, or `--base-url` does not implicitly delete other stored Claude auth inputs, and refreshing `--claude-config-dir` replaces the imported vendor login files as one maintained set. `--claude-model` no longer writes auth-owned model env; it resolves into launch-owned model selection.
- `--claude-state-template-file` remains optional Claude bootstrap state and is not itself a credential-providing method on the easy-specialist surface.
- The maintained vendor-login lane is still directory-based. Pass `--config-dir` or `--claude-config-dir`, not separate `.credentials.json` or `.claude.json` file flags.
- Detailed vendor-native model tuning belongs in the relevant specialist or credential skill documentation rather than the core CLI reference.
- Gemini credential lanes use the same contract in both `project credentials gemini add|set` and `project easy specialist create --tool gemini`: `--api-key`, optional `--base-url`, and optional `--oauth-creds` or `--gemini-oauth-creds`.
- Gemini auth bundle updates are patch-preserving: setting `--base-url` or `--oauth-creds` does not implicitly delete other Gemini auth inputs that were already stored.
- The project-local catalog is the source of truth; `agents/` under the active overlay root is a compatibility projection that is materialized as needed.

`project easy specialist set` notes:

- `--name` is required and must identify an existing specialist. At least one update or clear flag is required.
- Patchable fields include prompt (`--system-prompt`, `--system-prompt-file`, `--clear-system-prompt`), skills (`--with-skill`, `--add-skill`, `--remove-skill`, `--clear-skills`), setup (`--setup`), credential (`--credential`), prompt mode (`--prompt-mode`, `--clear-prompt-mode`), launch-owned model (`--model`, `--clear-model`, `--reasoning-level`, `--clear-reasoning-level`), and persistent env (`--env-set`, `--clear-env`).
- `--env-set` replaces the stored specialist env mapping with the repeated `NAME=value` records supplied on that command. Use `--clear-env` to remove the mapping.
- `--with-skill <dir>` imports a skill directory and adds it to the specialist. `--add-skill <name>` adds an already projected project skill by name. `--remove-skill <name>` removes that skill from the specialist definition; shared projected skill content is not deleted just because one specialist stops referencing it.
- `--setup <name>` switches to another setup bundle for the specialist's current tool lane. When the preset name changes, the old specialist-owned projected preset file is removed after the catalog projection is materialized.
- `--credential <name>` selects an existing credential display name for the specialist's current tool lane. It does not create or mutate credential bundles.
- `specialist set` does not rename specialists and does not change the tool lane; create a new specialist when either identity should change.
- Updates affect future launches and profile resolutions. Already-running easy instances are not mutated in place.

`project easy profile create` notes:

- `--name` and `--specialist` are required. The named profile targets exactly one existing specialist.
- Optional birth-time defaults: `--agent-name`, `--agent-id`, `--workdir`, `--auth`, `--prompt-mode {unattended|as_is}`, `--model`, `--reasoning-level`, repeatable `--env-set NAME=value`, mailbox flags (`--mail-transport {filesystem|stalwart}`, `--mail-principal-id`, `--mail-address`, `--mail-root`, `--mail-base-url`, `--mail-jmap-url`, `--mail-management-url`), launch posture flags (`--headless`, `--no-gateway`, `--gateway-port`), relaunch chat-session flags (`--relaunch-chat-session-mode {new|tool_last_or_new|exact}`, `--relaunch-chat-session-id`), managed-header flags (`--managed-header`, `--no-managed-header`, repeatable `--managed-header-section SECTION=enabled|disabled`), prompt-overlay flags (`--prompt-overlay-mode {append|replace}`, `--prompt-overlay-text`, `--prompt-overlay-file`), and memo-seed flags (`--memo-seed-text`, `--memo-seed-file`, `--memo-seed-dir`).
- `project easy profile create` rejects an existing profile name by default. Passing `--yes` confirms same-lane replacement of an existing easy profile; replacement uses create semantics, so omitted optional fields are cleared instead of preserved. `--yes` does not allow replacing an explicit launch profile with an easy profile.
- `project easy profile set --name <profile>` patches stored defaults on an existing easy profile while preserving unspecified fields. It accepts the same stored-default field families as explicit `launch-profiles set`, including clear flags such as `--clear-agent-name`, `--clear-agent-id`, `--clear-workdir`, `--clear-auth`, `--clear-prompt-mode`, `--clear-env`, `--clear-mailbox`, `--clear-headless`, `--clear-relaunch-chat-session`, `--clear-managed-header`, `--clear-managed-header-section`, `--clear-managed-header-sections`, `--clear-prompt-overlay`, and `--clear-memo-seed`.
- Easy-profile memo seed semantics match explicit launch profiles: stored seeds replace only represented memo/pages components, and `--clear-memo-seed` removes stored seed configuration rather than seeding an empty memo.
- The persisted easy profile lives in the shared catalog launch-profile family with `profile_lane=easy_profile` and `source_kind=specialist`. It projects into the same compatibility tree (`.houmao/agents/launch-profiles/<name>.yaml`) used by explicit launch profiles.
- `--auth <name>` is display-name-oriented at the CLI, but the stored easy-profile relationship resolves through auth-profile identity so later `project credentials <tool> rename` continues to work.
- Omitting both managed-header flags on `project easy profile create` stores `inherit`, which falls back to the default enabled managed-header behavior later at launch time.
- When no active project overlay exists for the caller, `project easy profile create` ensures `<cwd>/.houmao` exists before persisting the profile (matching the `project easy specialist create` bootstrap behavior).
- `project easy profile remove` removes only the profile definition. It does not remove the specialist that the profile referenced.
- For the conceptual model that ties easy profiles to explicit launch profiles, see [Launch Profiles](../../getting-started/launch-profiles.md).

`project easy instance launch` notes:

- Exactly one of `--specialist` or `--profile` is required. The two selectors are mutually exclusive.
- `--specialist` selects a compiled specialist definition to launch from directly. `--name` is required when launching from `--specialist`.
- `--profile` selects a stored easy profile. The command derives the source specialist from that profile, applies easy-profile-stored defaults (managed-agent identity, workdir, auth override, prompt mode, durable env records, declarative mailbox config, headless/gateway posture, prompt overlay, and any stored memo seed), and uses the active project overlay as the authoritative source context. Auth is still rendered by display name even though the stored relationship is auth-profile-backed. `--name` may be omitted when the selected profile stores a default managed-agent name; otherwise it remains required.
- Stored easy-profile memo seeds apply their represented memo/pages components before prompt composition and provider startup. Direct `project easy instance launch --specialist ...` launches do not apply one because no reusable easy profile was selected, and there is no one-shot memo-seed override flag on the launch surface.
- Direct launch-time overrides such as `--auth`, `--workdir`, `--name`, `--mail-transport`, `--mail-root`, and `--mail-account-dir` win over easy-profile defaults but never rewrite the stored easy profile. The next launch from the same profile will see the original stored defaults again.
- `--force [keep-stale|clean]` is also available here and behaves the same as on `agents launch`, but only for the current easy-instance launch. Bare `--force` means `keep-stale`, which stops the predecessor and reuses the predecessor managed home while leaving untouched stale artifacts alone.
- `--force clean` stops the predecessor and removes predecessor-owned replaceable launch artifacts before rebuilding. Shared mailbox message history and unrelated operator-owned paths are preserved.
- Force mode never becomes part of specialist metadata or easy-profile storage.
- `--managed-header` and `--no-managed-header` are mutually exclusive one-shot overrides. They win over the stored easy-profile managed-header policy for the current launch only and never rewrite the stored easy profile.
- When neither managed-header flag is supplied, easy-instance launch inherits policy from the selected profile when one is present; otherwise it falls back to the default enabled behavior.
- `project easy instance launch` also accepts repeatable `--managed-header-section SECTION=enabled|disabled` one-shot section overrides. These win over stored easy-profile section policy for the named section and never rewrite the stored easy profile.
- `--append-system-prompt-text` and `--append-system-prompt-file` are mutually exclusive one-shot appendix inputs. They append after any resolved easy-profile prompt overlay and never rewrite the stored specialist or easy profile.
- Easy-instance inspection (`project easy instance list` and `project easy instance get`) reports the originating easy-profile identity in addition to the originating specialist when runtime-backed state makes both resolvable.
- `--name` is the managed-agent instance name and also seeds the default filesystem mailbox identity when mailbox association is enabled.
- unless `--no-gateway` is supplied, the easy surface now requests launch-time gateway attach by default on loopback (`127.0.0.1`) with a system-assigned port.
- by default, that easy auto-attach uses same-session foreground gateway execution and reports `gateway_execution_mode` plus `gateway_tmux_window_index` when foreground attach succeeds.
- `--gateway-port <port>` keeps the default easy gateway attach enabled for that launch, but requests the specified loopback listener port instead of a system-assigned port.
- `--gateway-background` keeps easy auto-attach enabled for that launch, but requests detached background gateway execution instead of the default foreground auxiliary-window execution.
- `--gateway-tui-watch-poll-interval-seconds`, `--gateway-tui-stability-threshold-seconds`, `--gateway-tui-completion-stability-seconds`, `--gateway-tui-unknown-to-stalled-timeout-seconds`, `--gateway-tui-stale-active-recovery-seconds`, and `--gateway-tui-final-stable-active-recovery-seconds` are positive-second one-shot overrides for the gateway-owned TUI tracker. They affect the current launch-time gateway attach and are not stored in launch profiles or easy profiles.
- `--no-gateway` is mutually exclusive with `--gateway-port`, `--gateway-background`, and any `--gateway-tui-*` override.
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
| `init`, `status`, `register`, `unregister`, `repair`, `cleanup`, `clear-messages`, `export` | Perform mailbox-root lifecycle operations against `.houmao/mailbox`. |
| `accounts list|get` | Inspect mailbox registrations under the project mailbox root. |
| `messages list|get` | Inspect structural message projections under the project mailbox root. |

`project mailbox register` mirrors the generic mailbox overwrite-confirmation contract, including interactive overwrite prompts and `--yes` for non-interactive replacement.

`project mailbox clear-messages` mirrors the generic delivered-message reset, but targets the selected overlay mailbox root automatically.

`project mailbox export --output-dir <dir> (--all-accounts | --address <full-address>...) [--symlink-mode materialize|preserve]` mirrors the generic export behavior, but targets `mailbox/` under the selected project overlay and includes the selected overlay details in the structured result.

`project mailbox messages list|get` follows the same structural-only contract as `houmao-mgr mailbox messages list|get`; use `houmao-mgr agents mail ...` when the workflow needs actor-scoped unread/read follow-up state.

### `internals` — Internal utility commands

```
houmao-mgr internals [OPTIONS] COMMAND [ARGS]...
```

Internal Houmao utility commands for agents and maintainers.

The primary subgroup is `internals graph`, which provides NetworkX-backed helpers for loop plan authoring, structural analysis, and low-level graph manipulation. All graph commands use NetworkX node-link JSON as their interchange format.

For the full subcommand reference, see [internals](internals.md).

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
