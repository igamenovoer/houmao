# Plan Structure

Use this reference to choose between the single-file and bundle forms, keep the canonical entrypoint stable, and make the workspace contract explicit.

## Output Directory Contract

Every authored pairwise-v3 plan should live under one user-chosen output directory.

Canonical entrypoint for both forms:
- `<plan-output-dir>/plan.md`

Single-file output shape:
- `<plan-output-dir>/plan.md`

Bundle output shape:
- `<plan-output-dir>/plan.md`
- `<plan-output-dir>/workspace-contract.md`
- `<plan-output-dir>/prestart.md`
- `<plan-output-dir>/routing-packets.md` or `<plan-output-dir>/routing-packets/`
- `<plan-output-dir>/initialize-material.md`, when a separate durable-initialize note helps authoring
- `<plan-output-dir>/graph.md`
- `<plan-output-dir>/delegation.md`
- `<plan-output-dir>/reporting.md`
- `<plan-output-dir>/scripts/README.md`
- `<plan-output-dir>/scripts/<files>`
- `<plan-output-dir>/agents/<participant>.md`

## Single-File Form

Use one output directory containing only `plan.md` when the run is compact and does not need many supporting notes or scripts.

Minimum sections:
- Objective
- Master
- Participants
- Workspace Contract
- Delegation Policy
- Prestart Procedure
- Prestart Strategy
- Routing Packets
- Durable Initialize Material
- Operator Preparation Wave, when used
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
- `workspace-contract.md`
- `prestart.md`
- `routing-packets.md` or `routing-packets/`
- `initialize-material.md`, when a separate durable-initialize note helps authoring
- `graph.md`
- `delegation.md`
- `reporting.md`
- `scripts/README.md`
- `scripts/<files>`
- `agents/<participant>.md`

## Workspace Contract

Every pairwise-v3 plan should record one authored workspace contract.

The workspace contract must declare exactly one mode:
- `standard`
- `custom`

For `standard`, record:
- selected posture: `in-repo` or `out-of-repo`
- required task-scoping fields such as `task-name` for in-repo mode
- launch cwd or shared visibility surface
- private source-mutation surfaces
- shared writable surfaces when applicable
- default read-only surfaces
- ad hoc worktree posture
- relevant task-local `workspace.md` reference when one exists

For `custom`, record:
- explicit launch cwd
- explicit source write paths
- explicit shared writable paths
- explicit bookkeeping paths
- explicit read-only paths
- explicit ad hoc worktree posture

The workspace contract should describe allowed surfaces and ownership, not prescribe one fixed subtree under per-agent `kb/`.

## Standard In-Repo Workspace Contract

When the plan uses standard in-repo posture, treat the task root as:

- `<repo-root>/houmao-ws/<task-name>`

Record:
- repo-level index path: `<repo-root>/houmao-ws/workspaces.md`
- authoritative task contract: `<task-root>/workspace.md`
- task-local shared knowledge surface: `<task-root>/shared-kb/`
- one task-scoped agent directory per participant
- task-qualified branches such as `houmao/<task-name>/<agent-name>/main`

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
- `recover_and_continue`
- `stop`
- `hard-kill`

Canonical observed states:
- `authoring`
- `initializing`
- `awaiting_ack`
- `ready`
- `running`
- `paused`
- `recovering`
- `recovered_ready`
- `stopping`
- `stopped`
- `dead`

`awaiting_ack` belongs only to explicit `operator_preparation_wave` runs that selected `require_ack`; ordinary `start` itself is not an acknowledgement state.

## Run Memo Material

Every plan using pairwise-v3 managed memory should record:
- initialize memo-slot expectations for the designated master and other participants, typically under slot `initialize`
- run-scoped continuation page namespace such as `loop-runs/pairwise-v3/<run_id>/recover-and-continue.md`
- runtime-owned recovery record path such as `<runtime-root>/loop-runs/pairwise-v2/<run_id>/record.json`
- append-only recovery history path such as `<runtime-root>/loop-runs/pairwise-v2/<run_id>/events.jsonl`
- exact begin and end sentinel convention for memo blocks keyed by `run_id` and slot
- what each initialize memo block must contain for masters versus other participants
- fail-closed replacement handling for duplicate memo blocks

