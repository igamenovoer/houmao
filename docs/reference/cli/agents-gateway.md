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
| `--background` | Run the gateway as a detached background process instead of the default same-session auxiliary tmux window. |
| `--current-session` | Resolve the target from the current tmux session's managed-agent metadata. Implied when no selector is provided inside tmux. |
| `--target-tmux-session TEXT` | Explicit local tmux session name to target from outside tmux. |
| `--pair-port INTEGER` | Houmao pair authority port override for explicit attach. |
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
| `--target-tmux-session TEXT` | Explicit local tmux session name to target from outside tmux. |
| `--pair-port INTEGER` | Houmao pair authority port to use for explicit managed-agent targeting. |
| `--agent-id TEXT` | Authoritative managed-agent id. |
| `--agent-name TEXT` | Raw creation-time friendly managed-agent name. |

### `status`

Show live gateway status, including the execution mode and authoritative gateway tmux window index when foreground execution is active.

```
houmao-mgr agents gateway status [OPTIONS]
```

| Option | Description |
|---|---|
| `--current-session` | Resolve the target from the current tmux session's managed-agent metadata. |
| `--target-tmux-session TEXT` | Explicit local tmux session name to target from outside tmux. |
| `--pair-port INTEGER` | Houmao pair authority port to use for explicit managed-agent targeting. |
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
| `--force` | Send the prompt even when the gateway does not judge the target prompt-ready. |
| `--current-session` | Resolve the target from the current tmux session's managed-agent metadata. |
| `--target-tmux-session TEXT` | Explicit local tmux session name to target from outside tmux. |
| `--pair-port INTEGER` | Houmao pair authority port override for explicit gateway prompt. |
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
| `--target-tmux-session TEXT` | Explicit local tmux session name to target from outside tmux. |
| `--pair-port INTEGER` | Houmao pair authority port to use for explicit managed-agent targeting. |
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
| `--target-tmux-session TEXT` | Explicit local tmux session name to target from outside tmux. |
| `--pair-port INTEGER` | Houmao pair authority port override for explicit gateway raw control input. |
| `--agent-id TEXT` | Authoritative managed-agent id. |
| `--agent-name TEXT` | Raw creation-time friendly managed-agent name. |

### `tui`

Raw gateway-owned TUI tracking commands. These commands inspect the gateway's internal TUI state tracker, which captures terminal snapshots, readiness signals, and turn boundaries for the managed agent's TUI surface.

```
houmao-mgr agents gateway tui [OPTIONS] COMMAND [ARGS]...
```

| Subcommand | Description |
|---|---|
| `state` | Show raw gateway-owned live TUI state for one managed agent. |
| `history` | Show bounded raw gateway-owned TUI snapshot history for one managed agent. |
| `watch` | Poll raw gateway-owned TUI state repeatedly for one managed agent. |
| `note-prompt` | Record prompt-note provenance without submitting a queued gateway request. |

#### `tui state`

Show raw gateway-owned live TUI state for one managed agent.

```
houmao-mgr agents gateway tui state [OPTIONS]
```

| Option | Description |
|---|---|
| `--current-session` | Resolve the target from the current tmux session's managed-agent metadata. |
| `--target-tmux-session TEXT` | Explicit local tmux session name to target from outside tmux. |
| `--pair-port INTEGER` | Houmao pair authority port override for explicit gateway TUI state. |
| `--agent-id TEXT` | Authoritative managed-agent id. |
| `--agent-name TEXT` | Raw creation-time friendly managed-agent name. |

#### `tui history`

Show bounded raw gateway-owned TUI snapshot history for one managed agent. Returns the recent history buffer of TUI state snapshots maintained by the gateway tracker.

```
houmao-mgr agents gateway tui history [OPTIONS]
```

| Option | Description |
|---|---|
| `--current-session` | Resolve the target from the current tmux session's managed-agent metadata. |
| `--target-tmux-session TEXT` | Explicit local tmux session name to target from outside tmux. |
| `--pair-port INTEGER` | Houmao pair authority port override for explicit gateway TUI history. |
| `--agent-id TEXT` | Authoritative managed-agent id. |
| `--agent-name TEXT` | Raw creation-time friendly managed-agent name. |

#### `tui watch`

Poll raw gateway-owned TUI state repeatedly for one managed agent. In a TTY, clears the screen between polls for a live-updating display. When piped, emits one JSON object per poll cycle.

```
houmao-mgr agents gateway tui watch [OPTIONS]
```

| Option | Description |
|---|---|
| `--interval-seconds FLOAT` | Polling interval for repeated TUI state inspection. Must be > 0. Default: `1.0`. |
| `--current-session` | Resolve the target from the current tmux session's managed-agent metadata. |
| `--target-tmux-session TEXT` | Explicit local tmux session name to target from outside tmux. |
| `--pair-port INTEGER` | Houmao pair authority port override for explicit gateway TUI watch. |
| `--agent-id TEXT` | Authoritative managed-agent id. |
| `--agent-name TEXT` | Raw creation-time friendly managed-agent name. |

#### `tui note-prompt`

