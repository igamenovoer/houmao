# houmao-mgr agents single/self gateway

Gateway lifecycle and explicit live-gateway request commands for managed agents.

```
houmao-mgr agents single --agent-id <id> gateway [OPTIONS] COMMAND [ARGS]...
houmao-mgr agents single --agent-name <name> gateway [OPTIONS] COMMAND [ARGS]...
houmao-mgr agents self gateway [OPTIONS] COMMAND [ARGS]...
```

## Scope Note

This CLI covers gateway lifecycle, prompt and interrupt control, raw send-keys, TUI inspection, reminder control, and mail-notifier control.

Reminder operations are available through `houmao-mgr agents single --agent-id <id> gateway reminders ...`, `houmao-mgr agents single --agent-name <name> gateway reminders ...`, or `houmao-mgr agents self gateway reminders ...`.

- prompt reminders and send-keys reminders both use the same `reminders` subgroup
- the subgroup follows the same group-level target rules as the rest of the scoped gateway family
- `--pair-port` is available on selected-agent `agents single ... gateway` commands and works through the managed-agent `/houmao/agents/{agent_ref}/gateway/reminders...` proxy
- direct `/v1/reminders` remains the lower-level live gateway contract underneath the CLI

Use [Gateway Reminders](../gateway/operations/reminders.md) for the reminder behavior model and [Protocol And State Contracts](../gateway/contracts/protocol-and-state.md) for the exact HTTP payloads.

## Commands

### `attach`

Attach or reuse a live gateway for one managed agent, including serverless local TUIs.

```
houmao-mgr agents single --agent-id <id> gateway attach [OPTIONS]
```

