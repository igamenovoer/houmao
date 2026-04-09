## Context

`houmao-adv-usage-pattern` currently documents self-notification, but it does not describe a supported multi-agent relay loop where work enters at one managed agent, may transit across additional agents, and exits back to the original master agent through email.

The relevant runtime primitives already exist:

- queued gateway prompt delivery for live prompt handoff between already-running agents,
- mailbox send and reply behavior for receipts and result reporting,
- live gateway reminders for follow-up wakeups,
- self-mail for durable local backlog,
- `HOUMAO_JOB_DIR` for per-session scratch bookkeeping state.

The important current constraints are:

- a relay hop cannot safely wait inside one long LLM turn for downstream mail to arrive;
- mailbox `reply` routes back to the upstream sender rather than to an arbitrary next relay target;
- the ordinary shared mail send surface does not expose custom workflow headers or explicit caller-controlled threading fields;
- only one gateway reminder is effective at a time, so one reminder per active outbound loop does not scale well for one sender with many loops.
- `HOUMAO_MEMORY_DIR` is the durable memory lane and should not be repurposed as short-lived relay-loop control bookkeeping.
- the current mail-notifier reference doc claims digest-based deduplication, but the source currently computes unread digests only for audit/state and still re-enqueues unchanged unread snapshots on later cycles.

This change is documentation and packaged-skill guidance only. It does not add or change gateway, mailbox, or manager APIs.

## Goals / Non-Goals

**Goals:**

- Define one supported relay-loop pattern on top of current Houmao messaging, mailbox, and reminder surfaces.
- Make sender and receiver responsibilities explicit enough that repeated sends are safe under ambiguous network outcomes.
- Specify a scalable single-agent supervision model for many outbound loops from one sender.
- Keep the pattern honest about the live-gateway assumption and durability boundaries.

**Non-Goals:**

- Adding a new relay-loop API, queue, or mailbox protocol extension.
- Making mailbox thread ancestry the authoritative workflow identity for relay routing.
- Guaranteeing recovery across gateway restart or managed-agent replacement.
- Defining a fully generic distributed workflow engine beyond the packaged skill guidance.

## Decisions

### Document the workflow as a new advanced-usage pattern page

The implementation should add a new pattern page under `houmao-adv-usage-pattern/patterns/` and link it from the top-level `SKILL.md`.

Why:

- The behavior is a supported composition of existing skills, not a new direct-operation skill.
- The existing advanced-usage skill already owns this style of cross-skill workflow guidance.

Alternative considered:

- Expanding `houmao-agent-messaging` directly. Rejected because that skill owns communication-routing surfaces, not higher-level workflow protocols that combine messaging, mailbox, and reminders.

### Use queued gateway prompts for hop-to-hop handoff

The pattern should use queued gateway prompt delivery for each live hop from one agent to the next.

Why:

- The relay handoff is control work for an already-running managed agent.
- Gateway queue semantics fit better than raw send-keys or ad hoc direct prompt control.

Alternative considered:

- Raw gateway send-keys. Rejected because it is for exact terminal shaping rather than ordinary prompt-turn handoff.

### Use mailbox email for receipt, final result, and final-result acknowledgement

Each receiving agent should acknowledge ownership to its immediate upstream sender through email, and the designated loop egress should return the final result to the loop origin through email. The origin should acknowledge final-result receipt back to the egress.

Why:

- Email is the asynchronous shared surface already available to all participating agents.
- A receipt mail closes the ambiguity window for each sender without requiring a long-lived blocking turn.

Alternative considered:

- Using mailbox reply ancestry or mailbox thread identity as the full workflow identity. Rejected because reply routing goes back upstream and does not define arbitrary next-hop relay routing.

### Use explicit workflow tokens plus local ledger state

The pattern should define explicit identifiers such as `loop_id`, `handoff_id`, and result acknowledgement state, and require each agent to persist a local ledger row before sending downstream work.

Why:

- The current send surface does not provide a richer structured workflow envelope.
- Explicit local state is the only reliable way to support check-first, resend-second retry behavior and receiver-side deduplication.

Alternative considered:

- Reconstructing workflow identity from mailbox thread state alone. Rejected because the relay graph is not equivalent to one mailbox thread, especially when the egress returns directly to the origin.

### Store mutable relay-loop bookkeeping under `HOUMAO_JOB_DIR`

The pattern should direct agents to keep the mutable relay-loop ledger under `HOUMAO_JOB_DIR` by default, because that directory is the per-session scratch lane for runtime-managed work.

Why:

- Relay-loop bookkeeping is short-lived control state tied to one live pattern run.
- `HOUMAO_JOB_DIR` is the runtime-published scratch area intended for per-session outputs and bookkeeping.
- The pattern should not repurpose durable managed memory for transient retry counters, due times, or seen-handoff markers.

Alternative considered:

- Storing the ledger under `HOUMAO_MEMORY_DIR`. Rejected because managed memory is the durable notebook/archive lane and should not become the default home for ephemeral relay-control bookkeeping.

### Derive timing thresholds from context and ask the user when needed

The pattern should not present fixed universal receipt, result, or retry thresholds as if Houmao defines them. Instead, the pattern should direct agents to derive timing values from the current task context, any explicit user deadline, and the known live-gateway cadence boundaries.

