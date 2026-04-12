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
The packaged `houmao-adv-usage-pattern` skill SHALL include a supported elemental pairwise edge-loop pattern for workflows where one managed agent acts as a driver, sends work to exactly one worker for one loop round, and receives that same loop round's final result back from that same worker through mailbox email.

That pairwise edge-loop pattern SHALL describe the workflow through explicit roles:

- driver,
- worker.

That pairwise edge-loop pattern SHALL describe the pairwise topology as one two-node protocol round rather than a recursive tree, arbitrary graph, or master-owned multi-edge run plan.

That pairwise edge-loop pattern SHALL describe itself as a composition over the maintained direct-operation skills:

- `houmao-agent-messaging` for queued gateway prompt handoff between already-running managed agents,
- `houmao-agent-email-comms` for receipt email, final result email, and final-result acknowledgement email,
- `houmao-agent-gateway` for live reminder follow-up behavior used by the pattern,
- `houmao-agent-inspect` for read-only downstream worker peeking before due resends.

That pairwise edge-loop pattern SHALL state that it assumes all participating agents already have live attached gateways for that pattern run and SHALL NOT describe itself as the durable fallback pattern for gateway restart, gateway loss, or managed-agent replacement.

That pairwise edge-loop pattern SHALL include compact text-block templates that show the concrete information an agent is expected to record in:

- edge-loop request text,
- receipt email,
- final result email,
- final-result acknowledgement email,
- supervisor reminder text,
- optional self-mail checkpoint text when that variant is described.

That pairwise edge-loop pattern SHALL direct readers to a dedicated pairwise loop-planning skill when they need multiple pairwise edges, recursive child loops, a rendered control graph, master-owned run planning, or run-control actions.

#### Scenario: Pattern defines the pairwise roles and direct-skill composition
- **WHEN** an agent or operator opens the pairwise edge-loop pattern in `houmao-adv-usage-pattern`
- **THEN** the page identifies driver and worker explicitly
- **AND THEN** it routes prompt handoff work to `houmao-agent-messaging`, mailbox receipt and result work to `houmao-agent-email-comms`, reminder work to `houmao-agent-gateway`, and read-only downstream peeking to `houmao-agent-inspect`

#### Scenario: Final result closes back to the same driver that sent the request
- **WHEN** a reader follows the documented pairwise edge-loop message flow
- **THEN** the pattern shows the worker returning the final information to the same driver that sent the request for that edge-loop round
- **AND THEN** it does not describe the default pattern as having a distant loop egress return directly to some higher ancestor

#### Scenario: Pairwise page stays elemental
- **WHEN** a reader opens the pairwise edge-loop pattern page
- **THEN** the page describes one driver and one worker for one pairwise round
- **AND THEN** it does not teach recursive child edge-loops, parent edge identifiers, or arbitrary pairwise graph planning as part of the elemental pattern

#### Scenario: Pattern shows request and follow-up templates explicitly
- **WHEN** a reader needs to compose pairwise edge-loop request, mail, or reminder content from the pattern page
- **THEN** the page includes text-block templates for those artifacts
- **AND THEN** those templates name the workflow identifiers and follow-up fields that the reader is expected to record

### Requirement: Pairwise edge-loop guidance requires elemental local-close state, status-aware driver follow-up, and idempotent resend
The pairwise edge-loop pattern in `houmao-adv-usage-pattern` SHALL direct any driver that sends work to one worker to persist local edge-loop state before sending that request.

That local edge-loop state SHALL include explicit workflow identifiers and retry bookkeeping sufficient for idempotent resend and completion tracking for the elemental two-node round, including at minimum:

- `edge_loop_id`,
- peer identity,
- current phase,
- due time or next review time,
- retry or attempt count.

The pairwise edge-loop pattern SHALL NOT require or present `parent_edge_loop_id` as part of the elemental pairwise pattern.

The pairwise edge-loop pattern SHALL direct agents to store that mutable edge-loop ledger under `HOUMAO_JOB_DIR` by default as per-session scratch bookkeeping.

The pairwise edge-loop pattern SHALL NOT describe `HOUMAO_MEMORY_DIR` as the default or recommended location for this mutable edge-loop bookkeeping.

The pairwise edge-loop pattern SHALL describe timing thresholds such as receipt review time, result deadline, next review time, retry spacing, or retry horizon as workflow-policy values that agents derive from current task context and explicit user requirements rather than as fixed Houmao runtime constants.