Record prompt-note provenance without submitting a queued gateway request. This annotates the gateway's TUI tracker with the prompt text for provenance tracking, but does not enqueue a prompt for the agent.

```
houmao-mgr agents gateway tui note-prompt [OPTIONS]
```

| Option | Description |
|---|---|
| `--prompt TEXT` | Prompt text to record in the gateway-owned tracker. If omitted, piped stdin is used. |
| `--current-session` | Resolve the target from the current tmux session's managed-agent metadata. |
| `--target-tmux-session TEXT` | Explicit local tmux session name to target from outside tmux. |
| `--pair-port INTEGER` | Houmao pair authority port override for explicit gateway TUI prompt note. |
| `--agent-id TEXT` | Authoritative managed-agent id. |
| `--agent-name TEXT` | Raw creation-time friendly managed-agent name. |

### `mail-notifier`

Gateway mail-notifier lifecycle and inspection commands. The mail-notifier is a background polling loop within the gateway that periodically checks the agent's mailbox for new messages and injects notification prompts through the gateway's request queue.

```
houmao-mgr agents gateway mail-notifier [OPTIONS] COMMAND [ARGS]...
```

| Subcommand | Description |
|---|---|
| `status` | Show gateway mail-notifier status for one managed agent. |
| `enable` | Enable or reconfigure gateway mail-notifier behavior for one managed agent. |
| `disable` | Disable gateway mail-notifier behavior for one managed agent. |

#### `mail-notifier status`

Show the current mail-notifier status for one managed agent, including whether the notifier is enabled, the configured polling interval, and last-check metadata.

```
houmao-mgr agents gateway mail-notifier status [OPTIONS]
```

| Option | Description |
|---|---|
| `--current-session` | Resolve the target from the current tmux session's managed-agent metadata. |
| `--target-tmux-session TEXT` | Explicit local tmux session name to target from outside tmux. |
| `--pair-port INTEGER` | Houmao pair authority port override for explicit notifier status. |
| `--agent-id TEXT` | Authoritative managed-agent id. |
| `--agent-name TEXT` | Raw creation-time friendly managed-agent name. |

#### `mail-notifier enable`

Enable or reconfigure the gateway mail-notifier for one managed agent. When enabled, the gateway polls the agent's mailbox at the specified interval and submits notification prompts when unread messages are detected.

```
houmao-mgr agents gateway mail-notifier enable [OPTIONS]
```

| Option | Description |
|---|---|
| `--interval-seconds INTEGER` | Unread-mail polling interval in seconds. Must be >= 1. **Required.** |
| `--current-session` | Resolve the target from the current tmux session's managed-agent metadata. |
| `--target-tmux-session TEXT` | Explicit local tmux session name to target from outside tmux. |
| `--pair-port INTEGER` | Houmao pair authority port override for explicit notifier enable. |
| `--agent-id TEXT` | Authoritative managed-agent id. |
| `--agent-name TEXT` | Raw creation-time friendly managed-agent name. |

#### `mail-notifier disable`

Disable the gateway mail-notifier for one managed agent. The notifier stops polling and no further notification prompts are submitted until re-enabled.

```
houmao-mgr agents gateway mail-notifier disable [OPTIONS]
```

| Option | Description |
|---|---|
| `--current-session` | Resolve the target from the current tmux session's managed-agent metadata. |
| `--target-tmux-session TEXT` | Explicit local tmux session name to target from outside tmux. |
| `--pair-port INTEGER` | Houmao pair authority port override for explicit notifier disable. |
| `--agent-id TEXT` | Authoritative managed-agent id. |
| `--agent-name TEXT` | Raw creation-time friendly managed-agent name. |

## Targeting Rules

- Outside tmux, gateway commands require `--agent-id`, `--agent-name`, or `--target-tmux-session`.
- Use `--target-tmux-session` when you know the local tmux session name but do not want to resolve the managed-agent identity first.
- Inside a managed tmux session, omitting the selector resolves the current session from `HOUMAO_MANIFEST_PATH` first and falls back to `HOUMAO_AGENT_ID` plus shared registry when needed.
- `--current-session` is the explicit same-session selector. It cannot be combined with `--agent-id`, `--agent-name`, `--target-tmux-session`, or `--pair-port`.
- `--target-tmux-session` cannot be combined with `--agent-id`, `--agent-name`, `--current-session`, or `--pair-port`.
- `--target-tmux-session` resolves locally from the addressed tmux session's `HOUMAO_MANIFEST_PATH` first and falls back to an exact fresh shared-registry `terminal.session_name` match when the tmux-published manifest pointer is missing or stale.
- `--pair-port` is only supported with explicit `--agent-id` or `--agent-name` targeting. It selects the Houmao pair authority, not the live gateway listener port. Lower-level gateway listener overrides use runtime-facing flags such as `--gateway-port`.

## See Also

- [houmao-mgr](houmao-mgr.md) — parent CLI reference
- [Agent Gateway Reference](../gateway/index.md) — gateway subsystem details
- [Realm Controller Send-Keys](../realm_controller_send_keys.md) — raw control-input grammar and delivery semantics
