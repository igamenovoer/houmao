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
- External communication-only targets registered with `houmao-mgr agents external register` are supported with explicit `--agent-id` or `--agent-name`; mail operations route through the stored remote pair API and remote agent ref.
- Current-session targeting remains local tmux-only and does not resolve external records.

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

### `list`

List mailbox contents for one managed agent.

```
houmao-mgr agents mail list [OPTIONS]
```

| Option | Description |
|---|---|
| `--box TEXT` | Mailbox box/subdirectory to read. Defaults to `inbox`. |
| `--read-state [any\|read\|unread]` | Read-state filter. Defaults to `any`. |
| `--answered-state [any\|answered\|unanswered]` | Answered-state filter. Defaults to `any`. |
| `--archived / --not-archived` | Archived-state filter. |
| `--limit INTEGER` | Maximum number of messages to return. |
| `--since TEXT` | Optional RFC3339 lower bound. |
| `--include-body` | Include full message body text. |
| `--port INTEGER` | Houmao pair authority port to use with an explicit selector. |
| `--agent-id TEXT` | Authoritative managed-agent id. |
| `--agent-name TEXT` | Raw creation-time friendly managed-agent name. |

### `peek`

Peek at one mailbox message without marking it read.

```
houmao-mgr agents mail peek [OPTIONS]
```

| Option | Description |
|---|---|
| `--message-ref TEXT` | Opaque message reference returned by `agents mail list`. Required. |
| `--box TEXT` | Require the message to be in this box. |
| `--port INTEGER` | Houmao pair authority port to use with an explicit selector. |
| `--agent-id TEXT` | Authoritative managed-agent id. |
| `--agent-name TEXT` | Raw creation-time friendly managed-agent name. |

### `read`

Read one mailbox message and mark it read.

```
houmao-mgr agents mail read [OPTIONS]
```

