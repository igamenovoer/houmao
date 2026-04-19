# Project Mailbox Skills

When an agent has a mailbox binding, the build phase automatically projects a set of mailbox system skills into the agent's runtime home. These skills give the agent native knowledge of how to check, send, reply to, and manage mailbox messages.

## When Skills Are Projected

Mailbox skill projection happens during `BrainBuilder.build()` after standard user-defined skills are projected. The trigger is the presence of a resolved mailbox configuration in the build request — no explicit configuration is needed beyond having a mailbox binding in the source recipe, the resolved launch profile, or the build request.

## Projected Skills

Two mailbox skills are projected:

| Skill | Purpose |
|---|---|
| `houmao-process-emails-via-gateway` | Round-oriented workflow for processing gateway-notified mailbox work. Instructs the agent to list mailbox work through the gateway, triage by metadata, process relevant messages, archive successfully processed messages, and stop after the round. |
| `houmao-agent-email-comms` | Unified mailbox communication skill for exact shared `/v1/mail/*` operations, transport-aware fallback, and resolver-driven mailbox inspection. |

## Tool-Specific Behavior

The skill destination directory differs by tool, but Houmao-owned mailbox skills stay flat within that destination:

| Tool | Destination | Namespace |
|---|---|---|
| Claude | `skills/` (top-level) | No namespace — skills appear at top level as native SKILL.md projections. |
| Codex | `skills/` | No namespace — Houmao-owned Codex skills live at top level. |
| Gemini | `.gemini/skills/` | No namespace — Houmao-owned Gemini skills live at top level. |

Claude, Codex, and Gemini all receive mailbox skills as first-class top-level Houmao-owned skills because their maintained contracts rely on native skill discovery from the active skill destination. Gemini's upstream `.agents/skills/` path remains only an alias surface, but Houmao-owned projection now targets `.gemini/skills/`.

## Maintained Contract

Runtime-owned mailbox skills belong to the runtime home, not to copied project content. Maintained demos and runtime flows do not copy these Houmao mailbox skills into the launched project worktree just to make prompting succeed.

Ordinary mailbox prompting should use the installed native skill surface instead:

- Claude Code: invoke the installed skill through Claude's native skill surface, typically with `/houmao-...`.
- Codex: invoke the installed skill through Codex's native skill surface, typically with `$houmao-...`.
- Gemini: invoke the installed skill by name.

Maintained prompts should not tell agents to open copied `skills/.../SKILL.md` files from the worktree for ordinary mailbox rounds.

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

### `houmao-agent-email-comms`

The unified mailbox skill keeps the exact shared gateway facade plus no-gateway transport-aware fallback in one place:

| Action | Endpoint | Description |
|---|---|---|
| Check | `POST /v1/mail/check` | Inspect unread/current mailbox state with optional filtering. |
| Send | `POST /v1/mail/send` | Create new outbound message with recipients, subject, body, attachments. |
| Reply | `POST /v1/mail/reply` | Reply to a message using its opaque `message_ref`. |
| Mark read | `POST /v1/mail/state` | Mark an individual message as read after processing. |

The same skill also includes:

- `actions/status.md` and `actions/resolve-live.md` for mailbox binding inspection
- `transports/filesystem.md` for filesystem-specific layout and fallback guidance
- `transports/stalwart.md` for Stalwart-specific endpoint and fallback guidance

## See Also

- [Gateway Mail-Notifier](../../gateway/operations/mail-notifier.md) — the notifier that triggers email processing
- [Mailbox Reference](../index.md) — mailbox subsystem overview
- [Build Phase: Launch Overrides](../../build-phase/launch-overrides.md) — build phase configuration
