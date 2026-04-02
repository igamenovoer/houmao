# Project Mailbox Skills

When an agent has a mailbox binding, the build phase automatically projects a set of mailbox system skills into the agent's runtime home. These skills give the agent native knowledge of how to check, send, reply to, and manage mailbox messages.

## When Skills Are Projected

Mailbox skill projection happens during `BrainBuilder.build()` after standard user-defined skills are projected. The trigger is the presence of a resolved mailbox configuration in the build request — no explicit configuration is needed beyond having a mailbox binding in the preset or build request.

## Projected Skills

Four mailbox skills are projected:

| Skill | Purpose |
|---|---|
| `houmao-process-emails-via-gateway` | Round-oriented workflow for processing gateway-notified unread emails. Instructs the agent to list unread mail, triage by metadata, process relevant messages, and mark them read. |
| `houmao-email-via-agent-gateway` | Lower-level shared gateway facade with exact route contracts for `/v1/mail/*` operations (check, send, reply, mark-read). |
| `houmao-email-via-filesystem` | Transport-specific skill for filesystem mailbox validation, layout documentation, and fallback guidance when the gateway is unavailable. |
| `houmao-email-via-stalwart` | Transport-specific skill for Stalwart mailbox validation, endpoint configuration, and fallback to `houmao-mgr agents mail` commands. |

## Tool-Specific Behavior

The skill destination directory and namespace handling differ by tool:

| Tool | Destination | Namespace |
|---|---|---|
| Claude | `skills/` (top-level) | No namespace — skills appear at top level as native SKILL.md projections. |
| Codex | `skills/` | Namespaced under `mailbox/` (e.g., `mailbox/houmao-email-via-agent-gateway`). |
| Gemini | `.agents/skills/` | Namespaced under `mailbox/`. |

Claude receives mailbox skills as first-class top-level skills because Claude Code has native SKILL.md support. Other tools use the `mailbox/` namespace prefix to avoid collisions with user-defined skills. Gemini's upstream `.gemini/skills/` path remains a compatibility alias, but Houmao-owned projection now targets `.agents/skills/`.

## Skill Content

### `houmao-process-emails-via-gateway`

The primary round-oriented workflow skill. When triggered by a mail-notifier prompt, it instructs the agent to:

1. Confirm the gateway base URL is available.
2. Use `GET /v1/mail/status` to verify mailbox identity.
3. Use `POST /v1/mail/check` to list unread messages.
4. Perform metadata-first triage (subject, sender, timestamp).
5. Continue stalled or interrupted work from prior rounds.
6. Mark only successfully processed emails as read.
7. Stop after the round (do not proactively poll).

### `houmao-email-via-agent-gateway`

The lower-level gateway facade skill documenting exact HTTP routes:

| Action | Endpoint | Description |
|---|---|---|
| Check | `POST /v1/mail/check` | Inspect unread/current mailbox state with optional filtering. |
| Send | `POST /v1/mail/send` | Create new outbound message with recipients, subject, body, attachments. |
| Reply | `POST /v1/mail/reply` | Reply to a message using its opaque `message_ref`. |
| Mark read | `POST /v1/mail/state` | Mark an individual message as read after processing. |

### Transport-Specific Skills

`houmao-email-via-filesystem` and `houmao-email-via-stalwart` provide transport-specific validation and fallback guidance. They document the mailbox layout, environment variable expectations, and what to do when the gateway is unavailable (fall back to `houmao-mgr agents mail` commands or direct filesystem/JMAP access).

## See Also

- [Gateway Mail-Notifier](../../gateway/operations/mail-notifier.md) — the notifier that triggers email processing
- [Mailbox Reference](../index.md) — mailbox subsystem overview
- [Build Phase: Launch Overrides](../../build-phase/launch-overrides.md) — build phase configuration
