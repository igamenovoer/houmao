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

For the default `precomputed_routing_packets` strategy, the v2 `initialize` guidance SHALL materialize durable participant-facing initialize guidance in managed memory for each targeted participant that exposes managed memory, using a dedicated page plus a run-owned memo reference block rather than relying on standalone operator-origin preparation mail as the primary carrier.

For the default `precomputed_routing_packets` strategy, the v2 `initialize` guidance SHALL NOT send operator-origin standalone preparation mail to participants.

For the default `precomputed_routing_packets` strategy, the v2 `initialize` guidance SHALL define `ready` as requiring successful routing-packet validation and completion of the required durable initialize materialization for participants whose managed memory is being used, rather than preparation-mail delivery or participant acknowledgements.

For the default `precomputed_routing_packets` strategy, the v2 `start` guidance SHALL materialize the master-facing charter in durable managed memory before sending the live start trigger to the designated master.

For the default `precomputed_routing_packets` strategy, the v2 `start` guidance SHALL send a compact control-plane trigger that points at that durable charter page rather than using the live trigger as the only copy of the full charter.

The v2 runtime handoff guidance SHALL direct any driver that delegates to a child to append the exact child routing packet for that child to the ordinary pairwise edge request.

The v2 runtime handoff guidance SHALL direct intermediate agents to use their dispatch tables and prepared child packets instead of recomputing graph topology or descendant plan slices at runtime.

The v2 runtime handoff guidance SHALL forbid agents from editing, merging, or summarizing child routing packets unless the authored plan explicitly permits that transformation.

When a child packet is missing, the packet intended recipient does not match the actual child, or the packet freshness marker does not match the active plan, the v2 runtime handoff guidance SHALL require the driver to stop that downstream dispatch and report the mismatch to its immediate driver or, for the master, to the operator.

For the explicit `operator_preparation_wave` strategy, the v2 `initialize` guidance SHALL preserve the targeted preparation behavior: preparation mail targets delegating/non-leaf participants by default, leaf participants are included only when the user explicitly asks to prepare leaf agents, prepare all participants, or names leaf participants in the preparation target set, and `require_ack` applies to the actual preparation mail recipient set.

The v2 `initialize` and `start` guidance SHALL define `ready` as requiring completion of the selected prestart strategy:

- routing-packet validation plus required durable initialize materialization for `precomputed_routing_packets`,
- targeted preparation-wave completion plus any required acknowledgements for `operator_preparation_wave`.

#### Scenario: Default initialize validates routing packets and writes durable participant guidance without preparation mail
- **WHEN** a user invokes `houmao-agent-loop-pairwise-v2` and asks to initialize an authored plan that uses the default preparation strategy
- **THEN** the v2 preparation guidance validates that the root and child routing packets cover the authored topology
- **AND THEN** it writes or refreshes participant initialize pages and run-owned memo reference blocks for participants whose managed memory is being used
- **AND THEN** it does not send operator-origin standalone preparation mail to delegating or leaf participants

#### Scenario: Start gives the master a durable charter before the live trigger
- **WHEN** a v2 pairwise run using `precomputed_routing_packets` moves from `ready` to `start`
- **THEN** the guidance materializes the designated master's charter page in managed memory before the live start trigger is sent
- **AND THEN** the compact start trigger points at that durable charter page instead of acting as the only copy of the charter

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
- **THEN** the run enters `ready` after routing-packet validation succeeds and the required durable initialize materialization is complete for the participants whose managed memory is being used
- **AND THEN** it does not wait for participant acknowledgements unless the selected strategy is `operator_preparation_wave` with `require_ack`

### Requirement: Pairwise-v2 initialization treats memo links as authored content
The packaged `houmao-agent-loop-pairwise-v2` initialization guidance SHALL use each targeted live participant's `houmao-memo.md` file for per-agent initialization memory when the participant exposes managed memory.

