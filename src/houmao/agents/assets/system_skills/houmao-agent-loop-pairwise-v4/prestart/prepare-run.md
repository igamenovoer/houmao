# Initialize A Tree Loop Run

Use this page when the user already has one authored pairwise-v4 plan and needs the canonical `initialize` action before the master trigger.

## Summary

Default `initialize` uses `precomputed_routing_packets`:
- validate routing-packet coverage
- verify or enable gateway mail-notifier behavior for required mail-driven participants
- write run-owned memo blocks directly through `houmao-memory-mgr`
- make those memo blocks the canonical participant-facing prestart contract

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
- gateway mail-notifier interval, defaulting to `5s`
- routing packet inventory and root packet location when routing packets are part of the plan
- email/mailbox-capable designated master and participant set

## Workflow

1. Resolve the canonical plan entrypoint and the target `run_id`.
2. Verify the authored topology. If descendant relationships are not clear enough to validate routing packet coverage, return to the authoring or revision lane before continuing.
3. When routing packets are part of the plan, validate the packet set as structural preflight:
   - when a node-link graph and packet JSON document are available, use `houmao-mgr internals graph high validate-packets --graph <graph.json> --packets <packets.json>` as the explicit deterministic structural check before entering `ready`
   - when graph or packet JSON artifacts are unavailable, manually verify visible topology, descendant relationships, packet inventory, child dispatch tables, and freshness markers before entering `ready`
   - one root packet exists for the designated master
   - one child packet exists for every parent-to-child local-close edge
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
7. Verify or enable gateway mail-notifier behavior for every required participant with supported live gateway and mailbox binding:
   - use interval `5s` by default
   - use the user-specified or plan-specified interval when one is provided
   - record participants whose notifier setup is unsupported or blocked instead of pretending they are covered
   - if the plan depends on automatic mailbox wakeups for a participant and notifier setup is blocked, fail clearly and do not enter `ready`
8. For every targeted participant whose managed memory is being used, write or replace one run-owned memo block through `houmao-memory-mgr`:
   - use one exact begin sentinel and one exact end sentinel keyed by `run_id` and slot `initialize`
   - include local role, local objective, allowed delegation targets or allowed delegation set, task-handling rules, obligations, forbidden actions, mailbox and result-return expectations, and any routing-packet or child-dispatch references that the participant must keep easy to reopen
   - include the participant's declared workspace posture, writable source surfaces, shared writable surfaces, and bookkeeping paths
   - include the participant's exact routing packet or exact routing packet reference when routing packets are part of the plan
   - for the designated master, include the organization rules, participant set, completion posture, stop posture, and the routing or dispatch guidance needed to supervise the run
9. Replacement rules for that memo block:
   - replace only the bounded block when exactly one matching begin/end pair exists
   - append one new bounded block when no matching begin/end pair exists
   - fail closed and report a conflict when more than one matching begin/end pair exists
10. Track the observed initialization state explicitly:
   - enter `initializing` when routing-packet validation, launch-profile-backed participant launch, email/mailbox verification, notifier setup, or initialize memo materialization is still in progress
   - enter `ready` after routing-packet validation, required participant launch, email/mailbox verification, notifier setup, and memo materialization are complete
11. Keep `initialize` separate from the master trigger. This page handles `initialize`; it does not itself perform `start`.

## Routing Packets

Routing packets are the default structural control material for pairwise-v4 initialization.

- The root packet is for the designated master and must be available to the designated master's initialize memo block.
- Each child packet is for one immediate local-close edge and must name the intended recipient, immediate driver, plan revision or digest, local role and objective, result-return contract, obligations, forbidden actions, and any child dispatch table.
- Drivers later append child packets verbatim to local-close edge request email.
- If a packet is missing, mismatched, or stale, dispatch stops and the mismatch is reported instead of repaired from memory.

When a node-link graph and packet JSON document are available, `houmao-mgr internals graph high validate-packets --graph <graph.json> --packets <packets.json>` is the explicit deterministic structural check before `ready`. A validation failure is an initialization blocker; do not treat it as permission for runtime participants to repair packets from memory.

