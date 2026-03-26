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
| `--runtime-root PATH` | | Root directory for runtime state. |
| `--watch-poll-interval-seconds FLOAT` | | Polling interval for the session watcher. |
| `--recent-transition-limit INT` | | Maximum number of recent transitions to retain in memory. |
| `--stability-threshold-seconds FLOAT` | | Time a session must remain stable before it is considered settled. |
| `--completion-stability-seconds FLOAT` | | Time a completed session must remain stable before finalization. |
| `--unknown-to-stalled-timeout-seconds FLOAT` | | Timeout before an unknown-state session is marked stalled. |
| `--supported-tui-process TEXT` | | TUI process name the server should recognize. May be specified multiple times. |

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
