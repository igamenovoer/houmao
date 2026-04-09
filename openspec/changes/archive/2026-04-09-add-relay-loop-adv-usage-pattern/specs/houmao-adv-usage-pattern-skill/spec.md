## ADDED Requirements

### Requirement: `houmao-adv-usage-pattern` documents a supported multi-agent relay-loop composition
The packaged `houmao-adv-usage-pattern` skill SHALL include a supported relay-loop pattern for workflows where one managed agent hands work to a loop ingress agent, one or more relay agents may continue forwarding that work, and a designated loop egress agent returns the final information to the loop origin through mailbox email.

That relay-loop pattern SHALL describe the workflow through explicit roles:

- loop origin,
- loop ingress,
- relay agent,
- loop egress.

That relay-loop pattern SHALL describe itself as a composition over the maintained direct-operation skills:

- `houmao-agent-messaging` for queued gateway prompt handoff between already-running managed agents,
- `houmao-agent-email-comms` for receipt email, final result email, and final-result acknowledgement email,
- `houmao-agent-gateway` for live reminder follow-up behavior used by the pattern.

The relay-loop pattern SHALL state that it assumes all participating agents already have live attached gateways for that pattern run and SHALL NOT describe itself as the durable fallback pattern for gateway restart, gateway loss, or managed-agent replacement.

The relay-loop pattern SHALL include compact text-block templates that show the concrete information an agent is expected to record in:

- downstream handoff request text,
- receipt email,
- final result email,
- final-result acknowledgement email,
- supervisor reminder text,
- optional self-mail checkpoint text when that variant is described.

#### Scenario: Pattern defines the relay roles and direct-skill composition
- **WHEN** an agent or operator opens the relay-loop pattern in `houmao-adv-usage-pattern`
- **THEN** the page identifies loop origin, loop ingress, relay agent, and loop egress explicitly
- **AND THEN** it routes prompt handoff work to `houmao-agent-messaging`, mailbox receipt and result work to `houmao-agent-email-comms`, and reminder work to `houmao-agent-gateway`

#### Scenario: Loop egress returns final information to the origin through email
- **WHEN** a reader follows the documented relay-loop message flow
- **THEN** the pattern shows the designated loop egress returning the final information to the loop origin through mailbox email
- **AND THEN** it does not describe the final answer as returning only to the immediate upstream relay by default

#### Scenario: Pattern shows request and follow-up templates explicitly
- **WHEN** a reader needs to compose relay-loop request, mail, or reminder content from the pattern page
- **THEN** the page includes text-block templates for those artifacts
- **AND THEN** those templates name the workflow identifiers and follow-up fields that the reader is expected to record

### Requirement: Relay-loop guidance requires explicit loop state, sender follow-up, and idempotent retry
The relay-loop pattern in `houmao-adv-usage-pattern` SHALL direct any agent that sends a downstream handoff to persist local loop state before sending that handoff.

That local loop state SHALL include explicit workflow identifiers and retry bookkeeping sufficient for idempotent resend and completion tracking, including at minimum:

- `loop_id`,
- `handoff_id`,
- downstream target identity,
- current phase,
- due time or next review time,
- retry or attempt count.

The relay-loop pattern SHALL direct agents to store that mutable loop ledger under `HOUMAO_JOB_DIR` by default as per-session scratch bookkeeping.

The relay-loop pattern SHALL NOT describe `HOUMAO_MEMORY_DIR` as the default or recommended location for this mutable relay-loop bookkeeping.

The relay-loop pattern SHALL describe timing thresholds such as receipt review time, result deadline, next review time, retry spacing, or retry horizon as workflow-policy values that agents derive from current task context and explicit user requirements rather than as fixed Houmao runtime constants.

When the agent cannot choose one of those materially important timing values sensibly from current context, the relay-loop pattern SHALL permit and recommend asking the user for that value instead of inventing an arbitrary threshold.

The relay-loop pattern SHALL direct the sender to:

1. persist the local loop state,
2. send the downstream handoff,
3. arm follow-up for itself,
4. stop the current round instead of waiting actively inside one live provider turn for downstream email.

The relay-loop pattern SHALL describe the default follow-up model for a sender with many outbound loops as:

- one local loop ledger as the authoritative mutable state,
- one supervisor reminder as the live loop clock,
- optional self-mail checkpoint or backlog marker when the sender wants a durable local backlog anchor in addition to the live reminder.

The relay-loop pattern SHALL direct retry behavior to check mailbox state first and resend second using the same explicit workflow identifiers rather than inventing a fresh downstream handoff identity for each retry.

The relay-loop pattern SHALL direct receivers to deduplicate repeated handoffs by those explicit identifiers and to resend the corresponding receipt or final result instead of forwarding duplicate downstream work.

#### Scenario: Sender follow-up ends the current round instead of waiting in-turn
- **WHEN** a sender in the relay-loop pattern hands work to a downstream agent
- **THEN** the pattern directs that sender to persist local loop state, arm follow-up, and end the current round
- **AND THEN** it does not describe active waiting inside one long LLM chat round as the normal behavior

#### Scenario: Many outbound loops use one supervisor reminder instead of one reminder per loop
- **WHEN** one sender has multiple outbound relay loops in flight at the same time
- **THEN** the pattern directs that sender to keep the loop rows in one local ledger and use one supervisor reminder as the default live wake path
- **AND THEN** it does not describe one live reminder per active loop as the default scalable pattern

#### Scenario: Mutable relay-loop ledger uses the job dir rather than managed memory
- **WHEN** a reader looks for where the relay-loop pattern stores retry counters, due times, and seen-handoff bookkeeping
- **THEN** the pattern directs that mutable ledger to `HOUMAO_JOB_DIR`
- **AND THEN** it does not present `HOUMAO_MEMORY_DIR` as the normal home for that ephemeral control state

#### Scenario: Timing thresholds come from workflow context or explicit user input
- **WHEN** a reader looks for how to choose receipt deadlines, review cadence, or retry horizons in the relay-loop pattern
- **THEN** the pattern explains that those values come from workflow context and explicit user requirements rather than fixed Houmao defaults
- **AND THEN** it allows the agent to ask the user when a materially important timing value is not inferable from context

#### Scenario: Repeated handoff is deduplicated by workflow identifiers
- **WHEN** a receiver encounters the same `loop_id` and `handoff_id` again after an ambiguous resend
- **THEN** the pattern directs that receiver to treat the handoff as already owned
- **AND THEN** it resends the matching receipt or final result without duplicating downstream fan-out work
