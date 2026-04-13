# houmao-mgr agents gateway

Gateway lifecycle and explicit live-gateway request commands for managed agents.

```
houmao-mgr agents gateway [OPTIONS] COMMAND [ARGS]...
```

## Scope Note

This CLI covers gateway lifecycle, prompt and interrupt control, raw send-keys, TUI inspection, reminder control, and mail-notifier control.

Reminder operations are available through `houmao-mgr agents gateway reminders ...`.

- prompt reminders and send-keys reminders both use the same `reminders` subgroup
- the subgroup follows the same selector rules as the rest of `agents gateway`
- `--pair-port` works through the managed-agent `/houmao/agents/{agent_ref}/gateway/reminders...` proxy
- direct `/v1/reminders` remains the lower-level live gateway contract underneath the CLI

Use [Gateway Reminders](../gateway/operations/reminders.md) for the reminder behavior model and [Protocol And State Contracts](../gateway/contracts/protocol-and-state.md) for the exact HTTP payloads.

## Commands

### `attach`

Attach or reuse a live gateway for one managed agent, including serverless local TUIs.

```
houmao-mgr agents gateway attach [OPTIONS]
```

| Option | Description |
|---|---|
| `--background` | Run the gateway as a detached background process instead of the default same-session auxiliary tmux window. |
| `--gateway-tui-watch-poll-interval-seconds FLOAT` | Override the gateway-owned TUI watch poll interval for this attach. |
| `--gateway-tui-stability-threshold-seconds FLOAT` | Override the gateway-owned TUI stability threshold for this attach. |
| `--gateway-tui-completion-stability-seconds FLOAT` | Override the gateway-owned TUI completion stability guard time for this attach. |
| `--gateway-tui-unknown-to-stalled-timeout-seconds FLOAT` | Override how long an unknown active surface waits before becoming stalled for this attach. |
| `--gateway-tui-stale-active-recovery-seconds FLOAT` | Override the stale-active recovery safeguard time for this attach. |
| `--gateway-tui-final-stable-active-recovery-seconds FLOAT` | Override the final stable-active recovery safeguard time for this attach. |
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
| `--model TEXT` | Request-scoped headless execution model override for this prompt only. |
| `--reasoning-level INTEGER` | Optional tool/model-specific reasoning preset index override for this prompt only. |
| `--current-session` | Resolve the target from the current tmux session's managed-agent metadata. |
| `--target-tmux-session TEXT` | Explicit local tmux session name to target from outside tmux. |
| `--pair-port INTEGER` | Houmao pair authority port override for explicit gateway prompt. |
| `--agent-id TEXT` | Authoritative managed-agent id. |
| `--agent-name TEXT` | Raw creation-time friendly managed-agent name. |

These override flags are accepted only when the resolved managed agent is headless. TUI-backed targets fail clearly instead of silently ignoring them. The override applies to exactly the addressed gateway prompt submission — including when that submission is queued through `submit_prompt` — and does not mutate launch profiles, recipes, specialists, manifests, or any other live session defaults. Partial overrides are supported: supplying `--reasoning-level` without `--model` merges with the launch-resolved model defaults through the shared headless resolution helper. The meaning of `--reasoning-level` depends on the resolved tool/model ladder, higher unused numbers saturate to that ladder's highest maintained Houmao preset, and `0` means explicit off only when that ladder supports it.

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

### `reminders`

Gateway reminder lifecycle and inspection commands.

```
houmao-mgr agents gateway reminders [OPTIONS] COMMAND [ARGS]...
```

| Subcommand | Description |
|---|---|
| `list` | Show the live gateway reminder set for one managed agent. |
| `get` | Show one live gateway reminder for one managed agent. |
| `create` | Create one live gateway reminder for one managed agent. |
| `set` | Update one live gateway reminder for one managed agent. |
| `remove` | Delete one live gateway reminder for one managed agent. |

Reminder ranking stays numeric:

- `--ranking <int>` uses an exact rank
- `--before-all` computes one less than the smallest current live ranking
- `--after-all` computes one more than the largest current live ranking

Create requires exactly one of those ranking modes. `set` preserves the current ranking unless one of them is supplied.

#### `reminders list`

Show the live reminder set, including `effective_reminder_id` and the current blocked-versus-effective ordering.

```
houmao-mgr agents gateway reminders list [OPTIONS]
```

| Option | Description |
|---|---|
| `--current-session` | Resolve the target from the current tmux session's managed-agent metadata. |
| `--target-tmux-session TEXT` | Explicit local tmux session name to target from outside tmux. |
| `--pair-port INTEGER` | Houmao pair authority port override for reminder listing. |
| `--agent-id TEXT` | Authoritative managed-agent id. |
| `--agent-name TEXT` | Raw creation-time friendly managed-agent name. |

#### `reminders get`

Show one live reminder while also reporting the set's current `effective_reminder_id`.