## Initialize Memo Material

Use run-owned memo blocks as the default initialize material for participants whose managed memory is being used.

- memo slot: `initialize`
- memo block: the canonical participant-facing initialize contract
- memo work: route through `houmao-memory-mgr`

When the user asks about the agent memo itself, the `houmao-memo.md` file, or memo-linked managed-memory pages while running `initialize`, treat that as a `houmao-memory-mgr` task rather than a standalone pairwise-v4 editing surface.

## Memo Block Contract

Use exact sentinels keyed by `run_id` and slot `initialize`.

```md
<!-- HOUMAO_PAIRWISE_V4_BEGIN run_id=<run_id> slot=initialize -->
## Pairwise-V4 Run Initialization

- run: `<run_id>`
- role: <master | participant role>
- objective: <local objective>
- workspace: <relevant workspace and bookkeeping posture>
- routing: <exact packet or packet reference>
- note: this memo block is the durable initialize guidance for this participant
<!-- HOUMAO_PAIRWISE_V4_END run_id=<run_id> slot=initialize -->
```

Replacement rules:
- replace only the text bounded by the exact matching begin/end pair
- append one new bounded block when no matching begin/end pair exists
- fail closed and report a conflict when more than one matching begin/end pair exists
- do not infer replacement boundaries from headings, nearby prose, or fuzzy text matches

## Workspace Contract

Use the authored workspace contract as part of initialize guidance:

- `standard` mode records the selected Houmao-standard posture, such as task-scoped in-repo or standard out-of-repo.
- `custom` mode records explicit operator-owned paths and rules directly in the plan.
- Bookkeeping paths come from the authored contract; do not invent a fixed per-agent `kb/` subtree.
- Runtime-owned recovery files remain outside the authored workspace contract even when participants inspect leftover workspace state during recovery.

## Initialize Contract

- `initialize` is the prestart action, not the master trigger.
- Default `precomputed_routing_packets` validates routing packets first, launches missing participants from provided launch profiles when needed, verifies or enables notifier posture for required mail-driven participants, and then writes run-owned initialize memo blocks for participants whose managed memory is being used.
- Standalone preparation mail is not part of pairwise-v4 initialize.
- Missing required participants without provided launch profiles are an initialization blocker.
- Missing email/mailbox support for any required participant is an initialization blocker.
- Routing packet validation remains an initialization blocker when routing packets are part of the plan.
- `ready` means routing-packet validation, required participant launch, email/mailbox verification, notifier setup, and memo materialization are complete and the operator may proceed to `start`.

## Guardrails

- Do not treat standalone participant preparation mail as the default initialize path.
- Do not send standalone participant preparation mail during pairwise-v4 `initialize`.
- Do not treat gateway mail-notifier setup as optional for required mail-driven participants with supported live gateway and mailbox surfaces.
- Do not invent launch profiles for missing participants during `initialize`.
- Do not skip the run-owned initialize memo block for participants whose managed memory is being used.
- Do not proceed toward `ready` when a required participant is still missing after the launch-profile-backed launch step.
- Do not proceed toward `ready` when the designated master or any required participant lacks email/mailbox support.
- Do not rewrite runtime-owned recovery files as ordinary workspace or bookkeeping paths.
- Do not infer memo replacement boundaries from headings or nearby prose; use exact begin/end sentinels keyed by `run_id` and slot.
- Do not require acknowledgement by default.
- Do not send one shared upstream-aware matrix as the only routing artifact.
- Do not ask runtime participants to infer hidden downstream routing shapes; packets must be precomputed.
- Do not ask runtime participants to run graph analysis or recompute descendant slices after `start`; they must use dispatch tables and exact child packets prepared before `ready`.
- Do not guess packet coverage or initialize memo-slot expectations when the topology is unclear; return to authoring or revision first.
- Do not trigger the master before the selected prestart strategy is complete.
