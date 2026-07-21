# Project Mailbox Skills

Managed launch and join project the complete `agent` system-skill pack into the agent's runtime home. Its one public `houmao-agent-entrypoint` path contains protected mailbox routines for listing, inspecting, sending, replying to, and managing messages.

## When Skills Are Projected

Pack synchronization happens during `BrainBuilder.build()` after standard user-defined skills are projected. Managed launch selects the agent pack by default, independently of whether a mailbox binding already exists. A resolved mailbox configuration supplies runtime context for the nested routines.

## Public and Protected Shape

Only one mailbox-capable skill is public:

| Surface | Purpose |
|---|---|
| `houmao-agent-entrypoint` | Verifies managed self identity and routes agent-eligible work. |
| Protected `process-emails-via-gateway` | Processes one gateway-notified mailbox round, triages metadata, archives successful work, and stops after the round. |
| Protected `agent-email-comms` | Provides exact shared `/v1/mail/*` operations, transport-aware fallback, and resolver-driven mailbox inspection. |

## Tool-Specific Behavior

The public destination is the same shape for each managed tool:

| Tool | Public Path | Protected Mailbox Path |
|---|---|---|
| Claude | `skills/houmao-agent-entrypoint/` | `subskills/houmao-shared-routines/subskills/<routine>/` |
| Codex | `skills/houmao-agent-entrypoint/` | `subskills/houmao-shared-routines/subskills/<routine>/` |
| Kimi | `skills/houmao-agent-entrypoint/` | `subskills/houmao-shared-routines/subskills/<routine>/`; managed homes add `skills/` to `extra_skill_dirs` |


## Maintained Contract

Runtime-owned mailbox skills belong to the runtime home, not to copied project content. Maintained demos and runtime flows do not copy these Houmao mailbox skills into the launched project worktree just to make prompting succeed.

Ordinary mailbox prompting should use the installed native skill surface instead:

- Claude Code: `/houmao-agent-entrypoint process-emails-via-gateway <gateway-url>`.
- Codex: `$houmao-agent-entrypoint process-emails-via-gateway <gateway-url>`.
- Kimi: invoke `houmao-agent-entrypoint` with the protected route name and required gateway context.

Maintained prompts should not tell agents to open copied `skills/.../SKILL.md` files from the worktree for ordinary mailbox rounds.

## Skill Content

### Protected `process-emails-via-gateway`

The primary round-oriented workflow skill. When triggered by a mail-notifier prompt, it instructs the agent to:

1. Confirm the gateway base URL is available.
2. Use `GET /v1/mail/status` to verify mailbox identity.
3. Use `POST /v1/mail/list` to list eligible messages.
4. Perform metadata-first triage (subject, sender, timestamp).
5. Continue stalled or interrupted work from prior rounds.
6. Archive only successfully processed emails.
7. Stop after the round (do not proactively poll).

### Protected `agent-email-comms`

The unified mailbox skill keeps the exact shared gateway facade plus no-gateway transport-aware fallback in one place:

| Action | Endpoint | Description |
|---|---|---|
| List | `POST /v1/mail/list` | Inspect unread, open, archived, or current mailbox state with optional filtering. |
| Peek | `POST /v1/mail/peek` | Inspect one message without marking it read. |
| Read | `POST /v1/mail/read` | Inspect one message and mark it read. |
| Send | `POST /v1/mail/send` | Create new outbound message with recipients, subject, body, attachments. |
| Post | `POST /v1/mail/post` | Post an operator-origin note into a managed agent mailbox. |
| Reply | `POST /v1/mail/reply` | Reply to a message using its opaque `message_ref`. |
| Mark | `POST /v1/mail/mark` | Mark selected messages read, answered, or archived. |
| Move | `POST /v1/mail/move` | Move selected messages to another mailbox box. |
| Archive | `POST /v1/mail/archive` | Archive selected processed messages. |

The same skill also includes:

- `commands/status.md` and `commands/resolve-live.md` for mailbox binding inspection
- `references/transports/filesystem.md` for filesystem-specific layout and fallback guidance
- `references/transports/stalwart.md` for Stalwart-specific endpoint and fallback guidance

## See Also

- [Gateway Mail-Notifier](../../gateway/operations/mail-notifier.md) — the notifier that triggers email processing
- [Mailbox Reference](../index.md) — mailbox subsystem overview
- [Build Phase: Launch Overrides](../../build-phase/launch-overrides.md) — build phase configuration
