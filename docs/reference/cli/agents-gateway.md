# houmao-mgr agents gateway

Gateway lifecycle and explicit live-gateway request commands for managed agents.

```
houmao-mgr agents gateway [OPTIONS] COMMAND [ARGS]...
```

## Commands

### `attach`

Attach or reuse a live gateway for one managed agent, including serverless local TUIs.

```
houmao-mgr agents gateway attach [OPTIONS]
```

| Option | Description |
|---|---|
| `--foreground` | Run the gateway in an auxiliary tmux window inside the managed session. Window `0` remains the agent surface; inspect status for the authoritative non-zero gateway window index. |
| `--current-session` | Resolve the target from the current tmux session's managed-agent metadata. Implied when no selector is provided inside tmux. |
| `--port INTEGER` | Houmao server port override for explicit attach. |
| `--agent-id TEXT` | Authoritative managed-agent id. |
| `--agent-name TEXT` | Raw creation-time friendly managed-agent name. Do not include the `HOUMAO-` prefix. |

### `detach`

Detach the live gateway for one managed agent.

```
houmao-mgr agents gateway detach [OPTIONS]
```

| Option | Description |
|---|---|
| `--current-session` | Resolve the target from the current tmux session's managed-agent metadata. |
| `--port INTEGER` | Houmao pair authority port to use. |
| `--agent-id TEXT` | Authoritative managed-agent id. |
| `--agent-name TEXT` | Raw creation-time friendly managed-agent name. |

### `status`

Show live gateway status, including foreground execution-mode metadata when present.

```
houmao-mgr agents gateway status [OPTIONS]
```

| Option | Description |
|---|---|
| `--current-session` | Resolve the target from the current tmux session's managed-agent metadata. |
| `--port INTEGER` | Houmao pair authority port to use. |
| `--agent-id TEXT` | Authoritative managed-agent id. |
| `--agent-name TEXT` | Raw creation-time friendly managed-agent name. |

### `prompt`

Submit the explicit gateway-mediated prompt path for one managed agent.

```
houmao-mgr agents gateway prompt [OPTIONS]
```

| Option | Description |
|---|---|
| `--prompt TEXT` | Prompt text to submit. If omitted, piped stdin is used. |
| `--current-session` | Resolve the target from the current tmux session's managed-agent metadata. |
| `--port INTEGER` | Houmao server port override for explicit gateway prompt. |
| `--agent-id TEXT` | Authoritative managed-agent id. |
| `--agent-name TEXT` | Raw creation-time friendly managed-agent name. |

### `interrupt`

Submit the explicit gateway-mediated interrupt path for one managed agent.

```
houmao-mgr agents gateway interrupt [OPTIONS]
```

| Option | Description |
|---|---|
| `--current-session` | Resolve the target from the current tmux session's managed-agent metadata. |
| `--port INTEGER` | Houmao pair authority port to use. |
| `--agent-id TEXT` | Authoritative managed-agent id. |
| `--agent-name TEXT` | Raw creation-time friendly managed-agent name. |

### `send-keys`

Submit the explicit gateway raw control-input path for one managed agent.

```
houmao-mgr agents gateway send-keys [OPTIONS]
```

| Option | Description |
|---|---|
| `--sequence TEXT` | Raw control-input sequence to deliver through the live gateway. **Required.** |
| `--escape-special-keys` | Treat the entire sequence literally instead of parsing `<[key-name]>` tokens. |
| `--current-session` | Resolve the target from the current tmux session's managed-agent metadata. |
| `--port INTEGER` | Houmao server port override for explicit gateway raw control input. |
| `--agent-id TEXT` | Authoritative managed-agent id. |
| `--agent-name TEXT` | Raw creation-time friendly managed-agent name. |

### `tui`

Raw gateway-owned TUI tracking commands.

```
houmao-mgr agents gateway tui [OPTIONS] COMMAND [ARGS]...
```

| Subcommand | Description |
|---|---|
| `state` | Show raw gateway-owned live TUI state for one managed agent. |
| `history` | Show bounded raw gateway-owned TUI snapshot history for one managed agent. |
| `watch` | Poll raw gateway-owned TUI state repeatedly for one managed agent. |
| `note-prompt` | Record prompt-note provenance without submitting a queued gateway request. |

### `mail-notifier`

Gateway mail-notifier lifecycle and inspection commands.

```
houmao-mgr agents gateway mail-notifier [OPTIONS] COMMAND [ARGS]...
```

| Subcommand | Description |
|---|---|
| `status` | Show gateway mail-notifier status for one managed agent. |
| `enable` | Enable or reconfigure gateway mail-notifier behavior for one managed agent. |
| `disable` | Disable gateway mail-notifier behavior for one managed agent. |

## Targeting Rules

- Outside tmux, gateway commands require an explicit `--agent-id` or `--agent-name`.
- Inside a managed tmux session, omitting the selector resolves the current session from `HOUMAO_MANIFEST_PATH` first and falls back to `HOUMAO_AGENT_ID` plus shared registry when needed.
- `--current-session` forces same-session resolution and cannot be combined with `--agent-id`, `--agent-name`, or `--port`.
- `--port` is only supported with an explicit selector, because current-session mode uses the manifest-declared pair authority instead of retargeting another server.

## See Also

- [houmao-mgr](houmao-mgr.md) — parent CLI reference
- [Agent Gateway Reference](../gateway/index.md) — gateway subsystem details
- [Realm Controller Send-Keys](../realm_controller_send_keys.md) — raw control-input grammar and delivery semantics