```
houmao-mgr agents gateway reminders get [OPTIONS]
```

| Option | Description |
|---|---|
| `--reminder-id TEXT` | Reminder id to inspect. **Required.** |
| `--current-session` | Resolve the target from the current tmux session's managed-agent metadata. |
| `--target-tmux-session TEXT` | Explicit local tmux session name to target from outside tmux. |
| `--pair-port INTEGER` | Houmao pair authority port override for reminder lookup. |
| `--agent-id TEXT` | Authoritative managed-agent id. |
| `--agent-name TEXT` | Raw creation-time friendly managed-agent name. |

#### `reminders create`

Create one live reminder through the managed-agent gateway surface.

```
houmao-mgr agents gateway reminders create [OPTIONS]
```

| Option | Description |
|---|---|
| `--title TEXT` | Reminder title used for inspection and reporting. **Required.** |
| `--mode [one_off\|repeat]` | Reminder mode. **Required.** |
| `--prompt TEXT` | Prompt text to submit when the reminder fires. |
| `--sequence TEXT` | Raw send-keys sequence for reminder delivery. |
| `--ensure-enter / --no-ensure-enter` | For send-keys reminders, ensure one trailing Enter unless explicitly disabled. Default: `--ensure-enter`. |
| `--ranking INTEGER` | Explicit numeric ranking. Lower numbers win. |
| `--before-all` | Compute ranking as one less than the smallest current reminder ranking. |
| `--after-all` | Compute ranking as one more than the largest current reminder ranking. |
| `--paused / --no-paused` | Create the reminder paused or active. Default: `--no-paused`. |
| `--start-after-seconds FLOAT` | Relative delivery delay in seconds. |
| `--deliver-at-utc TEXT` | Absolute UTC delivery timestamp. |
| `--interval-seconds FLOAT` | Repeat cadence in seconds. Required for repeat reminders. |
| `--current-session` | Resolve the target from the current tmux session's managed-agent metadata. |
| `--target-tmux-session TEXT` | Explicit local tmux session name to target from outside tmux. |
| `--pair-port INTEGER` | Houmao pair authority port override for reminder creation. |
| `--agent-id TEXT` | Authoritative managed-agent id. |
| `--agent-name TEXT` | Raw creation-time friendly managed-agent name. |

#### `reminders set`

Patch one reminder through the CLI surface. The CLI fetches the current reminder, applies only supplied overrides, then sends the full replacement payload to the gateway.

```
houmao-mgr agents gateway reminders set [OPTIONS]
```

| Option | Description |
|---|---|
| `--reminder-id TEXT` | Reminder id to update. **Required.** |
| `--title TEXT` | Replacement reminder title. |
| `--mode [one_off\|repeat]` | Replacement reminder mode. |
| `--prompt TEXT` | Replacement prompt text. |
| `--sequence TEXT` | Replacement send-keys sequence. |
| `--ensure-enter / --no-ensure-enter` | For send-keys reminders, override the trailing Enter behavior. |
| `--ranking INTEGER` | Replacement numeric ranking. Lower numbers win. |
| `--before-all` | Recompute ranking as one less than the smallest competing reminder ranking. |
| `--after-all` | Recompute ranking as one more than the largest competing reminder ranking. |
| `--paused / --no-paused` | Override the paused state without restating the full reminder. |
| `--start-after-seconds FLOAT` | Reset next delivery to a relative delay in seconds. |
| `--deliver-at-utc TEXT` | Reset next delivery to an absolute UTC timestamp. |
| `--interval-seconds FLOAT` | Replacement repeat cadence in seconds. |
| `--current-session` | Resolve the target from the current tmux session's managed-agent metadata. |
| `--target-tmux-session TEXT` | Explicit local tmux session name to target from outside tmux. |
| `--pair-port INTEGER` | Houmao pair authority port override for reminder update. |
| `--agent-id TEXT` | Authoritative managed-agent id. |
| `--agent-name TEXT` | Raw creation-time friendly managed-agent name. |

#### `reminders remove`

Delete one live reminder by id.

```
houmao-mgr agents gateway reminders remove [OPTIONS]
```

| Option | Description |
|---|---|
| `--reminder-id TEXT` | Reminder id to delete. **Required.** |
| `--current-session` | Resolve the target from the current tmux session's managed-agent metadata. |
| `--target-tmux-session TEXT` | Explicit local tmux session name to target from outside tmux. |
| `--pair-port INTEGER` | Houmao pair authority port override for reminder deletion. |
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
- Gateway TUI timing overrides must be positive seconds. They apply to the gateway sidecar started by this attach and are persisted as the desired timing config for the gateway root after attach succeeds.

## See Also

- [houmao-mgr](houmao-mgr.md) — parent CLI reference
- [Agent Gateway Reference](../gateway/index.md) — gateway subsystem details
- [Realm Controller Send-Keys](../realm_controller_send_keys.md) — raw control-input grammar and delivery semantics
