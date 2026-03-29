# houmao-mgr

Houmao pair CLI with native server and managed-agent command families.

`houmao-mgr` is the primary management CLI for local lifecycle, managed agents, mailbox administration, repo-local project overlays, and `houmao-server` control. It provides native command groups for agent orchestration, filesystem mailbox administration, brain construction, project bootstrap, server management, and administrative tasks.

## Synopsis

```
houmao-mgr [OPTIONS] COMMAND [ARGS]...
```

## Command Groups

### `admin` — Administrative commands

```
houmao-mgr admin [OPTIONS] COMMAND [ARGS]...
```

Administrative utilities for the Houmao environment.

For dedicated coverage, see [admin cleanup](admin-cleanup.md).

The canonical cleanup tree is `houmao-mgr admin cleanup registry` plus `houmao-mgr admin cleanup runtime {sessions,builds,logs,mailbox-credentials}`. Registry cleanup probes tmux-backed records locally by default and accepts `--no-tmux-check` for lease-only cleanup. `houmao-mgr admin cleanup-registry` remains available as a compatibility alias for the registry-only command.

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
| `launch` | Start a managed agent. Provisions a runtime home, builds the brain, and launches a live session. |
| `join` | Adopt an existing tmux-backed TUI or native headless logical session into Houmao managed-agent control. |
| `list`, `state` | Inspect locally discovered or pair-backed managed agents. |
| `prompt` | Send a prompt to a running agent session. |
| `stop`, `interrupt`, `relaunch` | Control the current managed-agent runtime posture. |
| `mail` | Check, send, or reply to inter-agent mail messages. |
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
- Inside a managed tmux session, omitting the selector resolves the current session from `AGENTSYS_MANIFEST_PATH` first and falls back to `AGENTSYS_AGENT_ID` plus shared registry when needed.
- `--current-session` forces same-session resolution and cannot be combined with `--agent-id`, `--agent-name`, or `--port`.
- `--port` is only supported with an explicit selector, because current-session mode uses the manifest-declared pair authority instead of retargeting another server.

Gateway TUI notes:

- `gateway tui state` and `gateway tui watch` read the exact raw gateway-owned tracked state rather than the transport-neutral `agents state` payload.
- `gateway tui history` returns bounded in-memory snapshot history from the live gateway tracker, not coarse managed-agent `/history`.
- `gateway tui note-prompt` records explicit prompt provenance on the live gateway tracker without enqueueing a gateway prompt request.

The preferred local serverless mailbox workflow is:

1. `houmao-mgr mailbox init --mailbox-root <path>`
2. `houmao-mgr agents launch ...` or `houmao-mgr agents join ...`
3. `houmao-mgr agents mailbox register --agent-name <name> --mailbox-root <path>`
4. `houmao-mgr agents mail ...`

For supported tmux-backed managed sessions, including sessions adopted through `houmao-mgr agents join`, `agents mailbox register` and `agents mailbox unregister` refresh the live mailbox projection without requiring relaunch solely for mailbox binding refresh. That remains true even when a joined session is controllable but non-relaunchable because no launch options were recorded, as long as Houmao can still update the session manifest and the owning tmux live mailbox projection safely. When a direct mailbox workflow needs the current binding set explicitly, resolve it through `pixi run python -m houmao.agents.mailbox_runtime_support resolve-live`. That helper prefers current process env, falls back to the owning tmux session env, and returns optional live `gateway.base_url` data for attached `/v1/mail/*` work.

Cleanup targeting rules:

- `agents cleanup session|logs|mailbox` accept exactly one of `--agent-id`, `--agent-name`, `--manifest-path`, or `--session-root`.
- Inside the target tmux session, omitting those options resolves the current session from `AGENTSYS_MANIFEST_PATH` first and `AGENTSYS_AGENT_ID` plus fresh shared-registry metadata second.
- Every cleanup command supports `--dry-run` and reports `planned_actions`, `applied_actions`, `blocked_actions`, and `preserved_actions` in one normalized JSON payload.

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
| `messages list|get` | Inspect mailbox-visible messages for one registered mailbox address. |
| `repair` | Rebuild one filesystem mailbox root's shared index state locally. |
| `cleanup` | Remove inactive or stashed mailbox registrations while preserving active registrations and canonical `messages/` history. |

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
| `--config-profile TEXT` | Secret-free configuration profile name. |
| `--cred-profile TEXT` | Local auth bundle name. |
| `--recipe TEXT` | Brain recipe name (resolves tool, skills, and profiles from a declarative preset). |
| `--runtime-root PATH` | Root directory for runtime homes. |
| `--home-id TEXT` | Explicit home identifier for the runtime home directory. |
| `--reuse-home` | Reuse an existing runtime home if one matches, instead of creating a new one. |
| `--launch-overrides TEXT` | Secret-free launch overrides to pass through to the tool adapter. |
| `--agent-name TEXT` | Human-readable agent name. |
| `--agent-id TEXT` | Explicit agent identifier. |

`brains build` resolves the effective agent-definition root with this precedence:

1. `--agent-def-dir`
2. `AGENTSYS_AGENT_DEF_DIR`
3. nearest ancestor `.houmao/houmao-config.toml`
4. legacy `<pwd>/.agentsys/agents`

