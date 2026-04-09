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
| `--model TEXT` | Request-scoped headless execution model override for this turn only. |
| `--reasoning-level INTEGER` | Optional normalized `1..10` reasoning override for this turn only. |
| `--port INTEGER` | Houmao pair authority port to use. |
| `--agent-id TEXT` | Authoritative managed-agent id. |
| `--agent-name TEXT` | Raw creation-time friendly managed-agent name. Do not include the `HOUMAO-` prefix. |

The override flags affect only the submitted turn. They do not rewrite the stored manifest or future turns for the managed headless agent. Partial overrides are supported: supplying `--reasoning-level` without `--model` merges with the launch-resolved model defaults through the shared headless resolution helper rather than resetting fields that were not explicitly overridden. Because `agents turn submit` targets managed headless routes directly, TUI-target rejection does not apply here — but the same overrides are rejected clearly when reached through `agents prompt` or `agents gateway prompt` for a TUI-backed target.

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

Replay canonical managed headless turn events for one managed headless turn.

```
houmao-mgr agents turn events [OPTIONS] TURN_ID
```

This command replays Houmao's canonical semantic event stream for the turn instead of dumping raw provider stdout. It honors the root `--print-plain`, `--print-json`, and `--print-fancy` selection and defaults to `plain + concise`.

Use `--detail detail` when you need provider provenance and raw canonical event context. Use `stdout` or `stderr` when you need the exact durable provider artifacts.

| Argument | Description |
|---|---|
| `TURN_ID` | Identifier of the turn to inspect. |

| Option | Description |
|---|---|
| `--port INTEGER` | Houmao pair authority port to use. |
| `--agent-id TEXT` | Authoritative managed-agent id. |
| `--agent-name TEXT` | Raw creation-time friendly managed-agent name. |
| `--detail [concise\|detail]` | Canonical replay detail level. `concise` renders the stable answer/action/completion summary; `detail` includes extra structured provenance. |

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

This route stays raw on purpose. It returns the provider-owned stdout artifact and does not substitute canonical semantic JSON or replayed human rendering.

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

Like `stdout`, this command remains a raw durable-artifact inspection surface rather than a canonical event renderer.

## See Also

- [houmao-mgr](houmao-mgr.md) — parent CLI reference
- [Managed-Agent API](../managed_agent_api.md) — HTTP API surface for headless turn management
