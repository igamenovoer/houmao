## Context

`houmao-adv-usage-pattern` now documents a forward relay-loop pattern where work may pass across multiple agents before a more distant loop egress returns the final result to the loop origin. That pattern is useful when ownership should keep moving forward, but it is more protocol-heavy than the common case where every delegation edge should close locally.

The simpler model discussed here is pairwise and recursive:

- one driver sends one worker request,
- that same worker returns the final result to that same driver,
- if the worker needs help, it becomes the driver of one or more child edge-loops,
- those child edge-loops still close locally before the worker answers its own upstream driver.

The relevant runtime primitives are the same ones already used by the forward relay pattern:

- queued gateway prompt delivery for live prompt handoff between already-running agents,
- mailbox send and reply behavior for receipts and result reporting,
- live gateway reminders for follow-up wakeups,
- self-mail for optional durable backlog pointers,
- `HOUMAO_JOB_DIR` for per-session scratch bookkeeping state.

The important current constraints are also the same:

- a driver cannot safely wait inside one long LLM turn for downstream mail to arrive;
- mailbox `reply` routes back to the immediate upstream sender rather than to an arbitrary future hop;
- the shared mail send surface does not expose custom workflow headers or explicit caller-controlled threading fields;
- only one gateway reminder is effective at a time, so one reminder per active loop does not scale well for many concurrent loops;
- `HOUMAO_MEMORY_DIR` is the long-term memory lane and should not be used as the default home for short-lived edge-loop control bookkeeping.

This change is documentation and packaged-skill guidance only. It does not add or change gateway, mailbox, or manager APIs.

## Goals / Non-Goals

**Goals:**

- Define one supported pairwise driver-worker edge-loop pattern on top of current Houmao messaging, mailbox, and reminder surfaces.
- Make the new pattern explicitly simpler than the forward relay-loop pattern by closing each delegation edge locally.
- Specify recursive composition where a worker may become a driver of child edge-loops without letting child results bypass the immediate driver.
- Provide clear chooser guidance between the pairwise local-close model and the forward relay model.

**Non-Goals:**

- Replacing or removing the existing forward relay-loop pattern.
- Adding a new workflow engine, queue, or mailbox routing primitive.
- Guaranteeing recovery across gateway restart, gateway loss, or managed-agent replacement.
- Defining a generic graph-execution framework beyond documented advanced-usage guidance.

## Decisions

### Document the model as a separate sibling advanced-usage pattern page

The implementation should add a new pattern page under `houmao-adv-usage-pattern/patterns/` and list it from the top-level `SKILL.md` alongside the self-notification and forward relay-loop patterns.

Why:

- The pairwise model is not a minor variant of the forward relay pattern; its routing invariant is different.
- A separate page keeps the simpler local-close model readable without overloading the existing relay page.

Alternative considered:

- Folding the pairwise model into the existing relay pattern page. Rejected because it would blur two different routing invariants and make the chooser guidance harder to follow.

### Use pairwise local-close routing as the core invariant

The pattern should define one loop round as a driver request that closes only when the same worker returns the final result to that same driver.

Why:

- This is the actual simplification the user wants.
- Local-close routing eliminates the need for distant loop egress ownership transfer within one loop round.

Alternative considered:

- Reusing the forward relay model but describing a special case where the loop egress happens to be the immediate receiver. Rejected because it hides the intended local-close rule instead of making it the primary invariant.

### Allow recursive nesting through child edge-loops

The pattern should allow a worker to become the driver of one or more child edge-loops, while still requiring each child edge-loop to close locally before the worker reports upstream.

Why:

- This captures the practical graph behavior the user described without requiring one giant end-to-end loop protocol.
- It keeps every edge-loop simple while still supporting larger multi-agent workflows.

Alternative considered:

- Restricting the pairwise model to strictly flat two-agent interactions only. Rejected because it would be too narrow for realistic multi-agent decomposition.

