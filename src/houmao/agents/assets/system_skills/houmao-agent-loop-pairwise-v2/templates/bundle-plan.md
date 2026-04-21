# Bundle Pairwise Loop Plan Template

Use this form when the run needs supporting Markdown files or scripts but still needs one canonical entrypoint. Ask for the output directory if it is not already known, then write the bundle there.

## Suggested Layout

```text
<plan-output-dir>/
  plan.md
  prestart.md
  routing-packets.md
  graph.md
  delegation.md
  reporting.md
  scripts/
    README.md
    <script files>
  agents/
    <participant-a>.md
    <participant-b>.md
```

## Canonical Entrypoint

`plan.md` is the canonical entrypoint. The user agent should point the master at `<plan-output-dir>/plan.md`, or at the bundle root with an explicit instruction to open `plan.md` first.

## `plan.md` Skeleton

```md
# Objective
<summary>

# Master
<designated master>

# Participants
<named set>

# Topology
<descendant relationships that identify delegating/non-leaf participants and leaves>

Graph artifact: <none | NetworkX node-link graph path>
Packet JSON artifact: <none | packet JSON path for validate-packets>

# Delegation Policy
See `delegation.md`.

# Prestart Procedure
See `prestart.md`.

# Routing Packets
See `routing-packets.md`.

# Lifecycle Vocabulary
- operator actions: `plan`, `initialize`, `start`, `peek`, `ping`, `pause`, `resume`, `recover_and_continue`, `stop`, `hard-kill`
- observed states: `authoring`, `initializing`, `awaiting_ack`, `ready`, `running`, `paused`, `recovering`, `recovered_ready`, `stopping`, `stopped`, `dead`

# Completion Condition
<user-defined operational success condition>

# Stop Policy
Default stop mode: interrupt-first

# Reporting Contract
See `reporting.md`.

# Supporting Files
- `prestart.md`
- `routing-packets.md`
- `graph.md`
- `delegation.md`
- `reporting.md`
- `scripts/README.md`

# Mermaid Control Graph
<top-level mermaid graph>
```

## `prestart.md`

Record:

- selected `prestart_strategy`: default `precomputed_routing_packets`, or explicit `operator_preparation_wave`
- durable initialize page namespace and durable start-charter page namespace
- continuation page namespace and runtime-owned recovery record path family
- memo sentinel convention for run-owned reference blocks
- durable initialize page and memo reference-block write procedure
- notifier preflight procedure for `operator_preparation_wave`
- gateway mail-notifier interval: `5s` unless the user specified otherwise for `operator_preparation_wave`
- preparation-mail target policy: delegating or non-leaf participants by default, or an explicit target set when provided
- acknowledgement posture: `fire_and_proceed` by default, or explicit `require_ack`
- graph artifact and packet JSON artifact locations when available
- graph-tool preflight: `analyze`, optional `slice`, and `packet-expectations` during packet authoring when a graph artifact exists
- routing packet validation procedure, root packet location, packet inventory, and child dispatch-table expectations
- validation fallback when graph or packet JSON artifacts are unavailable: visible topology, descendant relationships, packet inventory, child dispatch tables, and freshness markers checked manually
- preparation-mail procedure for targeted preparation recipients when `operator_preparation_wave` is selected
- operator reply policy for preparation mail: `none` for default `fire_and_proceed`, or `operator_mailbox` for explicit `require_ack`
- in-loop job communication posture: advise all agents to use email/mailbox for pairwise edge requests, receipts, and results by default
- initialization state transitions: `initializing`, `awaiting_ack`, `ready`
- readiness behavior for the selected strategy
- how the master trigger remains separate from `initialize`

## `routing-packets.md`

Record one root packet for the designated master and one child packet for each parent-to-child edge. Each packet should record:

- packet id
- run id or placeholder
- plan id and revision or digest
- intended recipient
- immediate driver
- local role and objective
- allowed delegation targets
- result-return contract back to the immediate driver
- mailbox, reminder, receipt, result, or timeout-watch obligations
- forbidden actions
- child dispatch table for non-leaf recipients
- exact child packet text or exact references to packet text
- forwarding guardrails for verbatim append and fail-closed mismatch handling

## `agents/<participant>.md`

Use agent notes only for supporting material that does not replace the routing packet contract.

## `scripts/README.md` Inventory

List each script with:

- purpose
- allowed caller agents
- inputs
- outputs
- side effects
- failure behavior

## Guardrails

- Do not omit the top-level Mermaid graph from `plan.md`.
- Do not make `graph.md` the only place where the topology is visible.
- Do not leave routing packets only in a shared upstream-aware matrix that runtime agents must reinterpret.
- Do not ask intermediate runtime agents to recompute child packet content from the full plan.
- Do not ask intermediate runtime agents to run graph analysis or recompute descendant slices after `start`; they must use dispatch tables and exact child packets.
- Do not leave script behavior undocumented when scripts are part of the plan.