When the agent cannot choose one of those materially important timing values sensibly from current context, the pairwise edge-loop pattern SHALL permit and recommend asking the user for that value instead of inventing an arbitrary threshold.

The pairwise edge-loop pattern SHALL direct the driver to:

1. persist the local edge-loop state,
2. send the worker request,
3. arm follow-up for itself,
4. stop the current round instead of waiting actively inside one live provider turn for downstream email.

The pairwise edge-loop pattern SHALL describe follow-up for the elemental pairwise round as local ledger review plus a supervisor reminder, with optional self-mail checkpoint or backlog marker when the driver wants a durable local backlog anchor in addition to the live reminder.

The pairwise edge-loop pattern SHALL direct driver follow-up to check mailbox state first for a matching receipt, final result, or final-result acknowledgement.

When the expected mailbox signal is still missing and the pairwise round is due for review, the pairwise edge-loop pattern SHALL direct the driver to peek the downstream worker for the same `edge_loop_id` through `houmao-agent-inspect` before resending the request.

When the `houmao-agent-inspect` peek is unavailable, stale, or inconclusive and the resend decision remains ambiguous, the pairwise edge-loop pattern SHALL allow a fresh prompt, ping, or direct `houmao-agent-messaging` message only as a last-resort status probe before resend.

When that `houmao-agent-inspect` peek or last-resort status probe shows that the worker still owns or is still actively working on the same `edge_loop_id`, the pairwise edge-loop pattern SHALL direct the driver to update local review state and schedule the next review instead of resending the request.

Only when the expected mailbox signal is missing, the pairwise round is due, and the worker cannot be observed or confirmed as still owning or actively working on the same `edge_loop_id`, the pairwise edge-loop pattern SHALL allow resend using the same explicit `edge_loop_id` rather than inventing a fresh identity for each retry.

The pairwise edge-loop pattern SHALL direct workers to deduplicate repeated edge-loop requests by those explicit identifiers and to resend the corresponding receipt or final result instead of duplicating work.

The pairwise edge-loop pattern SHALL NOT teach downstream child-loop dispatch, recursive local-close trees, or multi-edge graph planning as part of the elemental pairwise protocol.

#### Scenario: Driver follow-up ends the current round instead of waiting in-turn
- **WHEN** a driver in the pairwise edge-loop pattern hands work to a worker
- **THEN** the pattern directs that driver to persist local loop state, arm follow-up, and end the current round
- **AND THEN** it does not describe active waiting inside one long LLM chat round as the normal behavior

#### Scenario: Pairwise state excludes parent edge linkage by default
- **WHEN** a reader looks for the required identity fields in the elemental pairwise edge-loop pattern
- **THEN** the pattern requires `edge_loop_id` for the two-node round
- **AND THEN** it does not require `parent_edge_loop_id` as part of that elemental state model

#### Scenario: Mutable edge-loop ledger uses the job dir rather than managed memory
- **WHEN** a reader looks for where the pairwise edge-loop pattern stores retry counters, due times, and seen-request bookkeeping
- **THEN** the pattern directs that mutable ledger to `HOUMAO_JOB_DIR`
- **AND THEN** it does not present `HOUMAO_MEMORY_DIR` as the normal home for that ephemeral control state

#### Scenario: Timing thresholds come from workflow context or explicit user input
- **WHEN** a reader looks for how to choose receipt deadlines, review cadence, or retry horizons in the pairwise edge-loop pattern
- **THEN** the pattern explains that those values come from workflow context and explicit user requirements rather than fixed Houmao defaults
- **AND THEN** it allows the agent to ask the user when a materially important timing value is not inferable from context

#### Scenario: Driver uses read-only peek before resending a due pairwise request
- **WHEN** a driver's pairwise follow-up does not find the expected receipt or result in mailbox state
- **AND WHEN** the local ledger says the `edge_loop_id` is due for review
- **THEN** the pattern directs the driver to use `houmao-agent-inspect` to peek the downstream worker for that `edge_loop_id` before resending
- **AND THEN** it does not treat a fresh prompt, ping, or direct message as the default status check