| Option | Description |
|---|---|
| `--message-ref TEXT` | Opaque message reference returned by `agents mail list`. Required. |
| `--box TEXT` | Require the message to be in this box. |
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
| `--notify-block TEXT` | Sender-marked notification block text; capped at 512 chars. When omitted, the body is scanned for the first ` ```houmao-notify ` fenced block. See [Notification-prompt block](#notification-prompt-block). |
| `--notify-block-placement [append\|prepend]` | Placement metadata for `--notify-block`. Controls where the auto-mirrored body fence is inserted (prepend before existing body, append after) and where the gateway notifier renders the block (prepend before the inbox opener, append after the mailbox API summary). Defaults to `append`. Ignored when `--notify-block` is omitted. |
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
| `--reply-policy [none\|operator_mailbox]` | Operator-origin reply policy. Defaults to `operator_mailbox`. |
| `--attach TEXT` | Attachment file path. Repeatable. |
| `--notify-block TEXT` | Sender-marked notification block text; capped at 512 chars. When omitted, the body is scanned for the first ` ```houmao-notify ` fenced block. See [Notification-prompt block](#notification-prompt-block). |
| `--notify-block-placement [append\|prepend]` | Placement metadata for `--notify-block`. Controls where the auto-mirrored body fence is inserted (prepend before existing body, append after) and where the gateway notifier renders the block (prepend before the inbox opener, append after the mailbox API summary). Defaults to `append`. Ignored when `--notify-block` is omitted. |
| `--port INTEGER` | Houmao pair authority port to use with an explicit selector. |
| `--agent-id TEXT` | Authoritative managed-agent id. |
| `--agent-name TEXT` | Raw creation-time friendly managed-agent name. |

`post` is filesystem-only in v1. It delivers from the reserved Houmao-owned sender `HOUMAO-operator@houmao.localhost` into the selected managed agent mailbox and marks the message as operator-origin with explicit reply policy metadata. The default `reply_policy=operator_mailbox` allows replies to that specific operator-origin message back to the reserved operator mailbox. `reply_policy=none` is the explicit no-reply opt-out for one-way operator-origin notes. This action does not allow TUI submission fallback.

### `reply`

Reply to one mailbox message for a managed agent.

```
houmao-mgr agents mail reply [OPTIONS]
```

| Option | Description |
|---|---|
| `--message-ref TEXT` | Opaque message reference returned by `agents mail list`. Required. |
| `--body-content TEXT` | Inline body content. |
| `--body-file TEXT` | Body content file path. |
| `--attach TEXT` | Attachment file path. Repeatable. |
| `--port INTEGER` | Houmao pair authority port to use with an explicit selector. |
| `--agent-id TEXT` | Authoritative managed-agent id. |
| `--agent-name TEXT` | Raw creation-time friendly managed-agent name. |

Replies to operator-origin parent messages succeed when the parent was posted with `reply_policy=operator_mailbox`, which is the default for new operator-origin posts. When the parent explicitly used `reply_policy=none`, reply is rejected explicitly.

### `mark`

Mark selected mailbox messages for a managed agent.

```
houmao-mgr agents mail mark [OPTIONS]
```

| Option | Description |
|---|---|
| `--message-ref TEXT` | Message reference. Required and repeatable. |
| `--read / --unread` | Set read state. |
| `--answered / --unanswered` | Set answered state. |
| `--archived / --unarchived` | Set archived state. |
| `--port INTEGER` | Houmao pair authority port to use with an explicit selector. |
| `--agent-id TEXT` | Authoritative managed-agent id. |
| `--agent-name TEXT` | Raw creation-time friendly managed-agent name. |

At least one of `--read/--unread`, `--answered/--unanswered`, or `--archived/--unarchived` is required.

### `move`

Move selected mailbox messages for a managed agent.

```
houmao-mgr agents mail move [OPTIONS]
```

| Option | Description |
|---|---|
| `--message-ref TEXT` | Message reference. Required and repeatable. |
| `--destination-box TEXT` | Destination mailbox box/subdirectory. Required. |
| `--port INTEGER` | Houmao pair authority port to use with an explicit selector. |
| `--agent-id TEXT` | Authoritative managed-agent id. |
| `--agent-name TEXT` | Raw creation-time friendly managed-agent name. |

### `archive`

Archive selected mailbox messages for a managed agent.

```
houmao-mgr agents mail archive [OPTIONS]
```

| Option | Description |
|---|---|
| `--message-ref TEXT` | Message reference. Required and repeatable. |
| `--port INTEGER` | Houmao pair authority port to use with an explicit selector. |
| `--agent-id TEXT` | Authoritative managed-agent id. |
| `--agent-name TEXT` | Raw creation-time friendly managed-agent name. |

## Result Semantics

- Verified pair-owned and manager-owned execution returns `authoritative: true`, `status: "verified"`, and `execution_path: "gateway_backed"` or `"manager_direct"`.
- Local live-TUI fallback returns `authoritative: false` with submission-only status such as `submitted`, `rejected`, `busy`, `interrupted`, or `tui_error`.
- `post` never returns a TUI-submission result because it refuses non-authoritative execution.
- Non-authoritative fallback results may include `preview_result`, but callers must verify outcome through manager-owned follow-up such as `agents mail status` or `agents mail list`, the live gateway `/v1/mail/*` state, filesystem mailbox inspection, or transport-native mailbox state.

## Notification-prompt block

`send` and `post` carry an optional typed `notify_block` field in the canonical mailbox envelope. The shape is `MailboxNotifyBlock(text, placement)` where `text` is the prominent sender-authored content and `placement` is `append` or `prepend`. The gateway notifier renders `text` into the receiver's wake-up prompt at the requested placement (prepend slot before the inbox opener, append slot after the mailbox API summary). There are two authoring paths:

**Body fence (default authoring path)** — write a Markdown fenced code block with info-string `houmao-notify` inside `--body-content` (or the file passed to `--body-file`). The first such fence is extracted into the canonical `notify_block` field at composition time, with `placement="append"` by default. The fence text remains in the body source so receivers reading the full message see the same content.

```bash
pixi run houmao-mgr agents mail send \
  --agent-name alice \
  --to bob@houmao.localhost \
  --subject "bench results" \
  --body-content $'see attached numbers.\n\n```houmao-notify\nIf speedup ≥ 50x, re-run on official timing path before reporting.\n```'
```

**Explicit `--notify-block` + `--notify-block-placement` flags** — supply the value out of band. The CLI uses the explicit value directly; body-fence extraction is bypassed. The protocol-side **auto-mirror invariant** synthesizes a `houmao-notify` fenced block in the body at the requested placement when the body does not already contain one, so the receiver always finds the same text in the message body even though the channel reaches the wake-up prompt earlier.

```bash
pixi run houmao-mgr agents mail post \
  --agent-name alice \
  --subject "Continue current task" \
  --body-content "Operator note from supervisor." \
  --notify-block "continue current task" \
  --notify-block-placement prepend
```

Constraints to know:

- Maximum `notify_block.text` length is 512 characters; longer values are truncated to 511 characters plus a trailing `…`.
- When the body contains more than one `houmao-notify` fence, only the first is extracted; later fences remain in the body but are not added to `notify_block`.
- An empty fence produces no `notify_block` (treated as absent rather than empty text).
- The gateway notifier configuration controls whether sender-supplied notify-blocks are rendered at all and how their authentication metadata is verified. See [Gateway Protocol And State Contracts: Mail-notifier trust posture](../gateway/contracts/protocol-and-state.md#mail-notifier-trust-posture). Defaults are `notify_block_render=enabled`, `notify_block_auth_mode=permissive-log`, `notify_block_auth_verifier=none`; flipping `notify_block_auth_mode` to `required` causes the verifier to suppress unauthenticated blocks from the rendered prompt.
- Stalwart-bound mailbox sends currently reject `notify_block`; the JMAP-side projection lands in a follow-on change.

## Examples

```bash
# Resolve the current session's live mailbox binding from inside the owning tmux session.
pixi run houmao-mgr agents mail resolve-live

# Leave one operator-origin note in the current managed agent mailbox.
pixi run houmao-mgr agents mail post \
  --agent-name research \
  --subject "Resume after sync" \
  --body-content "Continue from the latest mailbox checkpoint."

# Archive one processed message for an explicit target.
pixi run houmao-mgr agents mail archive \
  --agent-name research \
  --message-ref filesystem:msg-20260312T050000Z-parent
```

## See Also

- [houmao-mgr](houmao-mgr.md) — parent CLI reference
- [agents mailbox](agents-mailbox.md) — late filesystem mailbox registration
- [Mailbox Reference](../mailbox/index.md) — mailbox subsystem details
- [System Skills Overview](../../getting-started/system-skills-overview.md) — narrative tour of `houmao-agent-email-comms` and `houmao-process-emails-via-gateway`
- [Managed-Agent API](../managed_agent_api.md) — HTTP mail follow-up routes
