## Context

Houmao's current packaged system skills are organized around direct operational surfaces: lifecycle, messaging, gateway control, ordinary mailbox work, and notifier-driven mailbox rounds. That model is effective for mapping an immediate user request to one supported CLI or HTTP surface, but it leaves a gap for supported higher-level compositions that intentionally combine several Houmao skills into one workflow pattern.

The first requested advanced pattern is self-wakeup through gateway-mediated self-mail. The desired operator and agent contract is:

- the agent can send one or more follow-up emails to its own mailbox,
- the agent can leave gateway notifier polling enabled at a short interval such as five seconds,
- the mailbox unread set acts as the durable work backlog,
- notifier-driven rounds re-enter the agent later so it can continue or stage work incrementally.

That pattern is currently invalid on the filesystem mailbox transport. Filesystem delivery writes one actor-local mailbox-view state row per affected registration and seeds sender state as read. When sender and recipient are the same mailbox registration, the resulting mailbox-local state is read, so `agents mail check --unread-only` and gateway notifier polling do not treat that self-mail as actionable unread work.

This change is therefore cross-cutting across packaged system-skill assets, packaged skill-catalog selection, mailbox delivery semantics, gateway mailbox result shaping, and public documentation.

## Goals / Non-Goals

**Goals:**

- Add a packaged Houmao-owned system skill `houmao-adv-usage-pattern` that serves as an index for higher-level supported workflow compositions.
- Structure that skill with `SKILL.md` as the entry index and dedicated subpages for each advanced pattern.
- Ship an initial self-wakeup pattern page that composes existing mailbox, gateway, and notifier-round skills without redefining their lower-level command surfaces.
- Make filesystem self-sent mail addressed to the sender's own mailbox start unread for that actor so the pattern is actually actionable.
- Keep actor unread/read semantics, immediate send results, and repair/reindex defaults consistent with that self-send unread rule.
- Expose the new packaged skill through the maintained system-skill catalog, install defaults, CLI inventory, and narrative overview docs.

**Non-Goals:**

- Introduce a new durable job scheduler or claim durable arbitrary-work recovery through gateway wakeups.
- Change Stalwart server-side self-send behavior in this phase.
- Redesign the existing direct-operation skills so that `houmao-adv-usage-pattern` becomes their replacement.
- Change structural filesystem mailbox projection layout (`sent/`, `inbox/`, canonical messages) beyond the actor-local unread/read semantics needed for self-send.

## Decisions

### `houmao-adv-usage-pattern` is a packaged meta-skill, not a new control surface

The new skill will be packaged under the maintained system-skill asset root and projected like the other `houmao-*` system skills. Its `SKILL.md` will act as an index/router and point to local pattern pages such as `patterns/self-wakeup-via-self-mail.md`.

The skill will not become a new owner of `houmao-mgr` commands or gateway routes. Instead, each pattern page will compose the maintained direct-operation skills:

- `houmao-agent-email-comms` for ordinary mailbox operations,
- `houmao-agent-gateway` for notifier or optional wakeup control,
- `houmao-process-emails-via-gateway` for the actual notified unread-mail round.

This keeps operational authority with the existing skills and uses the advanced skill as a supported workflow layer above them.

The rejected alternative was to extend one existing direct-operation skill, such as `houmao-agent-email-comms`, until it also became the general owner of advanced compositions. That would blur the current skill boundaries and make ordinary mailbox work harder to keep concise.

### The new skill gets its own dedicated catalog set and default installation

The packaged system-skill catalog will add `houmao-adv-usage-pattern` as a current installable skill and define a dedicated named set for it, for example `advanced-usage`.

That set will be included in:

- managed launch auto-install,
- managed join auto-install,
- CLI-default installation.

This keeps the skill available inside ordinary managed homes where the advanced patterns are meant to be used, and it preserves the current catalog style of using explicit named sets rather than ad hoc one-off inventory logic.

The rejected alternative was to leave the advanced skill out of default installation and require explicit operator install every time. That would make the new supported pattern unavailable in the very managed homes it is supposed to guide.

### The self-wakeup pattern is defined around durable unread mail, not durable gateway timers

The initial pattern page will state the workflow as:

1. send one or more follow-up emails to the same mailbox,
2. keep gateway mail-notifier polling enabled,
3. stop and wait for the next notifier-driven round,
4. in each later round, inspect the unread set, choose the relevant step email or emails, complete work, and mark only the completed ones read.

