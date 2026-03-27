# houmao-mgr

Houmao pair CLI with native server and managed-agent command families.

`houmao-mgr` is the primary management CLI for local lifecycle, managed agents, mailbox administration, and `houmao-server` control. It provides native command groups for agent orchestration, filesystem mailbox administration, brain construction, server management, and administrative tasks.

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

The canonical cleanup tree is `houmao-mgr admin cleanup registry` plus `houmao-mgr admin cleanup runtime {sessions,builds,logs,mailbox-credentials}`. Registry cleanup probes tmux-backed records locally by default and accepts `--no-tmux-check` for lease-only cleanup. `houmao-mgr admin cleanup-registry` remains available as a compatibility alias for the registry-only command.

### `agents` — Agent lifecycle

```
houmao-mgr agents [OPTIONS] COMMAND [ARGS]...
```

Agent lifecycle: launch, terminate, observe, send-prompt, mail, join, gateway operations.

#### Subcommands

| Subcommand | Description |
|---|---|
| `launch` | Start a managed agent. Provisions a runtime home, builds the brain, and launches a live session. |
| `join` | Adopt an existing tmux-backed TUI or native headless logical session into Houmao managed-agent control. |
| `list`, `show`, `state` | Inspect locally discovered or pair-backed managed agents. |
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

- `gateway tui state` and `gateway tui watch` read the exact raw gateway-owned tracked state rather than the curated `agents show` payload.
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
| `--cred-profile TEXT` | Local credential profile name. |
| `--recipe TEXT` | Brain recipe name (resolves tool, skills, and profiles from a declarative preset). |
| `--runtime-root PATH` | Root directory for runtime homes. |
| `--home-id TEXT` | Explicit home identifier for the runtime home directory. |
| `--reuse-home` | Reuse an existing runtime home if one matches, instead of creating a new one. |
| `--launch-overrides TEXT` | Secret-free launch overrides to pass through to the tool adapter. |
| `--agent-name TEXT` | Human-readable agent name. |
| `--agent-id TEXT` | Explicit agent identifier. |

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

### `passthrough` — Passthrough utilities

```
houmao-mgr passthrough [OPTIONS] COMMAND [ARGS]...
```

Passthrough utilities for forwarding operations to underlying tools.

---

**Deprecated entrypoints:** `houmao-cli` and `houmao-cao-server` are deprecated compatibility entrypoints. Use `houmao-mgr` and `houmao-server`/`houmao-passive-server` instead.