If attach times out waiting for gateway health readiness, the command now reports the last observed health probe error when one exists. Use [Gateway Troubleshooting](../gateway/operations/troubleshooting.md) for the readiness timeout checklist and [Protocol And State Contracts](../gateway/contracts/protocol-and-state.md#gateway-client-proxy-policy) for the live gateway proxy policy.

| Option | Description |
|---|---|
| `--background` | Run the gateway as a detached background process instead of the default same-session auxiliary tmux window. |
| `--gateway-tui-watch-poll-interval-seconds FLOAT` | Override the gateway-owned TUI watch poll interval for this attach. |
| `--gateway-tui-stability-threshold-seconds FLOAT` | Override the gateway-owned TUI stability threshold for this attach. |
| `--gateway-tui-completion-stability-seconds FLOAT` | Override the gateway-owned TUI completion stability guard time for this attach. |
| `--gateway-tui-unknown-to-stalled-timeout-seconds FLOAT` | Override how long an unknown active surface waits before becoming stalled for this attach. |
| `--gateway-tui-stale-active-recovery-seconds FLOAT` | Override the stale-active recovery safeguard time for this attach. |
| `--gateway-tui-final-stable-active-recovery-seconds FLOAT` | Override the final stable-active recovery safeguard time for this attach. |
| `--pair-port INTEGER` | Houmao pair authority port override for explicit attach. |

### `detach`

Detach the live gateway for one managed agent.

```
houmao-mgr agents single --agent-id <id> gateway detach [OPTIONS]
```

| Option | Description |
|---|---|
| `--pair-port INTEGER` | Houmao pair authority port to use for explicit managed-agent targeting. |

### `status`

Show live gateway status, including the execution mode and authoritative gateway tmux window index when foreground execution is active.

```
houmao-mgr agents single --agent-id <id> gateway status [OPTIONS]
```

| Option | Description |
|---|---|
| `--pair-port INTEGER` | Houmao pair authority port to use for explicit managed-agent targeting. |

### `prompt`

Submit the explicit gateway-mediated prompt path for one managed agent.

```
houmao-mgr agents single --agent-id <id> gateway prompt [OPTIONS]
```

| Option | Description |
|---|---|
| `--prompt TEXT` | Prompt text to submit. If omitted, piped stdin is used. |
| `--force` | Send the prompt even when the gateway does not judge the target prompt-ready. |
| `--model TEXT` | Request-scoped headless execution model override for this prompt only. |
| `--reasoning-level INTEGER` | Optional tool/model-specific reasoning preset index override for this prompt only. |
| `--pair-port INTEGER` | Houmao pair authority port override for explicit gateway prompt. |

These override flags are accepted only when the resolved managed agent is headless. TUI-backed targets fail clearly instead of silently ignoring them. The override applies to exactly the addressed gateway prompt submission — including when that submission is queued through `submit_prompt` — and does not mutate launch profiles, recipes, specialists, manifests, or any other live session defaults. Partial overrides are supported: supplying `--reasoning-level` without `--model` merges with the launch-resolved model defaults through the shared headless resolution helper. The meaning of `--reasoning-level` depends on the resolved tool/model ladder, higher unused numbers saturate to that ladder's highest maintained Houmao preset, and `0` means explicit off only when that ladder supports it.

### `interrupt`

Submit the explicit gateway-mediated interrupt path for one managed agent.

```
houmao-mgr agents single --agent-id <id> gateway interrupt [OPTIONS]
```

| Option | Description |
|---|---|
| `--pair-port INTEGER` | Houmao pair authority port to use for explicit managed-agent targeting. |

### `send-keys`

Submit the explicit gateway raw control-input path for one managed agent.

```
houmao-mgr agents single --agent-id <id> gateway send-keys [OPTIONS]
```

| Option | Description |
|---|---|
| `--sequence TEXT` | Raw control-input sequence to deliver through the live gateway. **Required.** |
| `--escape-special-keys` | Treat the entire sequence literally instead of parsing `<[key-name]>` tokens. |
| `--pair-port INTEGER` | Houmao pair authority port override for explicit gateway raw control input. |

### `reminders`

Gateway reminder lifecycle and inspection commands.

```
houmao-mgr agents single --agent-id <id> gateway reminders [OPTIONS] COMMAND [ARGS]...
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
houmao-mgr agents single --agent-id <id> gateway reminders list [OPTIONS]
```

| Option | Description |
|---|---|
| `--pair-port INTEGER` | Houmao pair authority port override for reminder listing. |

#### `reminders get`

Show one live reminder while also reporting the set's current `effective_reminder_id`.

```
houmao-mgr agents single --agent-id <id> gateway reminders get [OPTIONS]
```

| Option | Description |
|---|---|
| `--reminder-id TEXT` | Reminder id to inspect. **Required.** |
| `--pair-port INTEGER` | Houmao pair authority port override for reminder lookup. |

#### `reminders create`

Create one live reminder through the managed-agent gateway surface.

```
houmao-mgr agents single --agent-id <id> gateway reminders create [OPTIONS]
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
| `--pair-port INTEGER` | Houmao pair authority port override for reminder creation. |

#### `reminders set`

Patch one reminder through the CLI surface. The CLI fetches the current reminder, applies only supplied overrides, then sends the full replacement payload to the gateway.

```
houmao-mgr agents single --agent-id <id> gateway reminders set [OPTIONS]
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
| `--pair-port INTEGER` | Houmao pair authority port override for reminder update. |

#### `reminders remove`

Delete one live reminder by id.

```
houmao-mgr agents single --agent-id <id> gateway reminders remove [OPTIONS]
```

| Option | Description |
|---|---|
| `--reminder-id TEXT` | Reminder id to delete. **Required.** |
| `--pair-port INTEGER` | Houmao pair authority port override for reminder deletion. |

### `tui`

Raw gateway-owned TUI tracking commands. These commands inspect the gateway's internal TUI state tracker, which captures terminal snapshots, readiness signals, and turn boundaries for the managed agent's TUI surface.

```
houmao-mgr agents single --agent-id <id> gateway tui [OPTIONS] COMMAND [ARGS]...
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
houmao-mgr agents single --agent-id <id> gateway tui state [OPTIONS]
```

| Option | Description |
|---|---|
| `--pair-port INTEGER` | Houmao pair authority port override for explicit gateway TUI state. |

#### `tui history`

Show bounded raw gateway-owned TUI snapshot history for one managed agent. Returns the recent history buffer of TUI state snapshots maintained by the gateway tracker.

```
houmao-mgr agents single --agent-id <id> gateway tui history [OPTIONS]
```

| Option | Description |
|---|---|
| `--pair-port INTEGER` | Houmao pair authority port override for explicit gateway TUI history. |

#### `tui watch`

Poll raw gateway-owned TUI state repeatedly for one managed agent. In a TTY, clears the screen between polls for a live-updating display. When piped, emits one JSON object per poll cycle.

```
houmao-mgr agents single --agent-id <id> gateway tui watch [OPTIONS]
```

| Option | Description |
|---|---|
| `--interval-seconds FLOAT` | Polling interval for repeated TUI state inspection. Must be > 0. Default: `1.0`. |
| `--pair-port INTEGER` | Houmao pair authority port override for explicit gateway TUI watch. |

#### `tui note-prompt`

Record prompt-note provenance without submitting a queued gateway request. This annotates the gateway's TUI tracker with the prompt text for provenance tracking, but does not enqueue a prompt for the agent.

```
houmao-mgr agents single --agent-id <id> gateway tui note-prompt [OPTIONS]
```

| Option | Description |
|---|---|
| `--prompt TEXT` | Prompt text to record in the gateway-owned tracker. If omitted, piped stdin is used. |
| `--pair-port INTEGER` | Houmao pair authority port override for explicit gateway TUI prompt note. |

### `mail-notifier`

Gateway mail-notifier lifecycle and inspection commands. The mail-notifier is a background polling loop within the gateway that periodically checks the agent's mailbox for open inbox work and injects notification prompts through the gateway's request queue. It can also run opt-in context handling before a notification prompt is enqueued.

```
houmao-mgr agents single --agent-id <id> gateway mail-notifier [OPTIONS] COMMAND [ARGS]...
```

| Subcommand | Description |
|---|---|
| `status` | Show gateway mail-notifier status for one managed agent. |
| `enable` | Enable or reconfigure gateway mail-notifier behavior for one managed agent. |
| `disable` | Disable gateway mail-notifier behavior for one managed agent. |

#### `mail-notifier status`

Show the current mail-notifier status for one managed agent, including whether the notifier is enabled, the configured polling interval, effective mode, effective appendix text, effective context policies, and last-check metadata.

```
houmao-mgr agents single --agent-id <id> gateway mail-notifier status [OPTIONS]
```

| Option | Description |
|---|---|
| `--pair-port INTEGER` | Houmao pair authority port override for explicit notifier status. |

#### `mail-notifier enable`

Enable or reconfigure the gateway mail-notifier for one managed agent. When enabled, the gateway polls the agent's mailbox at the specified interval and submits notification prompts for mail that matches the selected mode. The default `any_inbox` mode notifies for any unarchived inbox mail, including read or answered mail. The opt-in `unread_only` mode notifies only for unread unarchived inbox mail. `--appendix-text` replaces the runtime appendix appended to future notifier prompts; omit it to preserve the current appendix, or pass an empty value to clear it. `--context-error-policy` defaults to `continue_current`, so degraded context remains diagnostic and does not force reset. `--context-error-policy clear_context` is opt-in and clears context only when the live degraded diagnostic is recognized for the owning CLI tool. `--pre-notification-context-action compact` runs a supported compaction action before each notification prompt; v1 supports Codex TUI through `/compact` and rejects unsupported tool/backend combinations.

```
houmao-mgr agents single --agent-id <id> gateway mail-notifier enable [OPTIONS]
```

| Option | Description |
|---|---|
| `--interval-seconds INTEGER` | Mailbox polling interval in seconds. Must be >= 1. **Required.** |
| `--mode [any_inbox\|unread_only]` | Notification mode. Defaults to `any_inbox`. |
| `--appendix-text TEXT` | Runtime guidance appended to each generated notifier prompt. Empty string clears the stored appendix. |
| `--context-error-policy [continue_current\|clear_context]` | Degraded-context policy. Defaults to `continue_current`; `clear_context` is opt-in and applies only to recognized tool-owned degraded diagnostics. |
| `--pre-notification-context-action [none\|compact]` | Context action to run before each notification prompt. Defaults to `none`; `compact` is supported for live Codex TUI gateways. |
| `--pair-port INTEGER` | Houmao pair authority port override for explicit notifier enable. |

#### `mail-notifier disable`

Disable the gateway mail-notifier for one managed agent. The notifier stops polling and no further notification prompts are submitted until re-enabled. Disabling does not clear stored appendix text.

```
houmao-mgr agents single --agent-id <id> gateway mail-notifier disable [OPTIONS]
```

| Option | Description |
|---|---|
| `--pair-port INTEGER` | Houmao pair authority port override for explicit notifier disable. |

## Targeting Rules

- `agents single --agent-id <id> gateway ...` and `agents single --agent-name <name> gateway ...` require exactly one explicit group-level selected-agent target. Nested gateway leaves do not repeat `--agent-id` or `--agent-name`.
- `agents self gateway ...` targets the current registered managed tmux session and accepts no explicit selectors, no `--current-session`, and no `--pair-port`.
- `--pair-port` is only supported on selected-agent `agents single ... gateway` commands. It selects the Houmao pair authority, not the live gateway listener port. Lower-level gateway listener overrides use runtime-facing flags such as `--gateway-port`.
- Gateway TUI timing overrides must be positive seconds. They apply to the gateway sidecar started by this attach and are persisted as the desired timing config for the gateway root after attach succeeds.
- External communication-only targets registered with `houmao-mgr agents external register` are supported through selected-agent communication-safe routes such as `agents single --agent-name <name> gateway status`, `gateway prompt`, and `gateway interrupt`; those commands route through the stored remote pair API base URL and remote agent ref.
- External targets are rejected for local gateway ownership commands such as `gateway attach`, `gateway detach`, `gateway send-keys`, self/current-session targeting, TUI snapshot helpers, reminders, and mail-notifier mutation.

## See Also

- [houmao-mgr](houmao-mgr.md) — parent CLI reference
- [Agent Gateway Reference](../gateway/index.md) — gateway subsystem details
- [Realm Controller Send-Keys](../realm_controller_send_keys.md) — raw control-input grammar and delivery semantics
