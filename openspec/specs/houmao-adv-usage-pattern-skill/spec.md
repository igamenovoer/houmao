## Purpose
Define the packaged advanced-usage system skill that documents supported multi-skill workflow compositions on top of Houmao's direct-operation skills.
## Requirements
### Requirement: Houmao provides a packaged `houmao-adv-usage-pattern` system skill
The system SHALL package a Houmao-owned system skill named `houmao-adv-usage-pattern` under the maintained system-skill asset root.

The top-level `SKILL.md` for that packaged skill SHALL serve as an entry index for advanced supported workflow compositions rather than as a flattened direct-operation document.

That skill SHALL organize its guidance through local pattern pages beneath the same packaged skill directory.

That skill SHALL remain distinct from the direct-operation skills that own the supported mailbox, gateway, messaging, and lifecycle surfaces.

#### Scenario: Installed advanced skill exposes an index and local pattern pages
- **WHEN** an agent or operator opens the installed `houmao-adv-usage-pattern` skill
- **THEN** the top-level `SKILL.md` acts as an index of supported advanced workflow compositions
- **AND THEN** the detailed workflow guidance lives in local pattern pages under the same packaged skill directory

### Requirement: `houmao-adv-usage-pattern` self-wakeup guidance composes existing Houmao skills
The packaged `houmao-adv-usage-pattern` skill SHALL include a self-notification pattern family that compares two supported ways for a managed agent to notify itself about later work:

- live gateway reminders through `/v1/reminders`,
- self-mail reminders that re-enter through unread mailbox work.

That pattern family SHALL describe self-notification as a composition over the maintained direct-operation skills:

- `houmao-agent-gateway` for live gateway reminder creation, inspection, update, and deletion through `/v1/reminders`,
- `houmao-agent-email-comms` for mailbox send, check, read, reply, and mailbox-state follow-up work around self-mail reminders,
- `houmao-process-emails-via-gateway` for notifier-driven unread-mail rounds when the self-notification mode is self-mail.

The pattern family SHALL explain that gateway reminders are the preferred mode when the task is high-priority, should stay focused ahead of unrelated new incoming mail, or benefits from one-off, repeating, ranking, or pause behavior.

The pattern family SHALL explain that self-mail reminders are the preferred mode when the reminder must survive gateway shutdown or restart, or when the later round should be allowed to re-triage that reminder together with newly arrived unread mail.

For multi-step work, the pattern family SHALL direct the agent to keep the detailed substep list in local todo or scratch state and use one reminder or self-mail item per major work chunk rather than one mailbox reminder per tiny substep.

#### Scenario: Focused high-priority self-notification selects gateway reminders
- **WHEN** a managed agent needs to remind itself about high-priority work that should be handled before unrelated new incoming mail
- **THEN** the advanced-usage skill directs that agent to the live gateway reminder mode through `houmao-agent-gateway`
- **AND THEN** it describes that mode as the focus-first self-notification path rather than routing the agent through mailbox backlog first

#### Scenario: Durable or inbox-integrated self-notification selects self-mail
- **WHEN** a managed agent needs a reminder backlog that should survive gateway shutdown or that may be reprioritized together with other unread mail later
- **THEN** the advanced-usage skill directs that agent to the self-mail mode through `houmao-agent-email-comms` plus notifier-driven unread-mail rounds
- **AND THEN** it describes that mode as the durable or inbox-integrated self-notification path

#### Scenario: Multi-step work uses local todo state plus one major-chunk reminder
- **WHEN** a managed agent needs to continue a multi-step task later
- **THEN** the advanced-usage skill directs the agent to keep the detailed checklist in local todo or scratch state
- **AND THEN** it does not describe one mailbox reminder per tiny substep as the default pattern

### Requirement: `houmao-adv-usage-pattern` states self-wakeup durability boundaries honestly
The self-notification pattern family in `houmao-adv-usage-pattern` SHALL describe the focus, scheduling, and durability boundaries of gateway reminders and self-mail honestly.

For live gateway reminders, the pattern family SHALL state that:

- `/v1/reminders` is live gateway state rather than durable recovery state,
- reminder entries do not survive gateway shutdown or restart,
- reminder delivery does not mix with newly arrived unread mailbox traffic,
- the mode supports richer live behavior such as one-off timing, repeating cadence, ranking, and pause semantics.

For self-mail reminders, the pattern family SHALL state that:

- unread self-mail is the durable backlog for that mode,
- that durable backlog can survive gateway loss because it is mailbox state rather than gateway process state,
- later notifier-driven rounds inspect that backlog through ordinary unread-mail flow and therefore may encounter self-reminders together with unrelated new incoming mail.

When the caller is unsure and durable recovery is not an explicit requirement, the pattern family SHALL recommend `/v1/reminders` as the default self-notification mode because it provides the richer live reminder feature set.

The pattern family SHALL NOT claim guaranteed unfinished-work recovery beyond the actual mailbox unread state and live gateway contracts.

#### Scenario: Reminder mode supports focus-first work without mixing with new mail
- **WHEN** an agent or operator reads the reminder mode guidance in the advanced-usage self-notification family
- **THEN** the page states that live gateway reminders do not mix with newly arrived unread mailbox traffic
- **AND THEN** it describes that mode as the better fit for "work on this first" behavior

#### Scenario: Self-mail mode stays durable but mixes with unread mailbox triage
- **WHEN** an agent or operator reads the self-mail mode guidance in the advanced-usage self-notification family
- **THEN** the page states that unread self-mail is the durable backlog for that mode
- **AND THEN** it states that later unread-mail rounds may mix those self-reminders with unrelated new incoming mail

#### Scenario: Default recommendation prefers reminders when durability is not required
- **WHEN** an agent or operator needs self-notification guidance without an explicit durability requirement
- **THEN** the advanced-usage skill recommends live gateway reminders as the default mode
- **AND THEN** it still states that self-mail is the correct choice when gateway-surviving durability is required

### Requirement: `houmao-adv-usage-pattern` documents a supported pairwise driver-worker edge-loop composition
The packaged `houmao-adv-usage-pattern` skill SHALL include a supported pairwise edge-loop pattern for workflows where one managed agent acts as a driver, sends work to exactly one worker for one loop round, and receives that same loop round's final result back from that same worker through mailbox email.

That pairwise edge-loop pattern SHALL describe the workflow through explicit roles:

- driver,
- worker.

That pairwise edge-loop pattern SHALL describe itself as a composition over the maintained direct-operation skills:

- `houmao-agent-messaging` for queued gateway prompt handoff between already-running managed agents,
- `houmao-agent-email-comms` for receipt email, final result email, and final-result acknowledgement email,
- `houmao-agent-gateway` for live reminder follow-up behavior used by the pattern.

That pairwise edge-loop pattern SHALL state that it assumes all participating agents already have live attached gateways for that pattern run and SHALL NOT describe itself as the durable fallback pattern for gateway restart, gateway loss, or managed-agent replacement.

That pairwise edge-loop pattern SHALL include compact text-block templates that show the concrete information an agent is expected to record in:

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
