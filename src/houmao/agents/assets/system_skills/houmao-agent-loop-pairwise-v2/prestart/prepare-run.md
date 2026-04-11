# Initialize A Pairwise Loop Run

Use this page when the user already has one authored pairwise plan and needs the canonical `initialize` action before the master trigger.

Default initialization uses `precomputed_routing_packets`: validate that the root and child packets are ready, then move to `ready` without sending operator-origin participant preparation mail.

Use `operator_preparation_wave` only when the authored plan or user explicitly asks for prestart preparation mail, participant warmup, or acknowledgement-gated readiness.

## Workflow

1. Resolve the canonical plan entrypoint and the target `run_id`.
2. Confirm that the plan already defines:
   - the designated master
   - the participant set
   - the authored topology or descendant relationships
   - the selected `prestart_strategy`
   - routing packet inventory and root packet location when using `precomputed_routing_packets`
   - preparation target policy and acknowledgement posture when using explicit `operator_preparation_wave`
3. Verify the authored topology. If descendant relationships are not clear enough to validate routing packet coverage or explicit preparation-wave targets, return to the authoring or revision lane before continuing.
4. For default `precomputed_routing_packets`, validate the packet set:
   - when a node-link graph and packet JSON document are available, use `houmao-mgr internals graph high validate-packets --graph <graph.json> --packets <packets.json>` as the explicit deterministic structural check before entering `ready`
   - when graph or packet JSON artifacts are unavailable, manually verify visible topology, descendant relationships, packet inventory, child dispatch tables, and freshness markers before entering `ready`
   - one root packet exists for the designated master
   - one child packet exists for every parent-to-child pairwise edge
   - every packet has packet id, intended recipient, immediate driver, and plan revision or digest
   - every non-leaf packet has a child dispatch table and exact child packet text or exact child packet references
   - packet recipients and immediate drivers match the authored topology
5. When packet validation succeeds, enter `ready`. Do not verify or enable mail-notifier behavior solely for preparation mail, and do not send operator-origin standalone preparation mail to participants in this default strategy.
6. For explicit `operator_preparation_wave`, resolve the preparation mail recipient set:
   - by default, include only participants that have descendants in the authored topology, meaning participants expected to delegate jobs to other agents
   - exclude leaf participants by default
   - include leaf participants only when the user explicitly asks to prepare leaf agents, prepare all participants, or names leaf participants in the preparation target set
7. Verify or enable gateway mail-notifier behavior for the targeted preparation recipients through `houmao-agent-gateway` before the run starts.
8. Choose preparation posture for the explicit preparation wave:
   - default `fire_and_proceed`
   - optional `require_ack`
9. Send one standalone preparation email to each targeted recipient through the owned mailbox surfaces:
   - include only that participant's own role, resources, delegation authority, obligations, forbidden actions, and optional timeout-watch policy
   - do not assume the participant already knows which upstream participant may later contact it
   - do not send preparation mail to leaf participants that were not explicitly included in the preparation target set
10. Match operator-origin reply policy to the explicit preparation-wave posture:
   - `fire_and_proceed` -> `reply_policy=none`
   - `require_ack` -> `reply_policy=operator_mailbox`
11. When acknowledgement is required, instruct targeted recipients to reply to `HOUMAO-operator@houmao.localhost` and review those replies through the reserved operator mailbox before the master trigger is sent.
12. Track the observed initialization state explicitly:
   - enter `initializing` when routing packet validation, notifier preflight, or explicit preparation delivery is still in progress
   - enter `awaiting_ack` only when explicit `operator_preparation_wave` uses `require_ack` and required replies from targeted preparation recipients are still outstanding
   - enter `ready` after routing packet validation succeeds for `precomputed_routing_packets`, or after the explicit preparation wave is complete and any required acknowledgements from targeted recipients have arrived
13. Keep `initialize` separate from the master trigger. This page handles `initialize`; it does not itself perform `start`.

## Precomputed Routing Packets

Default initialization validates precomputed routing packets rather than sending preparation mail. The packet set must cover every parent-to-child pairwise edge in the authored topology.

The root packet is for the designated master and must be available to the normalized start charter. Each child packet is for one immediate pairwise edge and must name the intended recipient, immediate driver, plan revision or digest, local role and objective, result-return contract, obligations, forbidden actions, and any child dispatch table.

Drivers later append child packets verbatim to ordinary pairwise edge requests. If a packet is missing, mismatched, or stale, dispatch stops and the mismatch is reported instead of repaired from memory.

When a node-link graph and packet JSON document are available, `houmao-mgr internals graph high validate-packets --graph <graph.json> --packets <packets.json>` is the explicit deterministic structural check for this packet coverage before `ready`. When those artifacts are unavailable, manually verify visible topology, descendant relationships, packet inventory, child dispatch tables, and freshness markers before `ready`. A validation failure is an initialization blocker; do not treat it as permission for runtime participants to repair packets from memory.

## Operator Preparation Wave

Use this strategy only when the plan explicitly selects `operator_preparation_wave`.

Preparation targets are the delegating/non-leaf participants by default: participants that have descendants in the authored topology and are expected to delegate jobs to other agents.

Leaf participants are excluded by default. Include leaf participants only when the user explicitly asks to prepare leaf agents, prepare all participants, or names leaf participants in the preparation target set.

When `require_ack` is active, missing acknowledgements from leaf participants do not block `ready` unless those leaf participants were explicitly included in the preparation target set.

## Preparation Mail Contract

Each preparation mail should make these items easy to find for the targeted recipient:

- `run_id`
- participant identity and role
- local resources or artifacts available to that participant
- allowed delegation targets or allowed delegation set
- delegation-pattern expectations for work categories, when needed
- mailbox, reminder, receipt, or result obligations
- forbidden actions
- reply instructions when acknowledgement is required

## Initialize Contract

- `initialize` is the prestart action, not the master trigger.
- Default `precomputed_routing_packets` initialization validates root and child packet coverage and may move directly from `initializing` to `ready` without sending participant preparation mail.
- Explicit `operator_preparation_wave` initialization may send preparation mail to targeted recipients and may remain in `awaiting_ack` until required replies arrive.
- `ready` means the selected prestart strategy is complete and the operator may proceed to `start`.

## Guardrails

- Do not send operator-origin standalone preparation mail by default.
- Do not send one shared upstream-aware matrix as the only routing artifact.
- Do not ask runtime participants to infer hidden downstream routing shapes; packets must be precomputed.
- Do not ask runtime participants to run graph analysis or recompute descendant slices after `start`; they must use dispatch tables and exact child packets prepared before `ready`.
- Do not guess packet coverage or explicit preparation targets when the topology is unclear; return to authoring or revision first.
- Do not trigger the master before the selected prestart strategy is complete.
- Do not require acknowledgement by default.
- Do not treat `require_ack` as permission to silently widen explicit preparation mail to leaf participants.
