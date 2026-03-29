# houmao-mgr agents mail

Managed-agent mailbox follow-up commands. `houmao-mgr` routes these commands through pair-owned gateway-backed execution, local manager-owned direct execution when available, or local live-TUI submission fallback when direct authority is unavailable.

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

## Result Semantics

- Verified pair-owned and manager-owned execution returns `authoritative: true`, `status: "verified"`, and `execution_path: "gateway_backed"` or `"manager_direct"`.
- Local live-TUI fallback returns `authoritative: false` with submission-only status such as `submitted`, `rejected`, `busy`, `interrupted`, or `tui_error`.
- Non-authoritative fallback results may include `preview_result`, but mailbox verification should use manager-owned follow-up such as `agents mail status` or `agents mail check`, filesystem mailbox inspection, or transport-native mailbox state.

## See Also

- [houmao-mgr](houmao-mgr.md) — parent CLI reference
- [agents mailbox](agents-mailbox.md) — late filesystem mailbox registration
- [Mailbox Reference](../mailbox/index.md) — mailbox subsystem details
- [Managed-Agent API](../managed_agent_api.md) — HTTP mail follow-up routes
