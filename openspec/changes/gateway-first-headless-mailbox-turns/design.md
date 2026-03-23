## Context

The current repository already establishes two important contracts:

- the live gateway mailbox facade is the preferred shared mailbox surface when it is attached, and
- direct filesystem mailbox helpers exist for transport-local work and no-gateway fallback.

In practice, the unattended headless ping-pong demo still slips past that boundary. Kickoff turns and notifier wake-up turns for filesystem-backed sessions currently spend bounded time rediscovering `deliver_message.py`, transport-local threading fields, and message-read mechanics. That behavior is expensive in headless turns because it consumes the turn budget on transport reconstruction rather than on one mailbox action.

The hack-through findings exposed three concrete gaps:

1. direct filesystem delivery is still leaking into routine headless send and reply turns,
2. the gateway notifier prompt is descriptive but not actionable enough for bounded autonomous turns, and
3. the shared gateway mailbox facade stops short of the read-state update needed to finish the routine "process one unread message" loop without falling back to transport-specific helpers.

This change is cross-cutting across gateway routes, gateway mailbox adapters, projected mailbox skills, and the headless demo pack, so it benefits from an explicit design.

## Goals / Non-Goals

**Goals:**

- Make routine mailbox turns gateway-first whenever a live loopback gateway mailbox facade is attached.
- Let one bounded headless turn complete the common "inspect one unread message, reply, then mark it read" flow without reconstructing transport-local details.
- Keep the shared mailbox contract transport-neutral by continuing to center reply and state-update targeting on opaque `message_ref` values.
- Keep demo role prompts policy-thin so they carry ping-pong semantics rather than filesystem transport mechanics.
- Preserve direct transport-specific helper flows as a supported fallback when no live gateway mailbox facade is available.

**Non-Goals:**

- Proxy the gateway `/v1/mail/*` facade through `houmao-server` in this change.
- Remove filesystem managed scripts or direct transport-specific mailbox behavior entirely.
- Redesign canonical mailbox storage or thread ancestry semantics.
- Add broad mailbox flag editing for every possible mailbox state in one step if the bounded-turn fix only needs explicit read-state mutation.
- Add a new runtime-owned `mail state` CLI or extend `mail_commands.MailOperation` in this change.
- Change the business behavior of the ping-pong conversation beyond making its mailbox action path bounded and reliable.

## Decisions

### Decision: Attached-session routine mailbox work becomes gateway-first for both transports

When a live loopback gateway exposes shared mailbox routes for a session, routine mailbox actions shall be expressed in shared gateway terms first. For this change, "routine mailbox actions" means the actions that bounded autonomous turns need most often: check unread mail, send a new message, reply to one existing message, and mark one processed message read.

This keeps filesystem-backed and Stalwart-backed headless turns aligned with the existing documented product direction instead of letting filesystem sessions regress into low-level helper choreography during ordinary turns.

Alternatives considered:

- Keep prompting filesystem agents with explicit `deliver_message.py` recipes. Rejected because it duplicates transport logic into prompts and keeps bounded-turn latency coupled to agent rediscovery.
- Introduce a demo-only helper or role-specific private shortcut. Rejected because HT-02 and HT-03 exposed a product-surface problem, not a demo-only content gap.

### Decision: Add one shared gateway mailbox state-update route centered on one opaque `message_ref`

The shared gateway mailbox facade will gain one mailbox state-update operation for routine per-recipient read-state mutation. The route shape in this change is `POST /v1/mail/state`, keyed by opaque `message_ref` and carrying at least a `read` field.

In v1, that request is intentionally narrow: one required opaque `message_ref` plus explicit single-message read mutation for one processed message. This change does not add batch targeting, broader mailbox-state flags, or a separate runtime-owned CLI surface for state updates.

The route remains loopback-only under the same mailbox-facade availability rules as the existing `/v1/mail/*` routes. It does not consume the terminal-mutation queue slot, and it resolves through the existing transport adapter pattern.

The gateway will return a minimal structured acknowledgment for that mutation rather than a full normalized message document. The caller already knows which message it processed; the route only needs to confirm that the addressed `message_ref` is now marked read for the current principal.

For the filesystem transport, the adapter maps the shared ref to the underlying mailbox message and delegates the mutation through the managed mailbox state-update helper. For the Stalwart transport, the adapter maps the same shared ref to the transport-owned message and applies the corresponding read-state mutation through the mail server integration.

Alternatives considered:

- Auto-mark the parent message read as a side effect of `reply`. Rejected because initiator turns also need to mark processed replies read after a successful send of the next round, and not every processing step ends in a reply.
- Keep read-state updates outside the shared facade. Rejected because that still forces filesystem-backed headless turns to recover transport-local identifiers and helper boundaries after the gateway has already provided transport-neutral message references.

### Decision: Notifier wake-up becomes a bounded actionable mailbox task, not just an unread digest

