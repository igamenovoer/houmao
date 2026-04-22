# Initialize A Pairwise Loop Run

Use this page when the user already has one authored pairwise-v3 plan and needs the canonical `initialize` action before the master trigger.

## Summary

Default `initialize` uses `precomputed_routing_packets`:
- validate routing-packet coverage
- write run-owned memo blocks directly through `houmao-memory-mgr`
- make those memo blocks the canonical participant-facing prestart contract

Use `operator_preparation_wave` only when the plan or user explicitly asks for participant warmup, standalone preparation mail, or acknowledgement-gated readiness.

When `operator_preparation_wave` is selected, enabling or verifying gateway mail-notifier behavior for each targeted participant is a required initialize gate before any preparation mail is sent.

## Inputs

Before starting, confirm the plan defines:
- designated master
- participant set
- optional launch-profile references for participants that `initialize` may need to launch
- workspace contract
- authored topology or descendant relationships
- selected `prestart_strategy`
- exact memo sentinel convention keyed by `run_id` and slot
- initialize memo-slot expectations when managed memory is being used
- explicit `operator_preparation_wave` target policy and gateway mail-notifier interval when that strategy is selected
- acknowledgement posture, defaulting to `fire_and_proceed` unless `require_ack` is selected explicitly
- routing packet inventory and root packet location when routing packets are part of the plan
- email/mailbox-capable designated master and participant set

## Workflow

1. Resolve the canonical plan entrypoint and the target `run_id`.
2. Verify the authored topology. If descendant relationships are not clear enough to validate routing packet coverage, return to the authoring or revision lane before continuing.
3. When routing packets are part of the plan, validate the packet set as structural preflight:
   - when a node-link graph and packet JSON document are available, use `houmao-mgr internals graph high validate-packets --graph <graph.json> --packets <packets.json>` as the explicit deterministic structural check before entering `ready`
   - when graph or packet JSON artifacts are unavailable, manually verify visible topology, descendant relationships, packet inventory, child dispatch tables, and freshness markers before entering `ready`
   - one root packet exists for the designated master
   - one child packet exists for every parent-to-child pairwise edge
   - every packet has packet id, intended recipient, immediate driver, and plan revision or digest
   - every non-leaf packet has a child dispatch table and exact child packet text or exact child packet references
   - packet recipients and immediate drivers match the authored topology
4. Resolve the authored workspace contract before participant materialization:
   - when mode is `standard`, record the selected standard posture and any required values such as `task-name`
   - when mode is `custom`, record the explicit operator-owned paths and rules directly from the plan
   - keep runtime-owned recovery files outside this workspace contract
5. Launch missing participants when the plan provides launch profiles for them:
   - for each required participant that is not yet live, inspect the provided launch profile's mailbox association first
   - if the launch profile does not declare the mailbox association needed for the run's default email/mailbox communication posture, fail clearly before launching
   - for each required participant that is not yet live and whose launch profile passed that precheck, use the provided launch profile through the supported managed-agent launch skill
   - do not invent a launch profile when the plan does not provide one
   - if a required participant is still missing after this step, fail clearly instead of proceeding
6. Verify that the designated master and every required participant have email/mailbox support before continuing:
   - use the supported Houmao email or mailbox inspection surfaces to confirm that each required participant can participate in the run's default email/mailbox communication posture
   - if any required participant lacks that support, fail clearly and do not enter `ready`
7. For every targeted participant whose managed memory is being used, write or replace one run-owned memo block through `houmao-memory-mgr`:
   - use one exact begin sentinel and one exact end sentinel keyed by `run_id` and slot `initialize`
   - include local role, local objective, allowed delegation targets or allowed delegation set, task-handling rules, obligations, forbidden actions, mailbox and result-return expectations, and any routing-packet or child-dispatch references that the participant must keep easy to reopen
   - include the participant's declared workspace posture, writable source surfaces, shared writable surfaces, and bookkeeping paths
   - include the participant's exact routing packet or exact routing packet reference when routing packets are part of the plan
   - for the designated master, include the organization rules, participant set, completion posture, stop posture, and the routing or dispatch guidance needed to supervise the run