## Operator Preparation Wave

Every plan using explicit `operator_preparation_wave` should record:
- gateway mail-notifier setup before preparation mail
- gateway mail-notifier interval: `5s` unless the user specified otherwise
- preparation-mail target policy: delegating or non-leaf participants by default, leaf participants only when explicitly requested
- acknowledgement posture: `fire_and_proceed` by default, or explicit `require_ack`
- operator reply policy: `none` for `fire_and_proceed`, or `operator_mailbox` for `require_ack`
- initialize memo posture for the preparation recipients
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

When a plan keeps a NetworkX node-link graph and packet JSON document for machine checks, use:
- `houmao-mgr internals graph high analyze --input <graph.json>`
- optional `houmao-mgr internals graph high slice --input <graph.json> --root <agent> --direction descendants`
- `houmao-mgr internals graph high packet-expectations --input <graph.json>`
- `houmao-mgr internals graph high validate-packets --graph <graph.json> --packets <packets.json>`

These commands validate structural coverage only; they do not replace semantic review of delegation policy, forbidden actions, result routing, or lifecycle vocabulary.

## `prestart.md`

For bundle plans, `prestart.md` should record:
- selected `prestart_strategy`: default `precomputed_routing_packets`, or explicit `operator_preparation_wave`
- workspace contract summary or `workspace-contract.md` reference
- graph artifact and packet JSON artifact locations when available
- optional launch-profile references for required participants that `initialize` may launch, plus the rule that mailbox association is checked on those profiles before launch
- email/mailbox verification rule for the designated master and every required participant
- ordinary `start` mail-delivery rule, with direct prompt only by explicit user request
- initialize memo-slot expectations for the designated master and other participants
- runtime-owned recovery record path family and continuation page namespace
- exact begin/end sentinel convention for memo reference blocks keyed by `run_id` and slot
- initialize memo write procedure
- explicit `operator_preparation_wave` notifier preflight expectations, when that strategy is selected
- gateway mail-notifier interval: `5s` unless the user specified otherwise for `operator_preparation_wave`
- preparation-mail target policy and delivery procedure, when `operator_preparation_wave` is selected
- acknowledgement posture: default `fire_and_proceed`, or explicit `require_ack` for `operator_preparation_wave`
- operator reply policy for preparation mail
- routing packet validation rules, root packet location, packet inventory, and child dispatch-table expectations when routing packets are part of the plan
- authored topology or descendant relationships used to verify packet coverage
- initialization state transitions: `initializing`, `awaiting_ack`, `ready`
- readiness rules for the selected strategy
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

- Do not invent the plan output directory when the user has not provided one.
- Do not leave the single-file form without `plan.md`.
- Do not leave the bundle form without `plan.md`.
- Do not leave the bundle form without `prestart.md` when prestart strategy is part of the run contract.
- Do not leave the workspace contract implicit.
- Do not describe custom bookkeeping as a fixed standard subtree under per-agent `kb/`.
- Do not leave descendant relationships ambiguous when `initialize` needs to validate routing-packet coverage or explicit preparation-wave targets.
- Do not describe explicit `operator_preparation_wave` as the default prestart strategy.
- Do not invent launch-profile references for participants the plan did not specify.
- Do not skip initialize memo materialization when managed memory is being used.
- Do not let the run reach `ready` when the designated master or any required participant lacks email/mailbox support.
- Do not infer memo replacement boundaries from headings, nearby prose, or fuzzy text.
- Do not require acknowledgement by default; use `fire_and_proceed` unless the plan explicitly selects `require_ack`.
- Do not use a gateway mail-notifier interval other than `5s` for `operator_preparation_wave` unless the user or plan specifies another interval.
- Do not require runtime intermediate agents to recompute subtree slices that should have been prepared during authoring.
- Do not mix lifecycle action names and observed state names into one ambiguous status field.
- Do not hide plan-critical policy only inside an unreferenced support file.
- Do not omit the Mermaid control graph from the canonical plan surface.
- Do not treat runtime-owned recovery files as ordinary workspace or bookkeeping surfaces.
- Do not store mutable recovery ledgers only inside the authored plan bundle; the recovery record belongs under the runtime root.
