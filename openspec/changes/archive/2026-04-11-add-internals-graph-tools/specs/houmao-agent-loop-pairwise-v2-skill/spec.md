## ADDED Requirements

### Requirement: V2 authoring guidance uses internal graph tools for routing-packet validation
The packaged `houmao-agent-loop-pairwise-v2` guidance SHALL mention `houmao-mgr internals graph high` as the preferred deterministic graph helper surface when an agent needs to compute or validate topology-derived routing-packet facts during authoring or initialization.

For authored plans that use `precomputed_routing_packets`, the v2 guidance SHALL direct agents to use high-level graph tooling, when available, for:

- identifying non-leaf or delegating participants,
- computing immediate child relationships,
- computing descendant slices needed for authoring packet material,
- deriving root and child packet expectations,
- validating packet coverage before the run enters `ready`.

The v2 guidance SHALL preserve the existing semantic boundary: graph tooling can verify structural packet coverage, but the v2 skill remains responsible for plan semantics, delegation policy, forbidden actions, lifecycle vocabulary, and final readiness decisions.

The v2 guidance SHALL state that graph-tool validation failures are fail-closed authoring or initialization blockers rather than runtime permission for intermediate agents to repair packets from memory.

#### Scenario: Authoring uses graph high packet expectations
- **WHEN** a v2 pairwise authoring agent has a node-link graph for a plan using `precomputed_routing_packets`
- **THEN** the v2 guidance points the agent at `houmao-mgr internals graph high packet-expectations`
- **AND THEN** the guidance still requires the authored packet material to preserve the plan's delegation policy and forbidden actions

#### Scenario: Initialize uses graph high packet validation
- **WHEN** a v2 pairwise run is being initialized with precomputed routing packets
- **THEN** the v2 guidance points the agent at `houmao-mgr internals graph high validate-packets` when graph and packet JSON inputs are available
- **AND THEN** failed validation prevents treating the run as `ready`

#### Scenario: Graph tooling does not replace semantic review
- **WHEN** graph tooling reports that routing-packet coverage is structurally complete
- **THEN** the v2 guidance still requires the agent to ensure that packet content follows the authored plan contract
- **AND THEN** the agent does not treat graph coverage alone as permission to widen delegation, omit forbidden actions, or change result routing
