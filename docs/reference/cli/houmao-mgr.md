# houmao-mgr

Houmao pair CLI with native server and managed-agent command families.

`houmao-mgr` is the primary management CLI for local lifecycle, managed agents, and `houmao-server` control. It provides command groups for agent orchestration, brain construction, server management, and administrative tasks.

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

### `agents` — Agent lifecycle

```
houmao-mgr agents [OPTIONS] COMMAND [ARGS]...
```

Agent lifecycle: launch, terminate, observe, send-prompt, mail, join, gateway operations.

#### Subcommands

| Subcommand | Description |
|---|---|
| `launch` | Start a managed agent. Provisions a runtime home, builds the brain, and launches a live session. |
| `terminate` | Stop a running managed agent and clean up its session. |
| `prompt` | Send a prompt to a running agent session. |
| `join` | Attach to an existing agent's tmux session for direct interaction. |
| `mail` | Check, send, or reply to inter-agent mail messages. |
| `gateway attach` | Attach a gateway to an agent session. |
| `gateway status` | Show gateway status for a session. |
| `gateway prompt` | Send a prompt through the gateway. |
| `gateway interrupt` | Interrupt the current gateway operation. |

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