8. Replacement rules for that memo block:
   - replace only the bounded block when exactly one matching begin/end pair exists
   - append one new bounded block when no matching begin/end pair exists
   - fail closed and report a conflict when more than one matching begin/end pair exists
9. If the selected strategy is explicit `operator_preparation_wave`, resolve the preparation-mail recipient set:
   - target delegating or non-leaf participants by default
   - include leaf participants only when the user explicitly asks to prepare leaf agents, prepare all participants, or names those leaf participants in the target set
10. Treat notifier setup as a hard pre-mail gate for explicit `operator_preparation_wave`.
11. For every targeted `operator_preparation_wave` participant with a supported live gateway and mailbox binding, verify or enable gateway mail-notifier behavior through `houmao-agent-gateway` before sending preparation mail:
   - use interval `5s` by default
   - use the user-specified or plan-specified interval when one is provided
   - record participants whose notifier setup is unsupported or blocked instead of pretending they are covered
12. Choose acknowledgement posture for `operator_preparation_wave`:
   - default `fire_and_proceed`
   - optional `require_ack`
13. When `operator_preparation_wave` is selected, send one standalone preparation email to each targeted recipient only after the notifier gate above is satisfied for the supported participants and any unsupported or blocked cases are reported explicitly:
   - point the participant at its run-owned initialize memo block and exact routing packet or exact routing packet reference rather than making the mail the only copy of the run guidance
   - advise the participant to use email/mailbox for job communication by default, including in-loop pairwise edge requests, receipts, and results
   - do not assume the participant already knows which upstream participant may later contact it
14. Match operator-origin reply policy to the acknowledgement posture:
   - `fire_and_proceed` -> `reply_policy=none`
   - `require_ack` -> `reply_policy=operator_mailbox`
15. When acknowledgement is required, instruct targeted recipients to reply to `HOUMAO-operator@houmao.localhost` and review those replies through the reserved operator mailbox before the master trigger is sent.
16. Track the observed initialization state explicitly:
   - enter `initializing` when routing-packet validation, launch-profile-backed participant launch, email/mailbox verification, initialize memo materialization, or explicit `operator_preparation_wave` notifier or mail work is still in progress
   - enter `awaiting_ack` only when explicit `operator_preparation_wave` selected `require_ack` and required replies from targeted preparation recipients are still outstanding
   - enter `ready` after the selected prestart strategy is complete
17. Keep `initialize` separate from the master trigger. This page handles `initialize`; it does not itself perform `start`.

## Routing Packets

Routing packets are the default structural control material for pairwise-v3 initialization.

- The root packet is for the designated master and must be available to the designated master's initialize memo block.
- Each child packet is for one immediate pairwise edge and must name the intended recipient, immediate driver, plan revision or digest, local role and objective, result-return contract, obligations, forbidden actions, and any child dispatch table.
- Drivers later append child packets verbatim to pairwise edge request email.
- If a packet is missing, mismatched, or stale, dispatch stops and the mismatch is reported instead of repaired from memory.

When a node-link graph and packet JSON document are available, `houmao-mgr internals graph high validate-packets --graph <graph.json> --packets <packets.json>` is the explicit deterministic structural check before `ready`. A validation failure is an initialization blocker; do not treat it as permission for runtime participants to repair packets from memory.

## Initialize Memo Material

Use run-owned memo blocks as the default initialize material for participants whose managed memory is being used.

- memo slot: `initialize`
- memo block: the canonical participant-facing initialize contract
- memo work: route through `houmao-memory-mgr`

When the user asks about the agent memo itself, the `houmao-memo.md` file, or memo-linked managed-memory pages while running `initialize`, treat that as a `houmao-memory-mgr` task rather than a standalone pairwise-v3 editing surface.

## Memo Block Contract

Use exact sentinels keyed by `run_id` and slot `initialize`.