#### Scenario: Driver uses active status probe only as last resort
- **WHEN** the driver's `houmao-agent-inspect` peek is unavailable, stale, or inconclusive
- **AND WHEN** the resend decision remains ambiguous
- **THEN** the pattern allows a fresh prompt, ping, or direct message only as a last-resort status probe before resend

#### Scenario: Driver defers resend when worker is still working
- **WHEN** the driver's `houmao-agent-inspect` peek or last-resort status probe shows that the downstream worker still owns or is still actively working on the same `edge_loop_id`
- **THEN** the pattern directs the driver to update local review state and schedule another review
- **AND THEN** it does not resend the pairwise request

#### Scenario: Repeated edge-loop request is deduplicated by workflow identifier
- **WHEN** a worker encounters the same `edge_loop_id` again after an ambiguous resend
- **THEN** the pattern directs that worker to treat the request as already owned
- **AND THEN** it resends the matching receipt or final result without duplicating work

#### Scenario: Pairwise graph composition redirects to dedicated planning
- **WHEN** a reader needs recursive child edge-loops, multiple pairwise edges, or a rendered pairwise control graph
- **THEN** the advanced-usage pairwise pattern directs the reader to a dedicated pairwise loop-planning skill
- **AND THEN** it does not describe those composed topologies as part of the elemental pairwise protocol

### Requirement: `houmao-adv-usage-pattern` documents a supported multi-agent relay-loop composition
The packaged `houmao-adv-usage-pattern` skill SHALL include a supported elemental relay-loop pattern for workflows where one managed agent is the master/loop origin, work follows one ordered relay lane through one or more downstream managed agents, and a designated loop egress agent returns the final information to the master/loop origin through mailbox email.

That relay-loop pattern SHALL describe the workflow through explicit roles:

- master or loop origin,
- loop ingress,
- relay agent when the lane has intermediate agents,
- loop egress.

That relay-loop pattern SHALL describe one ordered N-node relay lane rather than fan-out, multiple relay lanes, or a graph composed of multiple loops.

That relay-loop pattern SHALL describe itself as a composition over the maintained direct-operation skills:

- `houmao-agent-messaging` for queued gateway prompt handoff between already-running managed agents,
- `houmao-agent-email-comms` for receipt email, final result email, and final-result acknowledgement email,
- `houmao-agent-gateway` for live reminder follow-up behavior used by the pattern,
- `houmao-agent-inspect` for read-only downstream peeking before due relay handoff resends.

The relay-loop pattern SHALL state that it assumes all participating agents already have live attached gateways for that pattern run and SHALL NOT describe itself as the durable fallback pattern for gateway restart, gateway loss, or managed-agent replacement.

The relay-loop pattern SHALL include compact text-block templates that show the concrete information an agent is expected to record in:

- downstream handoff request text,
- receipt email,
- final result email,
- final-result acknowledgement email,
- supervisor reminder text,
- optional self-mail checkpoint text when that variant is described.

That relay-loop pattern SHALL direct readers to `houmao-agent-loop-generic` when they need multi-lane routing, fan-out, route policy authoring, a rendered relay graph, master-owned run planning, relay run-control actions, or mixed pairwise/relay graph decomposition.

#### Scenario: Pattern defines the relay roles and direct-skill composition
- **WHEN** an agent or operator opens the relay-loop pattern in `houmao-adv-usage-pattern`
- **THEN** the page identifies the master/loop origin, loop ingress, optional relay agent, and loop egress explicitly
- **AND THEN** it routes prompt handoff work to `houmao-agent-messaging`, mailbox receipt and result work to `houmao-agent-email-comms`, reminder work to `houmao-agent-gateway`, and read-only downstream peeking to `houmao-agent-inspect`

#### Scenario: Loop egress returns final information to the origin through email
- **WHEN** a reader follows the documented relay-loop message flow
- **THEN** the pattern shows the designated loop egress returning the final information to the master/loop origin through mailbox email
- **AND THEN** it does not describe the final answer as returning only to the immediate upstream relay by default

#### Scenario: Relay page stays focused on one ordered lane
- **WHEN** a reader opens the relay-loop pattern page
- **THEN** the page describes one ordered N-node relay lane with one master/loop origin and one final egress
- **AND THEN** it does not teach fan-out, multiple relay lanes, or a graph composed of multiple relay loops as the elemental pattern