The pattern will explicitly distinguish three layers:

- unread self-mail is the durable intent backlog,
- gateway mail-notifier is the live re-entry trigger while the gateway is attached,
- direct `/v1/wakeups` is optional timing assistance, not the durable backlog.

This wording matches current gateway and queue contracts and avoids overstating crash-recovery guarantees that the runtime does not actually provide.

The rejected alternative was to document the pattern as generic unexpected-stop recovery. Current gateway contracts do not justify that stronger claim across gateway restart or upstream instance replacement.

### Filesystem self-send unread/read state is driven by recipient membership

The filesystem transport will change its actor-local initial read-state rule from "sender starts read" to "recipient membership wins."

Operationally:

- if a mailbox registration is among the delivered recipients for a message, that mailbox starts unread for that message,
- if a mailbox registration only has the sender-side projection and is not a recipient, it starts read,
- if sender and recipient are the same mailbox registration, that mailbox starts unread.

Structural projections stay the same: the message may still project into both `sent/` and `inbox/` for the same mailbox. The change applies only to mailbox-local actor state.

The rejected alternative was to split mailbox-local read state by projection folder. That would require a broader data-model change because mailbox-local `message_state` is intentionally keyed by `message_id` within one mailbox, not by projection folder.

### Recovery and fallback defaulting must use the same self-send rule

The self-send unread rule will not live only in the direct delivery path. The same semantic must be used in all places that can synthesize or rebuild mailbox-local state:

- initial filesystem delivery,
- repair/reindex that recreates mailbox-local state from canonical messages,
- lazy insertion of mailbox-local state when a mailbox view is missing a row for an existing projected message.

Without that consistency, self-send behavior would flip depending on whether a message was freshly delivered, recovered, or first touched through a later state-update path.

The rejected alternative was to fix only fresh delivery. That would leave state repair and lazy mailbox-state initialization with inconsistent behavior and make the advanced pattern brittle after maintenance workflows.

### Filesystem send and reply result payloads must reflect actor-local unread truth

The filesystem gateway mailbox adapter currently returns `unread=False` for ordinary `send()` and `reply()` results. After the self-send unread change, those result payloads must be computed from the effective actor-local state rather than hardcoded defaults so that immediate API and CLI results match later `check --unread-only` behavior.

This alignment is limited to filesystem transport in this change. Stalwart already returns normalized server-origin message payloads, so its behavior remains transport-native.

The rejected alternative was to leave result payloads hardcoded and rely only on later `check` calls. That would create contradictory behavior between immediate send results and authoritative mailbox-view state.

## Risks / Trade-offs

- [Advanced skill duplicates existing lower-level guidance] → Keep the new skill strictly compositional and route each concrete operation back to the current direct-operation skills.
- [Filesystem self-send unread surprises callers that equated self-send with sent-copy semantics] → Scope the unread rule specifically to actor recipient membership and document that actor-local unread state is distinct from structural `sent/` projection.
- [Repair and lazy-state paths drift from fresh delivery semantics] → Apply one consistent initial-state rule across delivery, recovery, and lazy mailbox-state reconstruction.
- [Stalwart behavior is assumed to match filesystem behavior without proof] → Keep the normative change filesystem-specific and document Stalwart parity as out of scope for this proposal.
- [Default installation grows the visible skill inventory and docs drift] → Update catalog-driven install surfaces, CLI inventory, and the narrative overview in the same change.

## Migration Plan

1. Add the new packaged advanced-usage system skill and register it in the packaged catalog and default install selections.
2. Update system-skills CLI and overview docs so the new packaged inventory is visible and explained.
3. Change filesystem mailbox delivery, recovery, and mailbox-state fallback logic to seed self-sent self-addressed mail as unread for that mailbox.
4. Align filesystem gateway mailbox send/reply result payloads with the new actor-local unread rule.
5. Add tests for filesystem self-send unread visibility, notifier visibility, explicit mark-read completion, and packaged skill inventory exposure.

Rollback is code rollback only. Filesystem mailbox data does not require a schema migration for this change because the rule changes how initial mailbox-local state is seeded, not the storage schema itself.

## Open Questions

- None blocking for this change. If later work wants transport-neutral self-wakeup guarantees for Stalwart, that should be proposed as a separate follow-up after validating actual server-side self-send behavior.
