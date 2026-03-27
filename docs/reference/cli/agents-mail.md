# houmao-mgr agents mail

Managed-agent mailbox follow-up commands. These commands operate through a live attached gateway on the targeted managed agent.

```
houmao-mgr agents mail [OPTIONS] COMMAND [ARGS]...
```

## Commands

### `status`

Show mailbox status for one managed agent.

```
houmao-mgr agents mail status [OPTIONS]
```

| Option | Description |
|---|---|
| `--port INTEGER` | Houmao pair authority port to use. |
| `--agent-id TEXT` | Authoritative managed-agent id. |
| `--agent-name TEXT` | Raw creation-time friendly managed-agent name. Do not include the `AGENTSYS-` prefix. |

### `check`

Check mailbox contents for one managed agent.

```
houmao-mgr agents mail check [OPTIONS]
```

| Option | Description |
|---|---|
| `--unread-only` | Return only unread messages. |
| `--limit INTEGER` | Maximum number of messages to return. |
| `--since TEXT` | Optional RFC3339 lower bound. |
| `--port INTEGER` | Houmao pair authority port to use. |
| `--agent-id TEXT` | Authoritative managed-agent id. |
| `--agent-name TEXT` | Raw creation-time friendly managed-agent name. |

### `send`

Send one mailbox message for a managed agent.

```
houmao-mgr agents mail send [OPTIONS]
```

| Option | Description |
|---|---|
| `--to TEXT` | Recipient address. **Required.** |
| `--cc TEXT` | CC recipient address. |
| `--subject TEXT` | Message subject. **Required.** |
| `--body-content TEXT` | Inline body content. |
| `--body-file TEXT` | Body content file path. |
| `--attach TEXT` | Attachment file path. |
| `--port INTEGER` | Houmao pair authority port to use. |
| `--agent-id TEXT` | Authoritative managed-agent id. |
| `--agent-name TEXT` | Raw creation-time friendly managed-agent name. |

### `reply`

Reply to one mailbox message for a managed agent.

```
houmao-mgr agents mail reply [OPTIONS]
```

| Option | Description |
|---|---|
| `--port INTEGER` | Houmao pair authority port to use. |
| `--agent-id TEXT` | Authoritative managed-agent id. |
| `--agent-name TEXT` | Raw creation-time friendly managed-agent name. |

## See Also

- [houmao-mgr](houmao-mgr.md) — parent CLI reference
- [agents mailbox](agents-mailbox.md) — late filesystem mailbox registration
- [Mailbox Reference](../mailbox/index.md) — mailbox subsystem details
- [Managed-Agent API](../managed_agent_api.md) — HTTP mail follow-up routes