#### Scenario: Pattern shows request and follow-up templates explicitly
- **WHEN** a reader needs to compose relay-loop request, mail, or reminder content from the pattern page
- **THEN** the page includes text-block templates for those artifacts
- **AND THEN** those templates name the workflow identifiers and follow-up fields that the reader is expected to record

### Requirement: Relay-loop guidance requires explicit loop state, status-aware sender follow-up, and idempotent resend
The relay-loop pattern in `houmao-adv-usage-pattern` SHALL direct any agent that sends the next handoff in one ordered relay lane to persist local loop state before sending that handoff.

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

The relay-loop pattern SHALL describe follow-up for one ordered relay lane as local ledger review plus a supervisor reminder, with optional self-mail checkpoint or backlog marker when the responsible agent wants a durable local backlog anchor in addition to the live reminder.

The relay-loop pattern SHALL direct sender follow-up to check mailbox state first for a matching receipt, final result, or final-result acknowledgement.

When the expected mailbox signal is still missing and the relay handoff is due for review, the relay-loop pattern SHALL direct the upstream sender to use `houmao-agent-inspect` read-only surfaces to peek the downstream agent for the same `loop_id` and `handoff_id` before resending the handoff.

When the `houmao-agent-inspect` peek is unavailable, stale, or inconclusive and the resend decision remains ambiguous, the relay-loop pattern SHALL allow a fresh prompt, ping, or direct `houmao-agent-messaging` message only as a last-resort status probe before resend.

When that `houmao-agent-inspect` peek or last-resort status probe shows that the downstream agent still owns or is still actively working on the same `loop_id` and `handoff_id`, the relay-loop pattern SHALL direct the upstream sender to update local review state and schedule the next review instead of resending the handoff.

Only when the expected mailbox signal is missing, the relay handoff is due, and the downstream agent cannot be observed or confirmed as still owning or actively working on the same `loop_id` and `handoff_id`, the relay-loop pattern SHALL allow resend using the same explicit workflow identifiers rather than inventing a fresh downstream handoff identity for each retry.

The relay-loop pattern SHALL direct receivers to deduplicate repeated handoffs by those explicit identifiers and to resend the corresponding receipt or final result instead of forwarding duplicate downstream work.

The relay-loop pattern SHALL NOT present many outbound loops, fan-out, or a graph of relay loops as the elemental relay-loop state model.

#### Scenario: Sender follow-up ends the current round instead of waiting in-turn
- **WHEN** a sender in the relay-loop pattern hands work to a downstream agent
- **THEN** the pattern directs that sender to persist local loop state, arm follow-up, and end the current round
- **AND THEN** it does not describe active waiting inside one long LLM chat round as the normal behavior

#### Scenario: Single relay lane uses local follow-up state
- **WHEN** an agent is responsible for an active handoff or final-result acknowledgement in one ordered relay lane
- **THEN** the pattern directs that agent to use local ledger review plus a supervisor reminder as the default live wake path
- **AND THEN** it does not describe many outbound relay loops or one reminder per active loop as the elemental state model

#### Scenario: Upstream sender uses read-only peek before resending a due relay handoff
- **WHEN** an upstream sender's relay follow-up does not find the expected receipt or result in mailbox state
- **AND WHEN** the local ledger says the `loop_id` and `handoff_id` are due for review
- **THEN** the pattern directs the upstream sender to use `houmao-agent-inspect` read-only surfaces to peek the downstream agent for that handoff before resending
- **AND THEN** it does not treat a fresh prompt, ping, or direct message as the default status check

#### Scenario: Upstream sender uses active status probe only as last resort
- **WHEN** the upstream sender's `houmao-agent-inspect` peek is unavailable, stale, or inconclusive
- **AND WHEN** the resend decision remains ambiguous
- **THEN** the pattern allows a fresh prompt, ping, or direct message only as a last-resort status probe before resend

#### Scenario: Upstream sender defers resend when downstream relay agent is still working
- **WHEN** the upstream sender's `houmao-agent-inspect` peek or last-resort status probe shows that the downstream agent still owns or is still actively working on the same `loop_id` and `handoff_id`
- **THEN** the pattern directs the upstream sender to update local review state and schedule another review
- **AND THEN** it does not resend the relay handoff

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
- **AND THEN** it resends the matching receipt or final result without duplicating downstream work

