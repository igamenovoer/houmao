# Initialize A Pairwise Loop Run

Use this page when the user already has one authored pairwise plan and needs the canonical `initialize` action before the master trigger.

Default initialization uses `email_initialization`: first turn on gateway email notification for targeted participants with interval `5s` unless the user specified another interval, then send standalone initialization email through the owned mailbox surfaces with `fire_and_proceed` acknowledgement posture.

Use `require_ack` only when the authored plan or user explicitly asks for acknowledgement-gated readiness. Use packet-only initialization only when the plan or user explicitly disables email initialization.

## Workflow

1. Resolve the canonical plan entrypoint and the target `run_id`.
2. Confirm that the plan already defines:
   - the designated master
   - the participant set
   - the authored topology or descendant relationships
   - the selected `prestart_strategy`
   - initialization email target policy
   - gateway mail-notifier interval, defaulting to `5s` unless the user specified otherwise
   - acknowledgement posture, defaulting to `fire_and_proceed` unless `require_ack` is selected explicitly
   - routing packet inventory and root packet location when routing packets are part of the plan
3. Verify the authored topology. If descendant relationships are not clear enough to validate routing packet coverage, return to the authoring or revision lane before continuing.
4. For every targeted participant with a supported live gateway and mailbox binding, verify or enable gateway mail-notifier behavior through `houmao-agent-gateway` before sending initialization mail:
   - use interval `5s` by default
   - use the user-specified or plan-specified interval when one is provided
   - record participants whose notifier setup is unsupported or blocked instead of pretending they are covered
5. Resolve the initialization email recipient set:
   - include every named participant by default, including leaf participants
   - narrow the recipient set only when the user or plan explicitly names a smaller initialization target set
6. When routing packets are part of the plan, validate the packet set as structural preflight:
   - when a node-link graph and packet JSON document are available, use `houmao-mgr internals graph high validate-packets --graph <graph.json> --packets <packets.json>` as the explicit deterministic structural check before entering `ready`
   - when graph or packet JSON artifacts are unavailable, manually verify visible topology, descendant relationships, packet inventory, child dispatch tables, and freshness markers before entering `ready`
   - one root packet exists for the designated master
   - one child packet exists for every parent-to-child pairwise edge
   - every packet has packet id, intended recipient, immediate driver, and plan revision or digest
   - every non-leaf packet has a child dispatch table and exact child packet text or exact child packet references
   - packet recipients and immediate drivers match the authored topology
7. Choose acknowledgement posture:
   - default `fire_and_proceed`
   - optional `require_ack`
8. Send one standalone initialization email to each targeted recipient through the owned mailbox surfaces:
   - include only that participant's own role, resources, delegation authority, obligations, forbidden actions, and optional timeout-watch policy
   - advise the participant to use email/mailbox for job communication by default, including in-loop pairwise edge requests, receipts, and results
   - include the participant's exact routing packet or exact routing packet reference when routing packets are part of the plan
   - do not assume the participant already knows which upstream participant may later contact it
9. Match operator-origin reply policy to the acknowledgement posture:
   - `fire_and_proceed` -> `reply_policy=none`
   - `require_ack` -> `reply_policy=operator_mailbox`
10. When acknowledgement is required, instruct targeted recipients to reply to `HOUMAO-operator@houmao.localhost` and review those replies through the reserved operator mailbox before the master trigger is sent.
11. Track the observed initialization state explicitly:
   - enter `initializing` when routing packet validation, notifier preflight, or initialization email delivery is still in progress
   - enter `awaiting_ack` only when `require_ack` is selected and required replies from targeted initialization recipients are still outstanding
   - enter `ready` after notifier setup and initialization email delivery are complete, routing packet validation succeeds when packets are part of the plan, and any required acknowledgements from targeted recipients have arrived
12. Keep `initialize` separate from the master trigger. This page handles `initialize`; it does not itself perform `start`.

## Routing Packets

Routing packets are optional structural control material for default email initialization. When the plan uses them, the packet set must cover every parent-to-child pairwise edge in the authored topology.

The root packet is for the designated master and must be available to the normalized start charter. Each child packet is for one immediate pairwise edge and must name the intended recipient, immediate driver, plan revision or digest, local role and objective, result-return contract, obligations, forbidden actions, and any child dispatch table.

Drivers later append child packets verbatim to pairwise edge request email. If a packet is missing, mismatched, or stale, dispatch stops and the mismatch is reported instead of repaired from memory.

When a node-link graph and packet JSON document are available, `houmao-mgr internals graph high validate-packets --graph <graph.json> --packets <packets.json>` is the explicit deterministic structural check for this packet coverage before `ready`. When those artifacts are unavailable, manually verify visible topology, descendant relationships, packet inventory, child dispatch tables, and freshness markers before `ready`. A validation failure is an initialization blocker; do not treat it as permission for runtime participants to repair packets from memory.

## Email Initialization

Use this strategy by default unless the plan or user explicitly disables email initialization.

Initialization targets are all named participants by default. Narrow the recipient set only when the user or plan explicitly names a smaller initialization target set.

The operator agent turns on gateway mail-notifier polling first for every targeted participant with a supported live gateway and mailbox binding. Use interval `5s` unless the user or plan specifies another interval.

The acknowledgement posture is `fire_and_proceed` by default. When `require_ack` is active, missing acknowledgements from targeted initialization recipients block `ready` until their replies arrive or the user changes the plan.

## Initialization Mail Contract

Each initialization mail should make these items easy to find for the targeted recipient:

- `run_id`
- participant identity and role
- local resources or artifacts available to that participant
- allowed delegation targets or allowed delegation set
- delegation-pattern expectations for work categories, when needed
- mailbox, reminder, receipt, or result obligations
- default job communication channel: email/mailbox for pairwise edge requests, receipts, and results
- forbidden actions
- reply instructions when acknowledgement is required

## Initialize Contract

- `initialize` is the prestart action, not the master trigger.
- Default `email_initialization` enables gateway mail-notifier polling first, using interval `5s` unless overridden, then sends initialization mail to targeted participants.
- Default acknowledgement posture is `fire_and_proceed`.
- Explicit `require_ack` initialization may remain in `awaiting_ack` until required replies arrive.
- Routing packet validation remains an initialization blocker when routing packets are part of the plan.
- `ready` means the selected prestart strategy is complete and the operator may proceed to `start`.

## Guardrails

- Do not skip gateway mail-notifier enablement before default email initialization unless explicitly disabled or unsupported for a participant.
- Do not use a notifier interval other than `5s` unless the user or plan specifies another interval.
- Do not require acknowledgement by default.
- Do not send one shared upstream-aware matrix as the only routing artifact.
- Do not ask runtime participants to infer hidden downstream routing shapes; packets must be precomputed.
- Do not ask runtime participants to run graph analysis or recompute descendant slices after `start`; they must use dispatch tables and exact child packets prepared before `ready`.
- Do not guess packet coverage or initialization email targets when the topology is unclear; return to authoring or revision first.
- Do not trigger the master before the selected prestart strategy is complete.
- Do not treat `require_ack` as permission to silently widen or narrow the explicit initialization mail target set.
