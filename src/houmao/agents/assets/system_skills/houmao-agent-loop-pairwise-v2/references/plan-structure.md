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
- Email Initialization
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

## Email Initialization

Every plan using the default `email_initialization` strategy should record:

- gateway mail-notifier setup before initialization mail
- gateway mail-notifier interval: `5s` unless the user specified otherwise
- initialization email target policy: all named participants by default, or an explicit target set when provided
- acknowledgement posture: `fire_and_proceed` by default, or explicit `require_ack`
- operator reply policy: `none` for `fire_and_proceed`, or `operator_mailbox` for `require_ack`
- in-loop job communication posture: advise all agents to use email/mailbox for pairwise edge requests, receipts, and results by default
- fallback behavior for participants whose live gateway or mailbox binding does not support notifier polling

## Routing Packets

Every plan using routing packets should record:

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
- forwarding guardrails: append child packets verbatim to pairwise edge request email, do not edit/merge/summarize packets unless the plan explicitly permits it, and fail closed on missing, mismatched, or stale packets

Routing packets should be prepared at authoring time so intermediate runtime agents do not need to infer descendants or recompute graph slices from the full plan.

When a plan keeps a NetworkX node-link graph and packet JSON document for machine checks, use `houmao-mgr internals graph high analyze --input <graph.json>`, optional `houmao-mgr internals graph high slice --input <graph.json> --root <agent> --direction descendants`, and `houmao-mgr internals graph high packet-expectations --input <graph.json>` during packet authoring. Use `houmao-mgr internals graph high validate-packets --graph <graph.json> --packets <packets.json>` before treating initialization as `ready` when routing packets are part of the plan. These commands validate structural coverage only; they do not replace semantic review of delegation policy, forbidden actions, result routing, or lifecycle vocabulary.

## `prestart.md`

For bundle plans, `prestart.md` should record:

- selected `prestart_strategy`: default `email_initialization`, or explicit packet-only initialization when the user disables email initialization
- graph artifact and packet JSON artifact locations when available
- notifier preflight expectations
- gateway mail-notifier interval: `5s` unless the user specified otherwise
- initialization email target policy and delivery procedure
- acknowledgement posture: default `fire_and_proceed`, or explicit `require_ack`
- operator reply policy for initialization mail
- routing packet validation rules, root packet location, packet inventory, and child dispatch-table expectations when routing packets are part of the plan
- authored topology or descendant relationships used to verify packet coverage
- initialization state transitions: `initializing`, `awaiting_ack`, `ready`
- readiness rules for the selected strategy: notifier setup plus initialization mail, explicit acknowledgements when `require_ack` is selected, and packet validation when routing packets are part of the plan
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
- Do not leave descendant relationships ambiguous when `initialize` needs to validate routing-packet coverage or initialization targets.
- Do not skip default email initialization merely because routing packet material exists.
- Do not require acknowledgement by default; use `fire_and_proceed` unless the plan explicitly selects `require_ack`.
- Do not use a gateway mail-notifier interval other than `5s` unless the user or plan specifies another interval.
- Do not require runtime intermediate agents to recompute subtree slices that should have been prepared during authoring.
- Do not mix lifecycle action names and observed state names into one ambiguous status field.
- Do not hide plan-critical policy only inside an unreferenced support file.
- Do not omit the Mermaid control graph from the canonical plan surface.
