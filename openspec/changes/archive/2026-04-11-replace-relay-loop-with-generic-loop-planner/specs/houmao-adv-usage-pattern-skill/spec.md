## MODIFIED Requirements

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
