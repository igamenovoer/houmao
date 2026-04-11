## MODIFIED Requirements

### Requirement: V2 authoring guidance uses internal graph tools for routing-packet validation
The packaged `houmao-agent-loop-pairwise-v2` guidance SHALL treat `houmao-mgr internals graph high` as the first-class deterministic graph helper surface for topology-derived routing-packet facts during authoring and initialization when NetworkX node-link graph and packet JSON artifacts are available.

For authored plans that use the default `precomputed_routing_packets` strategy, the v2 guidance SHALL direct agents to use high-level graph tooling, when available, for:

- identifying root reachability,
- identifying non-leaf or delegating participants,
- identifying leaf participants,
- computing immediate child relationships,
- computing descendant slices needed for authoring packet material,
- deriving root and child packet expectations,
- deriving child dispatch-table expectations for non-leaf recipients,
- validating packet coverage before the run enters `ready`.

The v2 guidance SHALL direct authoring agents to use `houmao-mgr internals graph high analyze` before packet authoring when a node-link graph artifact exists.

The v2 guidance SHALL direct authoring agents to use `houmao-mgr internals graph high slice` for plan-time descendant or subtree inspection when a graph artifact exists and a participant or component slice is easier to review separately.

The v2 guidance SHALL direct authoring agents to use `houmao-mgr internals graph high packet-expectations` to derive root packet, child packet, and non-leaf dispatch-table expectations when a graph artifact exists.

The v2 initialization guidance SHALL direct agents to use `houmao-mgr internals graph high validate-packets` before treating default `precomputed_routing_packets` initialization as `ready` when graph and packet JSON artifacts exist.

When graph or packet JSON artifacts are not available, the v2 guidance SHALL still require explicit visible topology, descendant relationships, packet inventory, child dispatch tables, and freshness markers sufficient to validate packet coverage manually before `ready`.

The v2 guidance SHALL preserve the existing semantic boundary: graph tooling can verify structural packet coverage, but the v2 skill remains responsible for plan semantics, delegation policy, forbidden actions, lifecycle vocabulary, result-return contracts, and final readiness decisions.

The v2 guidance SHALL state that graph-tool validation failures are fail-closed authoring or initialization blockers rather than runtime permission for intermediate agents to repair packets from memory.

The v2 runtime handoff guidance SHALL state that intermediate agents use precomputed dispatch tables and exact child packet text or exact packet references rather than running graph analysis or recomputing descendant plan slices during handoff.

#### Scenario: Authoring uses graph high packet expectations
- **WHEN** a v2 pairwise authoring agent has a node-link graph for a plan using `precomputed_routing_packets`
- **THEN** the v2 guidance points the agent at `houmao-mgr internals graph high analyze` and `houmao-mgr internals graph high packet-expectations`
- **AND THEN** the guidance still requires the authored packet material to preserve the plan's delegation policy and forbidden actions

#### Scenario: Initialize uses graph high packet validation
- **WHEN** a v2 pairwise run is being initialized with precomputed routing packets and graph plus packet JSON artifacts are available
- **THEN** the v2 guidance points the agent at `houmao-mgr internals graph high validate-packets`
- **AND THEN** failed validation prevents treating the run as `ready`

#### Scenario: Intermediate handoff avoids graph recomputation
- **WHEN** a non-leaf participant in a v2 run delegates to a child after `start`
- **THEN** the v2 guidance tells the participant to use its dispatch table and append the exact prepared child packet text or exact packet reference
- **AND THEN** the participant does not recompute descendants or repair missing packets by graph reasoning from memory

#### Scenario: Graph tooling does not replace semantic review
- **WHEN** graph tooling reports that routing-packet coverage is structurally complete
- **THEN** the v2 guidance still requires the agent to ensure that packet content follows the authored plan contract
- **AND THEN** the agent does not treat graph coverage alone as permission to widen delegation, omit forbidden actions, or change result routing