### Use one edge-local identifier plus optional parent linkage

The pattern should use `edge_loop_id` as the primary loop-round identifier and allow optional `parent_edge_loop_id` when one edge-loop is a child of another.

Why:

- The pairwise local-close model does not need the forward relay pattern's split between hop-local handoff identity and distant final-result routing identity.
- Optional parent linkage is enough to relate child loops back to an upstream edge when needed.

Alternative considered:

- Reusing `loop_id` plus `handoff_id` from the forward relay pattern. Rejected because it preserves complexity that the simpler pairwise model does not need as its primary identity scheme.

### Keep mutable bookkeeping under `HOUMAO_JOB_DIR`

The pattern should direct agents to store mutable edge-loop state under `HOUMAO_JOB_DIR` by default.

Why:

- Edge-loop bookkeeping is short-lived per-session control state.
- The pairwise model still needs local ledger rows for deduplication, resend timing, and phase tracking.

Alternative considered:

- Using `HOUMAO_MEMORY_DIR` as the normal bookkeeping location. Rejected because that is the durable notebook/archive lane rather than the intended scratch lane for transient workflow control state.

### Reuse the one-supervisor-reminder model

For one agent with many edge-loops in flight, the default pattern should remain one local ledger plus one supervisor reminder and optional self-mail checkpoint.

Why:

- The current reminder-selection model still blocks one reminder behind another.
- The pairwise model simplifies routing, not reminder semantics.

Alternative considered:

- One reminder per edge-loop. Rejected for the same scalability reason as the forward relay pattern.

### Derive thresholds from context and allow user-supplied policy

The pattern should treat receipt deadlines, result deadlines, review cadence, and retry horizon as workflow-policy values derived from context or explicit user input.

Why:

- Houmao exposes timing primitives and readiness gates, but no universal timeout policy.
- As a skill, this pattern can explicitly tell the agent to ask the user when a materially important threshold cannot be chosen sensibly from context.

Alternative considered:

- Defining one fixed timeout table inside the pattern page. Rejected because it would overstate runtime guarantees and encourage arbitrary values.

### Include chooser guidance against the forward relay pattern

The top-level advanced-usage guidance should explain when to choose:

- the pairwise edge-loop pattern for local-close driver-worker recursion,
- the forward relay-loop pattern for ownership that keeps moving forward until a later egress returns directly to a more distant origin.

Why:

- Without that comparison, readers will not know why two multi-agent loop pages exist.
- The distinction is architectural, not cosmetic.

Alternative considered:

- Leaving the relationship implicit. Rejected because the two pages would appear redundant.

## Risks / Trade-offs

- [Pattern overlap] → Readers may initially think the pairwise and forward relay patterns are duplicates. Mitigation: add explicit chooser guidance with side-by-side routing criteria.
- [Recursive nesting still adds complexity] → Even the simpler model can grow into a tree of child edge-loops. Mitigation: keep the protocol invariant local and require each child edge-loop to close before upstream reporting.
- [Local bookkeeping burden] → Agents still need a ledger instead of relying only on conversational context. Mitigation: keep the required fields minimal and centered on `edge_loop_id`, phase, timing, and peer identity.
- [Users may expect default timeouts] → Agents might still want exact numbers. Mitigation: state clearly that thresholds are policy values and allow direct user input when those values matter.

## Migration Plan

1. Add the delta spec for `houmao-adv-usage-pattern-skill`.
2. Add the new pairwise edge-loop pattern page under the advanced-usage skill assets.
3. Update the top-level advanced-usage skill index to point to the new pattern and distinguish it from the forward relay-loop pattern.
4. Update system-skill packaging and projection tests to assert that the new pattern page is projected and referenced.

Rollback is low risk: remove the new pairwise pattern page, revert the top-level skill index entry, and revert the delta spec before archive.

## Open Questions

- None for artifact generation. The design intentionally reuses current messaging, mailbox, and reminder surfaces without requiring new runtime behavior.