When a timing value is materially important to correctness or user expectations and the agent cannot choose a sensible value from available context, the pattern should explicitly allow and recommend asking the user for that parameter rather than inventing an arbitrary threshold.

Why:

- The gateway exposes timing primitives and readiness gates, but it does not define one correct relay-loop SLA for every workflow.
- As a skill, the guidance can rely on the agent asking the user for missing workflow policy when that policy is not inferable locally.
- Thresholds such as receipt review time, overall result deadline, and maximum retry horizon are business-policy values, not protocol constants.

Alternative considered:

- Publishing one repository-wide default timeout table in the pattern itself. Rejected because that would overstate runtime guarantees and encourage agents to use arbitrary values even when the task clearly needs user input.

### Require senders to arm follow-up and end the turn

Any agent that sends a downstream handoff should persist state, send the handoff, arm follow-up for itself, and then end the current round instead of waiting actively for downstream email.

Why:

- Waiting in one long provider turn prevents ordinary notifier-style re-entry and is fragile under temporary network problems.

Alternative considered:

- In-turn active waiting. Rejected because it is brittle and defeats the point of asynchronous mailbox receipts.

### Use one supervisor reminder per sender for many outbound loops

For a sender managing many outbound loops, the pattern should recommend one repeating supervisor reminder that reopens local loop state, checks mailbox first, advances completed loops, and resends only due loops.

Why:

- Only one live reminder is effective at a time, so many per-loop reminders would block one another.
- A single supervisor reminder scales cleanly while keeping loop-level state in the ledger where it belongs.

Alternative considered:

- One reminder per loop. Rejected as the default because it scales poorly under the current reminder-selection model.

### Treat self-mail as optional durable checkpoint, not the primary clock

The pattern should allow one optional self-mail checkpoint or backlog marker per agent when the sender wants a durable local backlog anchor in addition to the live supervisor reminder.

Why:

- Self-mail is useful as durable local backlog.
- The relay-loop pattern should still remain correct when live reminder behavior is the primary wake path.

Alternative considered:

- Pure self-mail-only supervision. Rejected as the default because the loop still needs explicit mutable state and a predictable live check cadence.

### Include concrete text templates in the relay-loop pattern page

The relay-loop pattern page should include compact text-block templates that an agent can adapt directly for:

- downstream handoff request text,
- receipt email,
- final result email,
- final-result acknowledgement email,
- supervisor reminder text,
- optional self-mail checkpoint text when that variant is described.

Each template should name the exact workflow fields the agent is expected to record, including identifiers such as `loop_id` and `handoff_id`, target or sender identity, due or review timing, and completion conditions when relevant.

Why:

- The pattern is operational guidance for agents, not only an abstract protocol description.
- Concrete text blocks reduce the chance that agents omit the identifiers or due-state details that the resend and deduplication model depends on.

Alternative considered:

- Leaving the expected fields in prose only. Rejected because template blocks are easier for agents and operators to apply directly.

### Resync the mail-notifier reference docs to current source behavior

The implementation should update the gateway mail-notifier reference page so it documents the current notifier behavior accurately, including the fact that the current implementation may enqueue repeated notifier prompts for the same unchanged unread snapshot while the messages remain unread.

Why:

- The docs currently overstate notifier deduplication.
- The relay-loop guidance depends on understanding the real wake behavior when unread self-mail remains in the mailbox.

Alternative considered:

- Leaving the mismatch untouched because this change is primarily about advanced usage. Rejected because the relay-loop design discussion explicitly depends on notifier behavior, and the current docs would mislead readers about that behavior.

## Risks / Trade-offs

- [Live-gateway assumption] → The pattern is intentionally optimized for sessions whose gateways stay alive. Mitigation: state that this is not the durable fallback pattern for gateway restart or replacement.
- [Duplicate wake sources] → Supervisor reminder and optional self-mail can both wake the same agent. Mitigation: require idempotent ledger processing, mailbox check first, and same-id resend semantics.
- [More local bookkeeping] → Agents must maintain explicit loop state instead of relying on conversational context alone. Mitigation: provide a small required ledger shape and keep the identifiers minimal.
- [Documentation can over-promise] → Readers may assume this is a guaranteed distributed workflow protocol. Mitigation: state clearly that it is supported guidance over existing live/durable surfaces, not a new transactional runtime feature.

## Migration Plan

1. Add the delta spec for `houmao-adv-usage-pattern-skill`.
2. Add the delta spec for `docs-gateway-mail-notifier-reference`.
3. Add the new relay-loop pattern page and link it from `houmao-adv-usage-pattern/SKILL.md`.
4. Include concrete text-block templates in the relay-loop pattern page for request, mail, and reminder content.
5. Update `docs/reference/gateway/operations/mail-notifier.md` to match the current source notifier behavior.
6. Update system-skill asset tests to assert the new pattern page is packaged and referenced.

Rollback is low risk: remove the new pattern page, revert the top-level skill index entry, and revert the delta spec before archive.

## Open Questions

- None for artifact generation. The design intentionally avoids requiring any new runtime or mailbox behavior beyond currently supported surfaces.
