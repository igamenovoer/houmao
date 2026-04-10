## ADDED Requirements

### Requirement: `houmao-adv-usage-pattern` documents a supported pairwise driver-worker edge-loop composition
The packaged `houmao-adv-usage-pattern` skill SHALL include a supported pairwise edge-loop pattern for workflows where one managed agent acts as a driver, sends work to exactly one worker for one loop round, and receives that same loop round's final result back from that same worker through mailbox email.

That pairwise edge-loop pattern SHALL describe the workflow through explicit roles:

- driver,
- worker.

That pairwise edge-loop pattern SHALL describe itself as a composition over the maintained direct-operation skills:

- `houmao-agent-messaging` for queued gateway prompt handoff between already-running managed agents,
- `houmao-agent-email-comms` for receipt email, final result email, and final-result acknowledgement email,
- `houmao-agent-gateway` for live reminder follow-up behavior used by the pattern.

The pairwise edge-loop pattern SHALL state that it assumes all participating agents already have live attached gateways for that pattern run and SHALL NOT describe itself as the durable fallback pattern for gateway restart, gateway loss, or managed-agent replacement.

The pairwise edge-loop pattern SHALL include compact text-block templates that show the concrete information an agent is expected to record in:

- edge-loop request text,
- receipt email,
- final result email,
- final-result acknowledgement email,
- supervisor reminder text,
- optional self-mail checkpoint text when that variant is described.

#### Scenario: Pattern defines the pairwise roles and direct-skill composition
- **WHEN** an agent or operator opens the pairwise edge-loop pattern in `houmao-adv-usage-pattern`
- **THEN** the page identifies driver and worker explicitly
- **AND THEN** it routes prompt handoff work to `houmao-agent-messaging`, mailbox receipt and result work to `houmao-agent-email-comms`, and reminder work to `houmao-agent-gateway`

#### Scenario: Final result closes back to the same driver that sent the request
- **WHEN** a reader follows the documented pairwise edge-loop message flow
- **THEN** the pattern shows the worker returning the final information to the same driver that sent the request for that edge-loop round
- **AND THEN** it does not describe the default pattern as having a distant loop egress return directly to some higher ancestor

#### Scenario: Pattern shows request and follow-up templates explicitly
- **WHEN** a reader needs to compose pairwise edge-loop request, mail, or reminder content from the pattern page
- **THEN** the page includes text-block templates for those artifacts
- **AND THEN** those templates name the workflow identifiers and follow-up fields that the reader is expected to record

### Requirement: Pairwise edge-loop guidance requires local-close recursion, explicit loop state, and idempotent retry
The pairwise edge-loop pattern in `houmao-adv-usage-pattern` SHALL direct any driver that sends work to a worker to persist local edge-loop state before sending that request.

That local edge-loop state SHALL include explicit workflow identifiers and retry bookkeeping sufficient for idempotent resend and completion tracking, including at minimum:

- `edge_loop_id`,
- peer identity,
- current phase,
- due time or next review time,
- retry or attempt count.

When the worker is itself handling one parent edge-loop while driving child edge-loops downstream, the pairwise edge-loop pattern SHALL describe optional `parent_edge_loop_id` linkage so the child loop can be associated with the parent loop without making the child loop's result bypass the immediate driver.

The pairwise edge-loop pattern SHALL direct agents to store that mutable edge-loop ledger under `HOUMAO_JOB_DIR` by default as per-session scratch bookkeeping.

The pairwise edge-loop pattern SHALL NOT describe `HOUMAO_MEMORY_DIR` as the default or recommended location for this mutable edge-loop bookkeeping.

The pairwise edge-loop pattern SHALL describe timing thresholds such as receipt review time, result deadline, next review time, retry spacing, or retry horizon as workflow-policy values that agents derive from current task context and explicit user requirements rather than as fixed Houmao runtime constants.

When the agent cannot choose one of those materially important timing values sensibly from current context, the pairwise edge-loop pattern SHALL permit and recommend asking the user for that value instead of inventing an arbitrary threshold.

The pairwise edge-loop pattern SHALL direct the driver to:

1. persist the local edge-loop state,
2. send the worker request,
3. arm follow-up for itself,
4. stop the current round instead of waiting actively inside one live provider turn for downstream email.

The pairwise edge-loop pattern SHALL describe the default follow-up model for one agent with many edge-loops in flight as:

- one local loop ledger as the authoritative mutable state,
- one supervisor reminder as the live loop clock,
- optional self-mail checkpoint or backlog marker when the sender wants a durable local backlog anchor in addition to the live reminder.

The pairwise edge-loop pattern SHALL direct retry behavior to check mailbox state first and resend second using the same explicit `edge_loop_id` rather than inventing a fresh identity for each retry.

The pairwise edge-loop pattern SHALL direct workers to deduplicate repeated edge-loop requests by those explicit identifiers and to resend the corresponding receipt or final result instead of duplicating work.

If a worker needs downstream help from another agent, the pairwise edge-loop pattern SHALL direct that worker to open one or more child edge-loops that each close back to that same worker before the worker reports its own final result upstream.

#### Scenario: Driver follow-up ends the current round instead of waiting in-turn
- **WHEN** a driver in the pairwise edge-loop pattern hands work to a worker
- **THEN** the pattern directs that driver to persist local loop state, arm follow-up, and end the current round
- **AND THEN** it does not describe active waiting inside one long LLM chat round as the normal behavior

#### Scenario: Worker closes child edge-loops locally before replying upstream
- **WHEN** a worker in one pairwise edge-loop needs help from another downstream agent
- **THEN** the pattern directs that worker to open one or more child edge-loops that close back to that same worker
- **AND THEN** the worker reports its own final result upstream only after those child edge-loops are locally integrated

#### Scenario: Mutable edge-loop ledger uses the job dir rather than managed memory
- **WHEN** a reader looks for where the pairwise edge-loop pattern stores retry counters, due times, and seen-request bookkeeping
- **THEN** the pattern directs that mutable ledger to `HOUMAO_JOB_DIR`
- **AND THEN** it does not present `HOUMAO_MEMORY_DIR` as the normal home for that ephemeral control state

#### Scenario: Timing thresholds come from workflow context or explicit user input
- **WHEN** a reader looks for how to choose receipt deadlines, review cadence, or retry horizons in the pairwise edge-loop pattern
- **THEN** the pattern explains that those values come from workflow context and explicit user requirements rather than fixed Houmao defaults
- **AND THEN** it allows the agent to ask the user when a materially important timing value is not inferable from context

#### Scenario: Many concurrent edge-loops use one supervisor reminder instead of one reminder per loop
- **WHEN** one driver has multiple pairwise edge-loops in flight at the same time
- **THEN** the pattern directs that driver to keep the loop rows in one local ledger and use one supervisor reminder as the default live wake path
- **AND THEN** it does not describe one live reminder per active edge-loop as the default scalable pattern

#### Scenario: Repeated edge-loop request is deduplicated by workflow identifier
- **WHEN** a worker encounters the same `edge_loop_id` again after an ambiguous resend
- **THEN** the pattern directs that worker to treat the request as already owned
- **AND THEN** it resends the matching receipt or final result without duplicating downstream work

### Requirement: Advanced-usage chooser guidance distinguishes pairwise edge-loops from forward relay loops
The packaged `houmao-adv-usage-pattern` skill SHALL explain that the pairwise driver-worker edge-loop pattern and the forward relay-loop pattern are sibling advanced-usage patterns with different routing behavior.

That chooser guidance SHALL state that the pairwise edge-loop pattern is the better fit when:

- every delegation edge should close locally,
- the intermediate agent must integrate child results before replying upstream,
- the final result for one loop round should always return to the same agent that sent that round's request.

That chooser guidance SHALL state that the forward relay-loop pattern is the better fit when:

- ownership should keep moving forward across agents,
- a designated downstream loop egress should return the final result directly to a more distant origin rather than only to its immediate driver.

#### Scenario: Reader can choose the pairwise pattern for local-close delegation
- **WHEN** an agent or operator compares the advanced-usage loop patterns
- **THEN** the guidance explains that the pairwise edge-loop pattern is for local-close driver-worker delegation
- **AND THEN** it describes that pattern as the better fit when intermediate agents must integrate child results before replying upstream

#### Scenario: Reader can choose the forward relay pattern for distant-return routing
- **WHEN** an agent or operator compares the advanced-usage loop patterns
- **THEN** the guidance explains that the forward relay-loop pattern is for ownership that keeps moving forward until a later egress returns the final result
- **AND THEN** it does not describe the pairwise edge-loop pattern as the default answer for that distant-return routing case