The gateway notifier will continue to discover unread mail through the shared mailbox facade, but the prompt it enqueues must become more actionable. Instead of only listing unread messages, it will nominate one actionable unread message and frame the turn as a bounded mailbox task.

Nomination policy is explicit in this change: when multiple unread messages are present, the notifier chooses the oldest unread message by `created_at_utc` with a stable tie-breaker rather than inheriting whichever iteration order a transport happens to return.

The wake-up prompt will include:

- the target `message_ref`,
- optional `thread_ref`,
- sender and subject context,
- the remaining unread count beyond the nominated target, and
- explicit instruction to complete processing through shared mailbox operations and mark the target read only after success.

Notifier deduplication remains keyed to the full unread set, not to the nominated target alone. Changing prompt structure or rotating between equivalent prompt renderings must not cause duplicate reminders when unread mailbox truth has not changed.

This keeps the notifier role as a scheduler rather than a transport explainer. It also gives the agent a single work item instead of an open-ended mailbox digest.

Alternatives considered:

- Keep the generic digest and rely on stronger role text alone. Rejected because HT-03 already demonstrated that descriptive reminders still leave too much room for transport reconstruction inside bounded turns.
- Push full message bodies and transport-specific delivery instructions into the notifier prompt. Rejected because the shared mailbox facade already provides a normalized read surface, and duplicating transport instructions would reintroduce the same coupling the change is trying to remove.

### Decision: Projected mailbox system skills separate routine shared actions from transport-local fallback

The projected mailbox system skill contract will distinguish two modes more clearly:

- attached-session routine shared actions use the live gateway facade when present, and
- direct filesystem helper usage remains the fallback for no-gateway sessions or transport-specific work outside the shared facade.

For both filesystem and Stalwart sessions, the projected skill shape should make that priority visible: a gateway-first routine-actions section first, followed by explicit transport-local fallback guidance. For filesystem sessions, this means the skill should stop presenting `deliver_message.py` and `update_mailbox_state.py` as the first choice for ordinary attached-session send, reply, and mark-read flows. Those helpers remain part of the transport contract, but they become implementation detail and fallback guidance rather than the primary path for routine headless turns.

Alternatives considered:

- Keep the skill transport-specific first and let the prompt override it ad hoc. Rejected because prompt-level overrides drift easily and produce the same ambiguity that caused HT-02 and HT-03.

### Decision: The ping-pong demo will carry policy, not transport mechanics

The demo pack will keep explicit ping-pong policy in its kickoff and role overlays: thread key, round, round limit, who replies next, and when to stop. It will stop embedding direct filesystem send and reply recipes as the normal path for gateway-attached runs.

In practice, kickoff should tell the initiator what message to send and to use the runtime-owned mailbox skill. Later responder or initiator wake-up turns should receive one actionable unread target through notifier context and complete one bounded reply-or-next-round action plus read-state update.

This keeps the demo aligned with the architecture already taught elsewhere in the repo: shared mailbox facade for shared operations, transport-specific helpers for fallback or transport-only work.

## Risks / Trade-offs

- [Gateway facade grows in scope] -> Keep the new surface narrow by adding only the read-state mutation needed for bounded routine turns and reusing the existing adapter boundary.
- [Transport parity may lag] -> Define the new shared state-update contract narrowly around read-state mutation and require explicit failures for transports that cannot satisfy it instead of silently falling back to filesystem-only behavior.
- [Prompt changes alone might still be insufficient for some models] -> Pair prompt tightening with product-surface narrowing so the agent has fewer decisions to make per turn.
- [Demo reliability may still depend on model latency] -> Keep role overlays thin, nominate exactly one actionable unread target, and avoid multi-step transport reconstruction in the active turn.
- [Direct helper fallback could drift from gateway-first behavior] -> Update the projected mailbox skill contract and tests so gateway-attached and no-gateway modes are both intentional and separately verified.

## Migration Plan

1. Extend gateway mailbox models, adapter protocol, and HTTP routes with the new shared mailbox state-update operation, using one opaque `message_ref` target and a minimal acknowledgment response.
2. Implement filesystem and Stalwart adapter support for that explicit read-state operation using the shared adapter boundary.
3. Update projected filesystem and Stalwart mailbox system skills so attached sessions lead with gateway-first routine actions and keep direct transport helpers as fallback guidance.
4. Update notifier prompt generation and prompt-input data so wake-up turns nominate the oldest actionable unread target, include sender and thread context, and preserve full-unread-set deduplication semantics.
5. Update the ping-pong demo pack prompts, role overlays, and automated tests to rely on the gateway-first routine path.
6. Refresh gateway and mailbox contract docs for the new route and notifier behavior.
7. Refresh workflow and demo guidance so attached-session mailbox behavior stays aligned with the gateway-first contract.

No durable data migration is required. Rollback is straightforward: revert the new gateway route and restore the older skill and prompt guidance. Existing mailbox content and gateway queue data remain structurally compatible.

## Open Questions

None for the v1 design scope captured by this change.