```md
<!-- HOUMAO_PAIRWISE_V3_BEGIN run_id=<run_id> slot=initialize -->
## Pairwise-V3 Run Initialization

- run: `<run_id>`
- role: <master | participant role>
- objective: <local objective>
- workspace: <relevant workspace and bookkeeping posture>
- routing: <exact packet or packet reference>
- note: this memo block is the durable initialize guidance for this participant
<!-- HOUMAO_PAIRWISE_V3_END run_id=<run_id> slot=initialize -->
```

Replacement rules:
- replace only the text bounded by the exact matching begin/end pair
- append one new bounded block when no matching begin/end pair exists
- fail closed and report a conflict when more than one matching begin/end pair exists
- do not infer replacement boundaries from headings, nearby prose, or fuzzy text matches

## Operator Preparation Wave

Use this strategy only when the plan or user explicitly selects `operator_preparation_wave`.

- Preparation-mail targets are delegating or non-leaf participants by default.
- The acknowledgement posture is `fire_and_proceed` by default.
- When `require_ack` is active, missing acknowledgements block `ready`.
- Verifying or enabling gateway mail-notifier behavior for supported targets happens before any preparation mail is sent.
- Each standalone preparation mail should point at the participant's initialize memo block and exact routing packet or exact packet reference when routing packets are part of the plan.

## Workspace Contract

Use the authored workspace contract as part of initialize guidance:

- `standard` mode records the selected Houmao-standard posture, such as task-scoped in-repo or standard out-of-repo.
- `custom` mode records explicit operator-owned paths and rules directly in the plan.
- Bookkeeping paths come from the authored contract; do not invent a fixed per-agent `kb/` subtree.
- Runtime-owned recovery files remain outside the authored workspace contract even when participants inspect leftover workspace state during recovery.

## Initialize Contract

- `initialize` is the prestart action, not the master trigger.
- Default `precomputed_routing_packets` validates routing packets first, launches missing participants from provided launch profiles when needed, and then writes run-owned initialize memo blocks for participants whose managed memory is being used.
- Standalone preparation mail belongs only to explicit `operator_preparation_wave`.
- Default acknowledgement posture is `fire_and_proceed`; explicit `require_ack` may remain in `awaiting_ack` until required replies arrive.
- Missing required participants without provided launch profiles are an initialization blocker.
- Missing email/mailbox support for any required participant is an initialization blocker.
- Routing packet validation remains an initialization blocker when routing packets are part of the plan.
- `ready` means the selected prestart strategy is complete and the operator may proceed to `start`.

## Guardrails

- Do not treat standalone participant preparation mail as the default initialize path.
- Do not treat gateway mail-notifier setup as optional when explicit `operator_preparation_wave` is selected.
- Do not send `operator_preparation_wave` preparation mail before notifier setup has been checked through `houmao-agent-gateway` for each targeted participant with supported live gateway and mailbox surfaces.
- Do not invent launch profiles for missing participants during `initialize`.
- Do not skip the run-owned initialize memo block for participants whose managed memory is being used.
- Do not proceed toward `ready` when a required participant is still missing after the launch-profile-backed launch step.
- Do not proceed toward `ready` when the designated master or any required participant lacks email/mailbox support.
- Do not rewrite runtime-owned recovery files as ordinary workspace or bookkeeping paths.
- Do not infer memo replacement boundaries from headings or nearby prose; use exact begin/end sentinels keyed by `run_id` and slot.
- Do not use a notifier interval other than `5s` for explicit `operator_preparation_wave` unless the user or plan specifies another interval.
- Do not require acknowledgement by default.
- Do not send one shared upstream-aware matrix as the only routing artifact.
- Do not ask runtime participants to infer hidden downstream routing shapes; packets must be precomputed.
- Do not ask runtime participants to run graph analysis or recompute descendant slices after `start`; they must use dispatch tables and exact child packets prepared before `ready`.
- Do not guess packet coverage, initialize memo-slot expectations, or explicit preparation-wave targets when the topology is unclear; return to authoring or revision first.
- Do not trigger the master before the selected prestart strategy is complete.
- Do not treat `require_ack` as permission to silently widen or narrow the explicit `operator_preparation_wave` target set.
