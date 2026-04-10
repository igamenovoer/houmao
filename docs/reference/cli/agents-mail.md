# houmao-mgr agents mail

Managed-agent mailbox discovery and follow-up commands. `houmao-mgr` routes ordinary mailbox actions through pair-owned gateway-backed execution, local manager-owned direct execution when available, or local live-TUI submission fallback when direct authority is unavailable. The dedicated operator-origin `post` action is stricter: it requires authoritative gateway-backed or manager-owned execution and never falls back to TUI submission.

This is the **operator-facing CLI** for ordinary mailbox follow-up. The matching **agent-facing skill surface** is now unified into two packaged Houmao skills:

- `houmao-agent-email-comms` — ordinary shared-mailbox operations and the no-gateway fallback path. This is the canonical mailbox-operations skill paired with the `agents mail` family below.
- `houmao-process-emails-via-gateway` — round-oriented workflow for processing notifier-driven unread shared-mailbox emails through a prompt-provided gateway base URL.

For the narrative tour of every packaged system skill, see the [System Skills Overview](../../getting-started/system-skills-overview.md).

```
houmao-mgr agents mail [OPTIONS] COMMAND [ARGS]...
```

## Targeting Rules

- `--agent-id` or `--agent-name` explicitly selects one managed agent.
- Inside the owning managed tmux session, omitting both selectors resolves the current session through `HOUMAO_MANIFEST_PATH` first and `HOUMAO_AGENT_ID` plus shared-registry metadata second.
- Outside tmux, omitting both selectors fails explicitly instead of guessing from cwd or ambient shell state.
- `--port` is only supported with an explicit `--agent-id` or `--agent-name` target.

## Commands

### `resolve-live`

Resolve the current mailbox bindings and optional live gateway metadata for one managed agent.

```
houmao-mgr agents mail resolve-live [OPTIONS]
```

| Option | Description |
|---|---|
| `--port INTEGER` | Houmao pair authority port to use with an explicit selector. |
| `--agent-id TEXT` | Authoritative managed-agent id. |
| `--agent-name TEXT` | Raw creation-time friendly managed-agent name. Do not include the `HOUMAO-` prefix. |

JSON output includes the resolved mailbox binding, a `managed_agent` summary, `gateway_available`, and optional `gateway` metadata including `base_url` when a live shared `/v1/mail/*` facade is available. The transport-specific mailbox details live under `mailbox.filesystem.*` or `mailbox.stalwart.*`. Mailbox-specific shell export is not part of the supported `resolve-live` contract.

### `status`

Show mailbox status for one managed agent.

```
houmao-mgr agents mail status [OPTIONS]
```

| Option | Description |
|---|---|
| `--port INTEGER` | Houmao pair authority port to use with an explicit selector. |
| `--agent-id TEXT` | Authoritative managed-agent id. |
| `--agent-name TEXT` | Raw creation-time friendly managed-agent name. Do not include the `HOUMAO-` prefix. |

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
| `--port INTEGER` | Houmao pair authority port to use with an explicit selector. |
| `--agent-id TEXT` | Authoritative managed-agent id. |
| `--agent-name TEXT` | Raw creation-time friendly managed-agent name. |

### `send`

Send one mailbox message for a managed agent.

```
houmao-mgr agents mail send [OPTIONS]
```

| Option | Description |
|---|---|
| `--to TEXT` | Recipient address. Required and repeatable. |
| `--cc TEXT` | CC recipient address. Repeatable. |
| `--subject TEXT` | Message subject. Required. |
| `--body-content TEXT` | Inline body content. |
| `--body-file TEXT` | Body content file path. |
| `--attach TEXT` | Attachment file path. Repeatable. |
| `--port INTEGER` | Houmao pair authority port to use with an explicit selector. |
| `--agent-id TEXT` | Authoritative managed-agent id. |
| `--agent-name TEXT` | Raw creation-time friendly managed-agent name. |

### `post`

Post one operator-origin mailbox note into a managed agent inbox.

```
houmao-mgr agents mail post [OPTIONS]
```

| Option | Description |
|---|---|
| `--subject TEXT` | Message subject. Required. |
| `--body-content TEXT` | Inline body content. |
| `--body-file TEXT` | Body content file path. |
| `--attach TEXT` | Attachment file path. Repeatable. |
| `--port INTEGER` | Houmao pair authority port to use with an explicit selector. |
| `--agent-id TEXT` | Authoritative managed-agent id. |
| `--agent-name TEXT` | Raw creation-time friendly managed-agent name. |

`post` is filesystem-only in v1. It delivers from the reserved Houmao-owned sender `HOUMAO-operator@houmao.localhost` into the selected managed agent mailbox and marks the message as operator-origin and one-way. This action does not allow TUI submission fallback.

### `reply`

Reply to one mailbox message for a managed agent.

```
houmao-mgr agents mail reply [OPTIONS]
```

| Option | Description |
|---|---|
| `--message-ref TEXT` | Opaque message reference returned by `agents mail check`. Required. |
| `--body-content TEXT` | Inline body content. |
| `--body-file TEXT` | Body content file path. |
| `--attach TEXT` | Attachment file path. Repeatable. |
| `--port INTEGER` | Houmao pair authority port to use with an explicit selector. |
| `--agent-id TEXT` | Authoritative managed-agent id. |
| `--agent-name TEXT` | Raw creation-time friendly managed-agent name. |

### `mark-read`

Mark one mailbox message read for a managed agent.

```
houmao-mgr agents mail mark-read [OPTIONS]
```

| Option | Description |
|---|---|
| `--message-ref TEXT` | Opaque message reference returned by `agents mail check`. Required. |
| `--port INTEGER` | Houmao pair authority port to use with an explicit selector. |
| `--agent-id TEXT` | Authoritative managed-agent id. |
| `--agent-name TEXT` | Raw creation-time friendly managed-agent name. |

## Result Semantics

- Verified pair-owned and manager-owned execution returns `authoritative: true`, `status: "verified"`, and `execution_path: "gateway_backed"` or `"manager_direct"`.
- Local live-TUI fallback returns `authoritative: false` with submission-only status such as `submitted`, `rejected`, `busy`, `interrupted`, or `tui_error`.
- `post` never returns a TUI-submission result because it refuses non-authoritative execution.
- Non-authoritative fallback results may include `preview_result`, but callers must verify outcome through manager-owned follow-up such as `agents mail status` or `agents mail check`, the live gateway `/v1/mail/*` state, filesystem mailbox inspection, or transport-native mailbox state.

## Examples

```bash
# Resolve the current session's live mailbox binding from inside the owning tmux session.
pixi run houmao-mgr agents mail resolve-live

# Leave one operator-origin note in the current managed agent mailbox.
pixi run houmao-mgr agents mail post \
  --agent-name research \
  --subject "Resume after sync" \
  --body-content "Continue from the latest mailbox checkpoint."

# Mark one processed unread message read for an explicit target.
pixi run houmao-mgr agents mail mark-read \
  --agent-name research \
  --message-ref filesystem:msg-20260312T050000Z-parent
```

## See Also

- [houmao-mgr](houmao-mgr.md) — parent CLI reference
- [agents mailbox](agents-mailbox.md) — late filesystem mailbox registration
- [Mailbox Reference](../mailbox/index.md) — mailbox subsystem details
- [System Skills Overview](../../getting-started/system-skills-overview.md) — narrative tour of `houmao-agent-email-comms` and `houmao-process-emails-via-gateway`
- [Managed-Agent API](../managed_agent_api.md) — HTTP mail follow-up routes