### `project` — Repo-local Houmao project overlays

```
houmao-mgr project [OPTIONS] COMMAND [ARGS]...
```

Local operator workflow for bootstrapping and inspecting one repo-local `.houmao/` overlay.

Command shape:

```text
houmao-mgr project
├── init | status
├── agents
│   ├── roles ...
│   └── tools <tool> ...
├── easy
│   ├── specialist ...
│   └── instance ...
└── mailbox
    ├── init | status | register | unregister | repair | cleanup
    ├── accounts list|get
    └── messages list|get
```

#### Subcommands

| Subcommand | Description |
|---|---|
| `init` | Create or validate `.houmao/`, write `.houmao/houmao-config.toml`, write `.houmao/.gitignore`, create `.houmao/catalog.sqlite`, and create managed `.houmao/content/` roots. |
| `status` | Report whether a project overlay was discovered from the current directory, which catalog was found, and which agent-definition root is effective. |
| `agents` | Low-level filesystem-oriented management for the `.houmao/agents/` compatibility projection. |
| `easy` | Higher-level specialist and instance workflow persisted in `.houmao/catalog.sqlite` with file-backed payloads under `.houmao/content/`. |
| `mailbox` | Project-scoped wrapper over the generic mailbox-root CLI targeting `.houmao/mailbox`. |

Project overlay notes:

- `project init` targets the current working directory in v1.
- `.houmao/.gitignore` contains `*`, so the whole overlay stays local-only without editing the repo root `.gitignore`.
- `project status` uses nearest-ancestor discovery for `.houmao/houmao-config.toml`.
- `project init` creates `.houmao/catalog.sqlite` plus managed `.houmao/content/prompts/`, `.houmao/content/auth/`, `.houmao/content/skills/`, and `.houmao/content/setups/`.
- `project init` does not create `.houmao/agents/`, `.houmao/agents/compatibility-profiles/`, `.houmao/mailbox/`, or `.houmao/easy/` by default.
- `project init --with-compatibility-profiles` opts into pre-creating `.houmao/agents/compatibility-profiles/`.

#### `project agents`

`project agents` is the low-level maintenance surface for the compatibility projection tree under `.houmao/agents/`.

| Subcommand | Description |
|---|---|
| `roles list|get|init|scaffold|remove` | Inspect, create, scaffold, or delete role roots under `.houmao/agents/roles/`. |
| `roles presets list|get|add|remove` | Manage canonical preset files under `roles/<role>/presets/<tool>/<setup>.yaml`. |
| `tools <tool> get` | Inspect one tool subtree, including adapter, setup, and auth bundle summaries. |
| `tools <tool> setups list|get|add|remove` | Inspect or clone setup bundles under `.houmao/agents/tools/<tool>/setups/`. |
| `tools <tool> auth list|get|add|set|remove` | Manage project-local auth bundles under `.houmao/agents/tools/<tool>/auth/<name>/`. |

#### `project easy`

`project easy` is the higher-level project authoring and runtime-instance path.

| Subcommand | Description |
|---|---|
| `specialist create` | Persist one specialist in `.houmao/catalog.sqlite`, snapshot prompt/auth/skill payloads into `.houmao/content/`, and materialize the needed `.houmao/agents/` compatibility projection. |
| `specialist list|get|remove` | Inspect or remove persisted specialist definitions without forcing manual tree inspection. |
| `instance launch` | Launch one managed agent from a compiled specialist with required `--specialist` and `--name` inputs. |
| `instance stop` | Stop one managed agent through the project-aware easy instance surface. |
| `instance list|get` | View existing managed-agent runtime state as project-local specialist instances. |

`project easy specialist create` notes:

- `--name` and `--tool` are required.
- `--credential` is optional; when omitted, Houmao uses `<specialist-name>-creds`.
- `--system-prompt` and `--system-prompt-file` are both optional; provide at most one.
- If neither system-prompt option is supplied, the compiled role remains valid and the runtime treats it as having no startup prompt content.
- The project-local catalog is the source of truth; `.houmao/agents/` is a compatibility projection that is materialized as needed.

`project easy instance launch` notes:

- `--specialist` selects the compiled specialist definition to launch from.
- `--name` is the managed-agent instance name and also seeds the default filesystem mailbox identity when mailbox association is enabled.
- `--mail-transport filesystem` requires `--mail-root` and optionally accepts `--mail-account-dir` for a symlink-backed private mailbox directory.
- `--mail-account-dir` must resolve outside the shared mailbox root; safe launch fails if the address slot already exists as a real directory or as a symlink to a different target.
- `--mail-transport email` is reserved for a future real-email path and currently fails fast as not implemented.

#### `project mailbox`

`project mailbox` mirrors the generic mailbox-root CLI, but automatically targets the discovered project's `.houmao/mailbox` root.

| Subcommand | Description |
|---|---|
| `init`, `status`, `register`, `unregister`, `repair`, `cleanup` | Perform mailbox-root lifecycle operations against `.houmao/mailbox`. |
| `accounts list|get` | Inspect mailbox registrations under the project mailbox root. |
| `messages list|get` | Inspect mailbox-visible messages under the project mailbox root. |

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
