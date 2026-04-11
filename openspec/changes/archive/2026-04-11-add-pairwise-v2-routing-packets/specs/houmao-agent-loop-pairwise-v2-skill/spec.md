## RENAMED Requirements

### Requirement: V2 initialize targets delegating participants by default
FROM: `V2 initialize targets delegating participants by default`
TO: `V2 defaults to precomputed routing packets for participant preparation`

## MODIFIED Requirements

### Requirement: V2 defaults to precomputed routing packets for participant preparation
The packaged `houmao-agent-loop-pairwise-v2` prestart guidance SHALL distinguish the selected preparation strategy from participant routing material.

The v2 authoring guidance SHALL define `precomputed_routing_packets` as the default preparation strategy for authored pairwise loop plans.

The v2 authoring guidance SHALL retain `operator_preparation_wave` as an explicit preparation strategy when the user asks for prestart preparation mail, participant warmup, or acknowledgement-gated readiness.

For the default `precomputed_routing_packets` strategy, the v2 authoring guidance SHALL precompute subtree slices during plan authoring or revision rather than requiring intermediate runtime agents to derive descendant plan slices.

For the default `precomputed_routing_packets` strategy, the authored plan SHALL contain one root routing packet for the designated master and one child routing packet for each parent-to-child pairwise edge in the authored topology.

Each routing packet SHALL identify at minimum:

- packet id,
- run id or run id placeholder,
- plan id plus plan revision, digest, or equivalent freshness marker,
- intended recipient,
- immediate driver,
- local role and local objective,
- allowed delegation targets,
- child dispatch table when the recipient has descendants,
- exact child packet text or exact references to child packet text when the recipient has descendants,
- result-return contract back to the immediate driver,
- mailbox, receipt, result, reminder, or timeout-watch obligations,
- forbidden actions.

For the default `precomputed_routing_packets` strategy, the v2 `initialize` guidance SHALL validate that the routing packet set covers the authored topology, that each non-leaf participant packet has a child dispatch table, and that the root routing packet is available to the start charter.

For the default `precomputed_routing_packets` strategy, the v2 `initialize` guidance SHALL NOT send operator-origin standalone preparation mail to participants.

For the default `precomputed_routing_packets` strategy, the v2 `initialize` guidance SHALL define `ready` as requiring successful routing-packet validation rather than preparation-mail delivery or participant acknowledgements.

For the default `precomputed_routing_packets` strategy, the v2 `start` guidance SHALL include the root routing packet, or an exact root packet reference, in the normalized start charter delivered to the designated master.

The v2 runtime handoff guidance SHALL direct any driver that delegates to a child to append the exact child routing packet for that child to the ordinary pairwise edge request.

The v2 runtime handoff guidance SHALL direct intermediate agents to use their dispatch tables and prepared child packets instead of recomputing graph topology or descendant plan slices at runtime.

The v2 runtime handoff guidance SHALL forbid agents from editing, merging, or summarizing child routing packets unless the authored plan explicitly permits that transformation.

When a child packet is missing, the packet intended recipient does not match the actual child, or the packet freshness marker does not match the active plan, the v2 runtime handoff guidance SHALL require the driver to stop that downstream dispatch and report the mismatch to its immediate driver or, for the master, to the operator.

For the explicit `operator_preparation_wave` strategy, the v2 `initialize` guidance SHALL preserve the targeted preparation behavior: preparation mail targets delegating/non-leaf participants by default, leaf participants are included only when the user explicitly asks to prepare leaf agents, prepare all participants, or names leaf participants in the preparation target set, and `require_ack` applies to the actual preparation mail recipient set.

The v2 `initialize` and `start` guidance SHALL define `ready` as requiring completion of the selected prestart strategy:

- routing-packet validation for `precomputed_routing_packets`,
- targeted preparation-wave completion plus any required acknowledgements for `operator_preparation_wave`.

#### Scenario: Default initialize validates routing packets without preparation mail
- **WHEN** a user invokes `houmao-agent-loop-pairwise-v2` and asks to initialize an authored plan that uses the default preparation strategy
- **THEN** the v2 preparation guidance validates that the root and child routing packets cover the authored topology
- **AND THEN** it does not send operator-origin standalone preparation mail to delegating or leaf participants

#### Scenario: Start gives the master the root routing packet
- **WHEN** a v2 pairwise run using `precomputed_routing_packets` moves from `ready` to `start`
- **THEN** the normalized start charter gives the designated master the root routing packet or an exact root packet reference
- **AND THEN** the master can begin dispatch without relying on a prior operator-origin preparation message

#### Scenario: Intermediate agent forwards a prepared child packet
- **WHEN** a non-leaf participant receives a routing packet with a child dispatch table and later delegates to one of those children
- **THEN** the participant appends the exact prepared child routing packet to the ordinary pairwise edge request for that child
- **AND THEN** it does not recompute the descendant subtree from the full plan

#### Scenario: Packet mismatch fails closed
- **WHEN** a driver is about to delegate to a child but the child packet is missing, names a different intended recipient, or carries a stale plan revision or digest
- **THEN** the driver stops that downstream dispatch and reports the mismatch to its immediate driver or to the operator when the driver is the master
- **AND THEN** it does not repair the packet by graph reasoning from memory

#### Scenario: Explicit operator preparation wave preserves targeted recipient behavior
- **WHEN** a user explicitly selects `operator_preparation_wave` or asks for acknowledgement-gated preparation before the master trigger
- **THEN** the v2 preparation guidance targets preparation mail to delegating/non-leaf participants by default
- **AND THEN** leaf participants are included only when the user explicitly asks to prepare leaf agents, prepare all participants, or names leaf participants in the preparation target set

#### Scenario: Ready state follows the selected prestart strategy
- **WHEN** a v2 pairwise run uses `precomputed_routing_packets`
- **THEN** the run enters `ready` after routing-packet validation succeeds
- **AND THEN** it does not wait for participant acknowledgements unless the selected strategy is `operator_preparation_wave` with `require_ack`
