# Plan Structure

Use this reference to choose between the single-file and bundle plan forms and to keep the canonical entrypoint stable.

## Single-File Form

Use one Markdown file when the run is compact and the plan does not need many supporting notes or scripts.

Minimum sections:

- Objective
- Master
- Participants
- Delegation Policy
- Prestart Procedure
- Prestart Strategy
- Routing Packets
- Operator Preparation Wave, when explicitly selected
- Lifecycle Vocabulary
- Completion Condition
- Stop Policy
- Reporting Contract
- Timeout-Watch Policy, when used
- Script Inventory, when scripts exist
- Mermaid Control Graph

## Bundle Form

Use one directory when the run needs supporting Markdown files, script documentation, or agent-specific notes.

Canonical entrypoint:

- `plan.md`

Suggested bundle contents:

- `plan.md`
- `prestart.md`
- `routing-packets.md` or `routing-packets/`
- `graph.md`
- `delegation.md`
- `reporting.md`
- `scripts/README.md`
- `scripts/<files>`
- `agents/<participant>.md`

## Lifecycle Vocabulary

Every plan should record the canonical lifecycle vocabulary separately for operator actions and observed states.

Canonical operator actions:

- `plan`
- `initialize`
- `start`
- `peek`
- `ping`
- `pause`
- `resume`
- `stop`
- `hard-kill`

Canonical observed states:

- `authoring`
- `initializing`
- `awaiting_ack`
- `ready`
- `running`
- `paused`
- `stopping`
- `stopped`
- `dead`

## Routing Packets

Every plan using the default `precomputed_routing_packets` strategy should record:

- root routing packet location for the designated master
- NetworkX node-link graph artifact location when machine-readable topology is available
- packet JSON document location when machine-readable packet validation is available
- routing packet inventory for every parent-to-child pairwise edge
- plan id plus plan revision, digest, or equivalent freshness marker used by every packet
- intended recipient and immediate driver for every packet
- local role, local objective, resources, delegation authority, and forbidden actions for every packet recipient
- result-return contract back to the immediate driver
- mailbox, reminder, receipt, result, or timeout-watch obligations
- child dispatch table for each non-leaf packet
- exact child packet text or exact references to child packet text for every child a non-leaf recipient may contact
- forwarding guardrails: append child packets verbatim to ordinary pairwise edge requests, do not edit/merge/summarize packets unless the plan explicitly permits it, and fail closed on missing, mismatched, or stale packets

Routing packets should be prepared at authoring time so intermediate runtime agents do not need to infer descendants or recompute graph slices from the full plan.

When a plan keeps a NetworkX node-link graph and packet JSON document for machine checks, use `houmao-mgr internals graph high analyze --input <graph.json>`, optional `houmao-mgr internals graph high slice --input <graph.json> --root <agent> --direction descendants`, and `houmao-mgr internals graph high packet-expectations --input <graph.json>` during packet authoring. Use `houmao-mgr internals graph high validate-packets --graph <graph.json> --packets <packets.json>` before treating default initialization as `ready`. These commands validate structural coverage only; they do not replace semantic review of delegation policy, forbidden actions, result routing, or lifecycle vocabulary.

## Operator Preparation Wave

When the plan explicitly selects `operator_preparation_wave`, preparation material and preparation mail recipients are separate. Plans may retain preparation material for all participants, but the explicit preparation mail recipient set targets the participants that have descendants in the authored topology by default. Leaf participants are included only when the user explicitly asks to prepare leaf agents, prepare all participants, or names leaf participants in the preparation target set.

## `prestart.md`

For bundle plans, `prestart.md` should record:

- selected `prestart_strategy`: default `precomputed_routing_packets`, or explicit `operator_preparation_wave`
- graph artifact and packet JSON artifact locations when available
- notifier preflight expectations
- routing packet validation rules, root packet location, packet inventory, and child dispatch-table expectations for default `precomputed_routing_packets`
- authored topology or descendant relationships used to verify packet coverage
- preparation target policy for explicit `operator_preparation_wave`: `delegating_non_leaf` by default, `all_participants` only when explicitly requested, or a named explicit target set
- preparation-mail posture for explicit `operator_preparation_wave`: `fire_and_proceed` or `require_ack`
- operator reply policy for explicit preparation mail
- initialization state transitions: `initializing`, `awaiting_ack`, `ready`
- readiness rules for the selected strategy: packet validation for `precomputed_routing_packets`, or targeted preparation plus acknowledgements when explicit `operator_preparation_wave` requires them
- how the master trigger is kept separate from `initialize`

## Script Inventory Fields

For each script, record:

- path
- purpose
- allowed caller agents
- inputs
- outputs
- side effects
- failure behavior

## Guardrails

- Do not leave the bundle form without `plan.md`.
- Do not leave the bundle form without `prestart.md` when prestart strategy is part of the run contract.
- Do not leave descendant relationships ambiguous when `initialize` needs to validate routing-packet coverage or explicit preparation-wave targets.
- Do not treat routing packet material as permission to send operator-origin preparation mail.
- Do not treat operator preparation material as proof that every participant should receive preparation mail.
- Do not require runtime intermediate agents to recompute subtree slices that should have been prepared during authoring.
- Do not mix lifecycle action names and observed state names into one ambiguous status field.
- Do not hide plan-critical policy only inside an unreferenced support file.
- Do not omit the Mermaid control graph from the canonical plan surface.
