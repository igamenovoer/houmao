## Context

The current gateway mail notifier prompt already lists all unread message headers, but it is still organized around the low-level gateway protocol skill and curl examples. That makes the prompt read like an operations reference instead of a wake-up contract for one email-processing round.

This change crosses two existing capability areas:

- `agent-gateway-mail-notifier`, which defines the wake-up prompt contract and how runtime values are rendered into that prompt.
- `agent-mailbox-system-skills`, which defines which runtime-owned mailbox skills are projected into sessions and how those skills are intended to be used.

The new behavior needs a cleaner separation of responsibilities:

- the notifier prompt should tell the agent what unread mail exists now and what workflow to use for this round,
- the new workflow skill should describe how to choose relevant messages, inspect them, do the work, and mark them read,
- the existing `houmao-email-via-agent-gateway` skill should remain the lower-level protocol surface for gateway routes and curl usage,
- transport-specific skills should remain transport context and no-gateway fallback material.

Another constraint is metadata availability. The notifier poll path already has cheap unread-snapshot fields such as `message_ref`, `thread_ref`, sender identity, subject, and creation time. It should not expand the first prompt section by reading or embedding message body content just to make the reminder richer.

## Goals / Non-Goals

**Goals:**

- Make the notifier prompt lead with a list of all unread emails in the current snapshot using non-body metadata only.
- Make the notifier prompt explicitly instruct the agent to use `houmao-process-emails-via-gateway` for the current notification round.
- Keep the later operations section focused on the exact live gateway base URL and the full mailbox endpoint URLs for that turn.
- Introduce a runtime-owned workflow skill that defines round-oriented email processing and stop-after-round behavior.
- Preserve the existing lower-level gateway protocol skill as the place for resolver, curl, and endpoint details beyond the notifier prompt.

**Non-Goals:**

- Adding new gateway HTTP routes or changing mailbox API payload schemas.
- Introducing notifier-owned state about which messages are “claimed” or “reserved” for one agent round.
- Embedding message body content into the notifier prompt summary section.
- Changing mailbox read-state authority or transport semantics.

## Decisions

### Decision: Restructure the notifier prompt into unread-summary first, gateway-operations second

The notifier prompt will be rendered in two conceptual sections:

1. an unread email summary section for the current snapshot, and
2. a gateway operations reference section for this turn.

The first section will include every unread message in the snapshot and explicitly instruct the agent to use `houmao-process-emails-via-gateway`. The later section will anchor the agent on the exact live gateway URL and the full mailbox endpoint URLs derived from that base URL.

Why:

- The wake-up prompt should answer “what needs attention now?” before it answers “how do I call the gateway?”
- This layout makes the prompt usable when multiple unread messages are present and reduces the chance that the agent treats the prompt as a generic mailbox tutorial.

Alternative considered:

- Keep the current layout and only replace the named skill. Rejected because it preserves the same low-level-first structure that is causing the prompt to feel more like reference material than a round trigger.

### Decision: Keep the first section body-free and metadata-driven

The unread summary section will include only metadata already available from the unread snapshot or other non-body fields that can be obtained without reading message bodies. It will not include `body_preview`, `body_text`, or copied message-body content.

Why:

- The notification prompt should stay concise and avoid leaking message content before the agent has decided which messages matter for this round.
- The current notifier poll path already has stable access to sender identity, subject, message references, and timestamps without expanding its responsibilities.

Alternative considered:

- Include previews or body snippets in the first section. Rejected because it blurs the line between notification and inspection, increases prompt size, and could expose irrelevant message content before the round workflow chooses what to inspect.

### Decision: Add a workflow skill above the existing gateway protocol skill

The system will project a new runtime-owned mailbox skill `houmao-process-emails-via-gateway` alongside the existing `houmao-email-via-agent-gateway` and transport-specific mailbox skills.

The new skill will define the round workflow:

- start from summary metadata,
- optionally inspect more detail to shortlist relevant messages,
- select the message or messages to process now,
- inspect all selected messages needed for the round,
- do the actual work,
- mark only successfully processed messages read,
- stop and wait for the next notifier wake-up.

The existing `houmao-email-via-agent-gateway` skill will remain the lower-level protocol guide for resolver usage, gateway endpoints, and route-specific operations.

Why:

- Prompting a workflow skill is clearer than asking the agent to infer a round workflow from protocol docs.
- The low-level skill still has value as shared operational reference, but it should not be the main wake-up entrypoint.

Alternative considered:

- Fold the round workflow directly into `houmao-email-via-agent-gateway`. Rejected because it mixes round orchestration with route reference material and makes the protocol skill harder to keep concise.

### Decision: Treat “wait for the next notification” as explicit workflow behavior

The new workflow skill will explicitly tell the agent not to actively search for new mail after a round completes. After finishing the selected round of work, the agent waits for the next notifier prompt.

Why:

- The upstream gateway and mailbox rules remain responsible for unread-set changes and future wake-ups.
- This avoids self-directed polling loops that compete with gateway-owned scheduling or cause the agent to second-guess mailbox policy.

Alternative considered:

- Encourage the agent to re-check immediately after each completed round. Rejected because it duplicates the notifier’s job and makes the workflow noisier and less bounded.

## Risks / Trade-offs

- [The prompt may become longer when many unread messages exist] → Mitigation: keep the first section metadata-only, avoid body content, and keep detailed route/tutorial material in skills instead of the prompt.
- [Three mailbox skills may feel redundant] → Mitigation: define a clear layering contract: processing workflow skill, gateway protocol skill, and transport-specific context skill.
- [The notifier prompt could promise metadata not always available across transports] → Mitigation: require a stable minimum set of fields and allow extra non-body metadata only when already available without reading message bodies.
- [Joined sessions with Houmao skill projection opt-out could receive misleading instructions] → Mitigation: preserve the existing rule that runtime prompts only claim Houmao-owned skills are installed when projection actually occurred.

## Migration Plan

1. Update the notifier prompt spec to describe the new two-section contract and the new workflow skill trigger.
2. Update the mailbox system skill spec to project `houmao-process-emails-via-gateway` and define its relationship to the lower-level gateway skill.
3. Revise the notifier prompt template and renderer to emit the new section layout and dynamic full endpoint URLs.
4. Add the new mailbox workflow skill assets and adjust existing mailbox skill docs so their roles do not overlap ambiguously.
5. Update prompt-rendering and skill-projection tests to assert the new prompt contract and projected skill inventory.

No external API migration is required because the gateway HTTP routes stay the same.

## Open Questions

None at proposal time. The intended contract is specific enough to implement with the existing mailbox facade and projected skill system.
