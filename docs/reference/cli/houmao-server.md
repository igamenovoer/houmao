# houmao-server

Houmao-owned HTTP service.

`houmao-server` is the supported server entrypoint for managing agent sessions, terminal state, and runtime coordination. It exposes a REST API for session lifecycle, health checks, and terminal observation.

## Synopsis

```
houmao-server [OPTIONS] COMMAND [ARGS]...
```

## Commands

### `serve`

Start the server.

```
houmao-server serve [OPTIONS]
```

**Options:**

| Option | Default | Description |
|---|---|---|
| `--api-base-url TEXT` | `http://127.0.0.1:9889` | Base URL the server listens on. |
| `--runtime-root TEXT` | | Optional runtime root override for Houmao-owned server artifacts. |
| `--startup-child / --no-startup-child` | `--startup-child` | Whether to start any configured startup child process. |
| `--compat-codex-warmup-seconds FLOAT` | `2.0` | Warmup delay for Codex compatibility. Must be ≥ 0. |
| `--compat-provider-ready-poll-interval-seconds FLOAT` | `1.0` | Poll interval for provider readiness detection. Must be > 0. |
| `--compat-provider-ready-timeout-seconds FLOAT` | `45.0` | Timeout for provider readiness. Must be > 0. |
| `--compat-shell-ready-poll-interval-seconds FLOAT` | `0.5` | Poll interval for shell readiness detection. Must be > 0. |
| `--compat-shell-ready-timeout-seconds FLOAT` | `10.0` | Timeout for shell readiness. Must be > 0. |
| `--watch-poll-interval-seconds FLOAT` | `0.5` | Polling interval for the session watcher. |
| `--recent-transition-limit INT` | `24` | Maximum number of recent transitions to retain in memory. |
| `--stability-threshold-seconds FLOAT` | `1.0` | Time a session must remain stable before it is considered settled. |
| `--completion-stability-seconds FLOAT` | `1.0` | Time a completed session must remain stable before finalization. |
| `--unknown-to-stalled-timeout-seconds FLOAT` | `30.0` | Timeout before an unknown-state session is marked stalled. |
| `--supported-tui-process TEXT` | | TUI process name the server should recognize. Repeat `tool=name1,name2` to override supported live TUI process detection. May be specified multiple times. |

### `health`

Read the compatibility-safe health payload.

```
houmao-server health [OPTIONS]
```

**Options:**

| Option | Description |
|---|---|
| `--api-base-url TEXT` | Base URL of the running server to query. |

### `current-instance`

Read Houmao current-instance metadata.

```
houmao-server current-instance [OPTIONS]
```

**Options:**

| Option | Description |
|---|---|
| `--api-base-url TEXT` | Base URL of the running server to query. |

### `register-launch`

Registration endpoint for notifying the server of a new agent launch.

```
houmao-server register-launch [OPTIONS]
```

### `sessions list`

List child-backed sessions through houmao-server.

```
houmao-server sessions list [OPTIONS]
```

**Options:**

| Option | Description |
|---|---|
| `--api-base-url TEXT` | Base URL of the running server to query. |

### `sessions get`

Get one session payload.

```
houmao-server sessions get <session_name> [OPTIONS]
```

**Arguments:**

| Argument | Description |
|---|---|
| `session_name` | Name of the session to retrieve. |

### `terminals state`

Read the latest Houmao terminal-state view.

```
houmao-server terminals state <terminal_id> [OPTIONS]
```

**Arguments:**

| Argument | Description |
|---|---|
| `terminal_id` | Identifier of the terminal to inspect. |

### `terminals history`

Read bounded in-memory Houmao terminal transition history.

```
houmao-server terminals history <terminal_id> [OPTIONS]
```

**Arguments:**

| Argument | Description |
|---|---|
| `terminal_id` | Identifier of the terminal to inspect. |

**Options:**

| Option | Description |
|---|---|
| `--limit INT` | Maximum number of history entries to return. |