The durable initialize material SHALL live primarily in a dedicated page under `HOUMAO_AGENT_PAGES_DIR`, scoped to the run and participant-facing initialize slot, rather than as a large inline memo body.

The initialize page SHALL include the participant's local role, local objective, allowed delegation targets or delegation set, task-handling rules, obligations, forbidden actions, mailbox and result-return expectations, and any routing-packet or child-dispatch references that the participant must keep easy to reopen across turns.

The v2 guidance SHALL direct initialization to write or replace the initialize page through the supported memory page operation when available, using `HOUMAO_AGENT_PAGES_DIR` as the in-agent pointer and the gateway or pair-server memory page endpoint as the operator-side entrypoint.

The v2 guidance SHALL direct initialization to write or replace a compact run-owned memo reference block through the supported memory memo operation when available, using `HOUMAO_AGENT_MEMO_FILE` as the in-agent pointer and the gateway or pair-server memory memo endpoint as the operator-side entrypoint.

The memo reference block SHALL point at the initialize page through an explicit authored memo link such as `pages/<relative-page>`.

The v2 guidance SHALL treat memo links to pages and the surrounding run-owned reference block as caller-authored Markdown content rather than generated index entries or global managed metadata.

#### Scenario: Initialization writes one participant initialize page and memo reference
- **WHEN** `houmao-agent-loop-pairwise-v2` initializes participant `worker-a`
- **AND WHEN** `worker-a` exposes managed memo file `/repo/.houmao/memory/agents/worker-a-id/houmao-memo.md`
- **AND WHEN** `worker-a` exposes managed pages directory `/repo/.houmao/memory/agents/worker-a-id/pages`
- **THEN** initialization records `worker-a`'s role, objective, delegation authority, obligations, forbidden actions, and result-return expectations in a dedicated initialize page
- **AND THEN** it writes or refreshes a memo reference block that links to that page

#### Scenario: Initialization update uses supported memory surfaces
- **WHEN** the operator-side initialize action needs to update a live participant's durable initialize material
- **AND WHEN** the participant has a live gateway or pair-server memory proxy
- **THEN** the v2 guidance uses the supported page and memo endpoints or CLI operations
- **AND THEN** it does not ask the participant to infer the initialization rules from prior email alone

#### Scenario: Initialize memo link remains authored content
- **WHEN** pairwise-v2 writes a memo reference block that links to `pages/loop-runs/pairwise-v2/run-1/initialize.md`
- **THEN** that link remains ordinary memo text owned by the caller
- **AND THEN** the guidance does not treat it as a Houmao-generated page index entry

## ADDED Requirements

### Requirement: Pairwise-v2 start materializes a durable master charter page
The packaged `houmao-agent-loop-pairwise-v2` start guidance SHALL materialize the master-facing charter in managed memory when the designated master exposes managed memory.

The durable start material SHALL live primarily in a dedicated page under `HOUMAO_AGENT_PAGES_DIR`, scoped to the run and `start-charter` slot.

The start-charter page SHALL include at minimum:

- `run_id`,
- plan reference,
- designated master identity,
- allowed participants,
- delegation policy summary,
- prestart strategy summary,
- routing packet validation summary,
- root routing packet or exact root packet reference when routing packets are part of the plan,
- completion condition summary,
- default stop mode,
- reporting contract summary with canonical observed states,
- the statement that the operator is outside the execution loop.

The v2 guidance SHALL direct `start` to write or replace the start-charter page through the supported memory page operation when available.

The v2 guidance SHALL direct `start` to write or replace a compact run-owned memo reference block that links to the start-charter page through the supported memory memo operation when available.

The live start trigger SHALL remain a control-plane message that points at the durable start-charter page and requires an explicit `accepted` or `rejected` master response.

#### Scenario: Start writes a master charter page before dispatch
- **WHEN** `houmao-agent-loop-pairwise-v2` starts run `run-1`
- **AND WHEN** the designated master exposes managed memory
- **THEN** the guidance writes or refreshes `run-1`'s start-charter page before the live trigger is sent
- **AND THEN** it also refreshes the matching memo reference block that links to that page

