## Context

Houmao mailbox work currently uses read/unread as the visible work-state boundary. This is too weak for agent workflows because an acknowledgement reply can mark a message read before the agent completes the requested work. Once that happens, the mail notifier can stop waking the agent even though the message is still actionable.

The existing filesystem transport already reserves mailbox subdirectories such as `archive/`, and the gateway already exposes a shared `/v1/mail/*` facade for status, check, send, post, reply, and read-state update. The change should reuse those surfaces but make the mailbox lifecycle explicit: reading a message, answering a message, and closing a message are different events.

The repository is in unstable development, so this design does not preserve old state-file or API compatibility. The only explicit endpoint compatibility constraint is to keep `POST /v1/mail/archive` as a shortcut because it is expected to be high-use.

## Goals / Non-Goals

**Goals:**

- Model mailbox lifecycle state as `read`, `answered`, box location, and archived/closed status rather than relying on read/unread alone.
- Support both automatic state transitions and manual state repair through shared gateway and CLI surfaces.
- Make `archive/` an active per-account box and let callers list any supported mailbox box and move messages among boxes.
- Distinguish `peek` from `read` so triage can inspect message content without mutating read state.
- Keep notifier reminders alive for open inbox work, including messages that are already read or answered but not archived.
- Update projected skills so agents archive mail only after successful processing.

**Non-Goals:**

- No migration path or backward-compatible shim for existing mailbox roots, message-state rows, or old gateway payload shapes.
- No attempt to make operator-origin `post` available for Stalwart as part of this change.
- No generalized user-defined folder hierarchy. The shared contract should support named mailbox boxes, but implementation may initially validate a supported set such as `inbox`, `sent`, `archive`, and transport-native equivalents.
- No deletion or trash workflow beyond preserving any existing `deleted` repair flag as an implementation detail where already present.
- No remote exposure of `/v1/mail/*` beyond the current loopback-bound gateway policy.

## Decisions

1. Use separate state fields instead of a single enum.

   The shared message state should expose booleans such as `read`, `answered`, and `archived` plus a `box` or `boxes` location view. This matches common mail-server concepts (`$seen`, `$answered`, mailbox membership) and avoids collapsing independent facts into one lifecycle enum. A single enum such as `new | acked | done` was rejected because a message can legitimately be read and not answered, answered and still open, or archived after manual triage without a reply.

2. Treat archive as a move plus closed-state shortcut.

   The general primitive should be `move` from one mailbox box to another, while `archive` remains a first-class shortcut for `move to archive` because callers will use it often. Archive should remove the message from the current inbox view, set `archived=true`, and mark it read by default unless a lower-level transport cannot express that atomically. Archive should not set `answered=true`; answering describes a reply event, not completion.

3. Split `peek` and `read`.

   `peek` should return the full message envelope/body without changing recipient-local state. `read` should return the same body and mark `read=true`. Listing operations should return metadata and preview material appropriate for triage without implicitly reading every message in a box. This gives agents a safe triage path and preserves an explicit action for workflows that want read receipts.

4. Make reply update `answered` automatically.

   A successful `reply` should mark the parent message as `answered=true` for the replying principal. This includes acknowledgement replies. It should also mark the parent read, because the agent necessarily targeted the parent message. This does not close the work; only archive closes it for notifier purposes.

5. Define notifier eligibility as open inbox work.

   The notifier should poll the shared mailbox facade for messages in the inbox that are not archived or otherwise closed. It should not require `read=false`. This keeps reminders active after acknowledgement replies or body inspection until the agent archives the processed mail. The notifier prompt should still avoid embedding message bodies and should continue to rely on the installed mailbox-processing skill for the round workflow.

6. Preserve `send` and `post` as distinct operations.

   Ordinary `send` continues to compose mail as the current mailbox principal to explicit recipients. Operator-origin `post` continues to inject a note from `HOUMAO-operator@houmao.localhost` to the selected agent mailbox, with the existing filesystem-only v1 boundary. The lifecycle change affects how resulting mail is read, answered, moved, and archived; it does not merge these delivery paths.

7. Put transport-specific mappings behind the shared adapter contract.

   Filesystem state should live in mailbox-local state storage and folder projections, while canonical Markdown remains immutable. Stalwart state should map onto JMAP concepts where available: seen/read, answered, mailbox membership, and an archive mailbox. Gateway and CLI callers should keep using opaque `message_ref` values and never derive storage identifiers from filesystem paths or Stalwart ids.

## Risks / Trade-offs

- Old mailbox roots and tests may break because state schema and route payloads are changing → Accept the break and update fixtures/tests directly; do not add compatibility code.
- Open inbox work can produce repeated reminders for intentionally deferred mail → Make archive the explicit completion action and keep notifier audit records clear enough to explain why reminders continue.
- Some transports may not support an exact multi-box model → Normalize through the shared adapter and fail explicitly for unsupported boxes or moves rather than silently pretending success.
- Automatically marking replies as answered may classify lightweight ACKs the same as substantive replies → This is intentional; `answered` means replied or acknowledged, while archive remains the processed/closed signal.
- Archive as both a box move and a state flag can drift if implemented in two places → Route archive through the same adapter method used by general move and derive the response from post-move transport evidence.
- Adding both `mark` and `move` broadens the state mutation surface → Keep validation strict, require explicit opaque message refs, return structured acknowledgements, and keep `/v1/mail/*` loopback-only under existing gateway policy.
