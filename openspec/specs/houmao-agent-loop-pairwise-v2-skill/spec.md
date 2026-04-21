# houmao-agent-loop-pairwise-v2-skill Specification

## Purpose
Define the packaged versioned enriched pairwise loop skill, including its manual invocation boundary, prestart preparation lane, expanded operator actions, and targeted preparation behavior.
## Requirements
### Requirement: Houmao provides a packaged `houmao-agent-loop-pairwise-v2` system skill
The system SHALL package a Houmao-owned system skill named `houmao-agent-loop-pairwise-v2` under the maintained system-skill asset root.

That packaged skill SHALL use `houmao-agent-loop-pairwise-v2` as both its skill name and its packaged asset directory name under `src/houmao/agents/assets/system_skills/`.

The top-level `SKILL.md` for that packaged skill SHALL describe the skill as the versioned enriched pairwise authoring, prestart, and run-control surface rather than as the stable pairwise contract.

The packaged `houmao-agent-loop-pairwise-v2` skill SHALL be manual-invocation-only. It SHALL instruct agents to use the skill only when the user explicitly asks for `houmao-agent-loop-pairwise-v2` by name.

That packaged skill SHALL remain distinct from both the restored stable `houmao-agent-loop-pairwise` skill and the lower-level messaging, mailbox, gateway, and advanced-usage skills that it composes.

That packaged skill SHALL own composed pairwise loop planning concerns, including multi-edge topology, recursive child-control edges, rendered control graphs, master-owned run planning, lifecycle preparation, run charters, and enriched run-control actions.

When that packaged skill references `houmao-adv-usage-pattern`, it SHALL treat the advanced-usage pairwise page as the elemental immediate driver-worker edge protocol to use per edge rather than as the owner of composed pairwise topology.

#### Scenario: User explicitly asks to invoke the v2 pairwise skill
- **WHEN** a user explicitly asks for `houmao-agent-loop-pairwise-v2`
- **THEN** `houmao-agent-loop-pairwise-v2` is the correct packaged Houmao-owned skill
- **AND THEN** it presents itself as the versioned enriched pairwise skill rather than as the restored stable pairwise skill

#### Scenario: Generic pairwise loop request does not auto-route to v2
- **WHEN** a user asks generically to plan or operate a pairwise loop without explicitly asking for `houmao-agent-loop-pairwise-v2`
- **THEN** `houmao-agent-loop-pairwise-v2` does not present itself as the default skill for that request
- **AND THEN** the request remains outside this packaged skill entrypoint unless the user later invokes the skill explicitly

### Requirement: The v2 skill preserves the enriched pairwise workflow surface
The packaged `houmao-agent-loop-pairwise-v2` skill SHALL preserve the enriched pairwise workflow currently carried by the renamed v2 asset tree.

That workflow SHALL include:

- authoring guidance,
- prestart preparation guidance,
- expanded operating guidance for enriched pairwise control, including restart recovery after participant stop or relaunch.

The canonical operator action vocabulary for `houmao-agent-loop-pairwise-v2` SHALL include at minimum:

- `plan`,
- `initialize`,
- `start`,
- `peek`,
- `ping`,
- `pause`,
- `resume`,
- `recover_and_continue`,
- `stop`,
- `hard-kill`.

The v2 guidance SHALL continue to define canonical observed states separately from those operator actions.

That observed-state vocabulary SHALL include at minimum:

- `authoring`,
- `initializing`,
- `awaiting_ack`,
- `ready`,
- `running`,
- `paused`,
- `recovering`,
- `recovered_ready`,
- `stopping`,
- `stopped`,
- `dead`.

#### Scenario: Reader sees the enriched operator action vocabulary in v2
- **WHEN** a reader opens the packaged `houmao-agent-loop-pairwise-v2` skill assets
- **THEN** the operating guidance includes the enriched operator action vocabulary including `recover_and_continue`
- **AND THEN** that vocabulary remains broader than the restored stable `houmao-agent-loop-pairwise` surface

#### Scenario: V2 keeps prestart guidance
- **WHEN** a reader opens the packaged `houmao-agent-loop-pairwise-v2` skill assets
- **THEN** the skill includes explicit prestart preparation guidance
- **AND THEN** that prestart lane remains packaged under the v2 skill rather than under the restored stable pairwise skill

#### Scenario: V2 exposes restart recovery as a distinct enriched control lane
- **WHEN** a reader opens the packaged `houmao-agent-loop-pairwise-v2` operating guidance
- **THEN** the guidance distinguishes `recover_and_continue` from both soft `resume` and terminal `hard-kill`
- **AND THEN** it exposes `recovering` and `recovered_ready` as canonical observed states before the run returns to `running`

### Requirement: Pairwise-v2 distinguishes soft resume from restart recovery
The packaged `houmao-agent-loop-pairwise-v2` guidance SHALL define `resume` as the action that restores one previously paused run whose participant set and wakeup posture remained logically live.

The guidance SHALL define `recover_and_continue` as the action that restores one accepted pairwise-v2 run after one or more participants were stopped, killed, or relaunched and later need to continue the same logical run under the same `run_id`.

During restart recovery, the guidance SHALL treat `recovering` as the observed state while participant rebinding, durable continuation-material refresh, or wakeup restoration is still in progress.

The guidance SHALL treat `recovered_ready` as the observed state after restart-recovery preparation is complete but before the designated master explicitly accepts continuation.

The guidance SHALL return the run to `running` only after the designated master explicitly replies `accepted` to the compact `recover_and_continue` trigger.

The guidance SHALL define `hard-kill` as terminal and SHALL NOT present it as an ordinary entrypoint to `recover_and_continue`.

#### Scenario: Previously paused run uses soft resume
- **WHEN** one pairwise-v2 run is currently `paused`
- **AND WHEN** the participant set and wakeup posture remained logically live
- **THEN** the guidance uses `resume` for that run
- **AND THEN** it does not require `recover_and_continue`

#### Scenario: Restarted participant uses recover_and_continue
- **WHEN** one accepted pairwise-v2 run has a participant that was stopped or relaunched
- **THEN** the guidance uses `recover_and_continue` rather than `resume`
- **AND THEN** the run does not return to `running` until restart recovery completes and the master explicitly accepts continuation

#### Scenario: Hard-killed run does not use ordinary restart recovery
- **WHEN** one pairwise-v2 run previously ended through `hard-kill`
- **THEN** the guidance does not present ordinary `recover_and_continue` as the next action for that run
- **AND THEN** it keeps `hard-kill` distinct from pause or restart recovery

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

### Requirement: Pairwise-v2 guidance avoids reindex workflow
The packaged `houmao-agent-loop-pairwise-v2` guidance SHALL NOT instruct callers to run a memory reindex operation after writing pages.

The guidance SHALL use the supported memory page resolve surface when it needs a precise memo-relative link or absolute page path.

#### Scenario: Initialization does not reindex after page write
- **WHEN** initialization writes an oversized routing packet page
- **THEN** the guidance records the returned or resolved `pages/<relative-page>` link where useful
- **AND THEN** it does not run or recommend a reindex command

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