#### Scenario: Start trigger stays compact
- **WHEN** the durable start-charter page has already been written for run `run-1`
- **THEN** the live start action sends a compact control-plane trigger that points at the page
- **AND THEN** the live trigger is not the only copy of the full charter

### Requirement: Pairwise-v2 memo reference block replacement uses exact sentinels
The packaged `houmao-agent-loop-pairwise-v2` guidance SHALL define one exact begin sentinel and one exact end sentinel for each run-owned memo reference block.

Each sentinel pair SHALL be keyed by the pairwise-v2 `run_id` and the slot name, such as `initialize` or `start-charter`.

When updating durable pairwise-v2 memo material for a given run-owned slot, the guidance SHALL replace only the content bounded by the exact matching sentinel pair, or append one new bounded block when no matching block exists.

The guidance SHALL fail closed when more than one matching bounded block exists for the same `run_id` and slot.

The guidance SHALL NOT infer replacement boundaries from headings, nearby prose, or fuzzy text matches.

#### Scenario: Existing initialize block is replaced by exact sentinel match
- **WHEN** `houmao-memo.md` already contains one bounded pairwise-v2 block for `run-1` and slot `initialize`
- **THEN** a later initialize refresh replaces only that bounded block
- **AND THEN** unrelated memo text outside the sentinels remains unchanged

#### Scenario: Missing block is appended
- **WHEN** `houmao-memo.md` does not yet contain a bounded pairwise-v2 block for `run-1` and slot `start-charter`
- **THEN** the guidance appends one new bounded block for that slot
- **AND THEN** it does not guess a replacement boundary from surrounding headings or prose

#### Scenario: Duplicate blocks fail closed
- **WHEN** `houmao-memo.md` contains more than one bounded pairwise-v2 block for the same `run_id` and slot
- **THEN** the guidance reports a conflict instead of editing the memo
- **AND THEN** it does not guess which block to replace

### Requirement: Pairwise-v2 plan authoring uses a user-selected output directory
The packaged `houmao-agent-loop-pairwise-v2` authoring guidance SHALL require one user-selected output directory before it writes a generated or revised plan to disk.

When the authoring request does not already identify that directory, the guidance SHALL ask the user for it rather than inventing a storage path.

The canonical plan entrypoint SHALL be `<plan-output-dir>/plan.md` for both the single-file and bundle forms.

For the single-file form, the guidance SHALL write the generated plan as `<plan-output-dir>/plan.md`.

For the bundle form, the guidance SHALL write `<plan-output-dir>/plan.md` plus the supporting bundle files under the same `<plan-output-dir>/`.

The revise guidance SHALL preserve the current output directory unless the user explicitly asks to relocate the plan.

#### Scenario: Authoring asks for an output directory before writing
- **WHEN** a user invokes `houmao-agent-loop-pairwise-v2` to create a plan
- **AND WHEN** the request does not already name a writable plan directory
- **THEN** the guidance asks the user for the output directory before writing plan files
- **AND THEN** it does not invent a default storage path

#### Scenario: Single-file plan uses plan.md under the selected directory
- **WHEN** a user selects the single-file form for pairwise-v2 plan authoring
- **AND WHEN** the selected output directory is `/workspace/loop-plan`
- **THEN** the guidance writes the canonical plan entrypoint to `/workspace/loop-plan/plan.md`
- **AND THEN** it treats that file as the plan reference used later by `start`

#### Scenario: Bundle plan stays under one selected directory
- **WHEN** a user selects the bundle form for pairwise-v2 plan authoring
- **AND WHEN** the selected output directory is `/workspace/loop-plan`
- **THEN** the guidance writes `/workspace/loop-plan/plan.md` and the supporting bundle files under `/workspace/loop-plan/`
- **AND THEN** it does not scatter the authored plan across unrelated directories
