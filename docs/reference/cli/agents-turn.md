# houmao-mgr agents turn

Managed headless turn submission and inspection commands.

```
houmao-mgr agents turn [OPTIONS] COMMAND [ARGS]...
```

These commands target server-managed native headless agents for durable turn submission and post-turn inspection.

## Commands

### `submit`

Submit one managed headless turn for a headless agent.

```
houmao-mgr agents turn submit [OPTIONS]
```

| Option | Description |
|---|---|
| `--prompt TEXT` | Prompt text to submit. If omitted, piped stdin is used. |
| `--port INTEGER` | Houmao pair authority port to use. |
| `--agent-id TEXT` | Authoritative managed-agent id. |
| `--agent-name TEXT` | Raw creation-time friendly managed-agent name. Do not include the `HOUMAO-` prefix. |

### `status`

Show one managed headless turn status payload.

```
houmao-mgr agents turn status [OPTIONS] TURN_ID
```

| Argument | Description |
|---|---|
| `TURN_ID` | Identifier of the turn to inspect. |

| Option | Description |
|---|---|
| `--port INTEGER` | Houmao pair authority port to use. |
| `--agent-id TEXT` | Authoritative managed-agent id. |
| `--agent-name TEXT` | Raw creation-time friendly managed-agent name. |

### `events`

Show structured events for one managed headless turn.

```
houmao-mgr agents turn events [OPTIONS] TURN_ID
```

| Argument | Description |
|---|---|
| `TURN_ID` | Identifier of the turn to inspect. |

| Option | Description |
|---|---|
| `--port INTEGER` | Houmao pair authority port to use. |
| `--agent-id TEXT` | Authoritative managed-agent id. |
| `--agent-name TEXT` | Raw creation-time friendly managed-agent name. |

### `stdout`

Print the raw persisted stdout artifact for one managed headless turn.

```
houmao-mgr agents turn stdout [OPTIONS] TURN_ID
```

| Argument | Description |
|---|---|
| `TURN_ID` | Identifier of the turn to inspect. |

| Option | Description |
|---|---|
| `--port INTEGER` | Houmao pair authority port to use. |
| `--agent-id TEXT` | Authoritative managed-agent id. |
| `--agent-name TEXT` | Raw creation-time friendly managed-agent name. |

### `stderr`

Print the raw persisted stderr artifact for one managed headless turn.

```
houmao-mgr agents turn stderr [OPTIONS] TURN_ID
```

| Argument | Description |
|---|---|
| `TURN_ID` | Identifier of the turn to inspect. |

| Option | Description |
|---|---|
| `--port INTEGER` | Houmao pair authority port to use. |
| `--agent-id TEXT` | Authoritative managed-agent id. |
| `--agent-name TEXT` | Raw creation-time friendly managed-agent name. |

## See Also

- [houmao-mgr](houmao-mgr.md) — parent CLI reference
- [Managed-Agent API](../managed_agent_api.md) — HTTP API surface for headless turn management