#### Scenario: Relay graph composition redirects to dedicated planning
- **WHEN** a reader needs multiple relay lanes, fan-out, route policy authoring, or a rendered relay graph
- **THEN** the advanced-usage relay pattern directs the reader to `houmao-agent-loop-relay`
- **AND THEN** it does not describe those composed topologies as part of the elemental relay protocol

### Requirement: Advanced-usage chooser guidance distinguishes pairwise edge-loops from forward relay loops
The packaged `houmao-adv-usage-pattern` skill SHALL explain that the pairwise driver-worker edge-loop pattern and the forward relay-loop pattern are sibling elemental advanced-usage patterns with different routing behavior.

That chooser guidance SHALL state that the pairwise edge-loop pattern is the better fit when:

- exactly one driver sends one worker request for one edge-loop round,
- the final result for that round should always return to the same driver that sent the request,
- the reader needs the atomic local-close protocol that a dedicated pairwise or generic loop-planning skill may compose into larger topologies.

That chooser guidance SHALL state that the forward relay-loop pattern is the better fit when:

- one master/loop origin starts one ordered N-node relay lane,
- ownership should keep moving forward along that lane,
- a designated downstream loop egress should return the final result directly to the master/loop origin rather than only to its immediate upstream sender.

That chooser guidance SHALL state that composed topologies, rendered graphs, mixed pairwise/relay graph decomposition, multi-edge pairwise runs, multi-lane relay routes, route/delegation policies, and start/status/stop run-control actions belong in dedicated loop-planning skills rather than in the elemental advanced-usage pattern pages.

That chooser guidance SHALL direct generic composed graph planning to `houmao-agent-loop-generic`.

That chooser guidance SHALL preserve the specialized pairwise loop-planning skills as explicit pairwise-only choices when a user asks for one of those pairwise skills by name or when a workflow has already selected a pairwise-only planning lane.

#### Scenario: Reader can choose the pairwise pattern for one local-close delegation round
- **WHEN** an agent or operator compares the advanced-usage loop patterns
- **THEN** the guidance explains that the pairwise edge-loop pattern is for one local-close driver-worker delegation round
- **AND THEN** it does not describe recursive pairwise graphs as the elemental pairwise pattern

#### Scenario: Reader can choose the forward relay pattern for one distant-return relay lane
- **WHEN** an agent or operator compares the advanced-usage loop patterns
- **THEN** the guidance explains that the forward relay-loop pattern is for ownership that moves along one ordered lane until a later egress returns the final result to the master/loop origin
- **AND THEN** it does not describe the pairwise edge-loop pattern as the default answer for that distant-return routing case

#### Scenario: Reader can route composed loop plans to dedicated skills
- **WHEN** an agent or operator needs a rendered loop graph, multiple pairwise edges, multiple relay lanes, mixed pairwise/relay graph decomposition, or run-control actions
- **THEN** the guidance directs generic composed graph planning to `houmao-agent-loop-generic`
- **AND THEN** it keeps `houmao-adv-usage-pattern` focused on elemental protocol guidance

### Requirement: `houmao-adv-usage-pattern` gateway-attach references defer to foreground-first lifecycle guidance
When a packaged `houmao-adv-usage-pattern` page mentions gateway attach or gateway discovery as part of a composed workflow, that page SHALL route attach posture decisions to `houmao-agent-gateway`.

Composition guidance SHALL NOT present background gateway execution as implicit setup for advanced usage patterns.

If an advanced usage pattern requires or recommends that a live gateway already be attached, the pattern guidance SHALL treat foreground same-session auxiliary-window attach as the default for tmux-backed managed sessions and detached background gateway execution as explicit user intent governed by `houmao-agent-gateway`.

#### Scenario: Self-wakeup pattern delegates gateway attach posture
- **WHEN** the self-wakeup via self-mail pattern tells the agent to use `houmao-agent-gateway` for gateway attach or discovery
- **THEN** the pattern guidance defers attach posture selection to `houmao-agent-gateway`
- **AND THEN** it does not imply that background gateway execution is the default setup for the pattern

#### Scenario: Advanced pattern background gateway execution remains explicit
- **WHEN** an advanced usage pattern needs a live gateway and the user has not explicitly requested background gateway execution
- **THEN** the pattern guidance does not tell the agent to choose a background gateway launch or attach path
- **AND THEN** it preserves the foreground-first gateway lifecycle rule from the owning gateway skill

