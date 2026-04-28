# Plan Structure

Use this reference to choose between the single-file and bundle forms, keep the canonical entrypoint stable, and make the workspace contract explicit.

## Output Directory Contract

Every authored pairwise-v4 plan should live under one user-chosen output directory.

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
- `<plan-output-dir>/constraint-coverage-audit.md`
- `<plan-output-dir>/templates/README.md`, when the run needs reusable reporting or bookkeeping scaffolds
- `<plan-output-dir>/templates/reporting/<files>`
- `<plan-output-dir>/templates/bookkeeping/<files>`
- `<plan-output-dir>/scripts/README.md`
- `<plan-output-dir>/scripts/<files>`
- `<plan-output-dir>/agents/<participant>.md`

## Single-File Form

Use one output directory containing only `plan.md` when the run is compact and does not need many supporting notes, scripts, or reusable reporting/bookkeeping templates.

Minimum sections:
- Objective
- Master
- Participants
- Workspace Contract
- Source Contract Summary
- Delegation Policy
- Prestart Procedure
- Routing Packets
- Durable Initialize Material
- Lifecycle Vocabulary
- Completion Condition
- Stop Policy
- Reporting Contract
- Constraint Coverage Audit
- Timeout-Watch Policy, when used
- Script Inventory, when scripts exist
- Mermaid Control Graph

## Bundle Form

Use one directory when the run needs supporting Markdown files, script documentation, agent-specific notes, or reusable reporting/bookkeeping templates.

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
- `constraint-coverage-audit.md`
- `templates/README.md`, when the run needs reusable reporting or bookkeeping scaffolds
- `templates/reporting/<files>`
- `templates/bookkeeping/<files>`
- `scripts/README.md`
- `scripts/<files>`
- `agents/<participant>.md`

When the run needs reusable reporting or bookkeeping scaffolds, use bundle form rather than single-file form.

## Strict Generated Document Templates

Pairwise-v4 authoring is template-first. When source task notes, user-provided documents with schema-like policy verb patterns, commons, rulebooks, or manually tuned examples govern the run, generate documents by filling the strict templates under `document-templates/`:

- `document-templates/plan.md` for canonical `plan.md`
- `document-templates/agent-note.md` for files under `agents/`
- `document-templates/reporting-template.md` for files under `templates/reporting/`
- `document-templates/bookkeeping-template.md` for files under `templates/bookkeeping/`
- `document-templates/constraint-coverage-audit.md` for coverage review

Keep required headings in order. Fill unknown required fields with `UNRESOLVED - <reason>` rather than deleting the section or replacing it with freeform prose.

## Source Contract Summary

Every v4 `plan.md` should include a central source-contract summary before the workspace contract when the run is derived from task notes, commons files, rulebooks, user-provided documents with schema-like policy verb patterns, or user-provided constraints.

The source-contract summary must record:
- referenced source paths or explicit user instructions
- preserved policy verbs such as `ALWAYS`, `NEVER`, `CHECK`, `RUN`, `READ`, `ANALYZE`, `DECIDE`, `OUTPUT`, `UPDATE`, `COMMIT`, `MERGE`, and `DISPATCH`
- a carried-forward constraints table with stable source-constraint IDs such as `SC-001`
- unresolved source inputs with explicit reasons

Project source constraints into central plan sections, role-local agent notes, routing packets, reporting templates, bookkeeping templates, scripts, or supporting files. Do not flatten policy-bearing verbs into generic prose when they define gates, required actions, forbidden actions, evidence, or output format.

## Workspace Contract

Every pairwise-v4 plan should record one authored workspace contract.

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

## Template Bundle

When a bundle plan includes reusable templates, keep them under `<plan-output-dir>/templates/`.

Use discoverable categories:
- `templates/reporting/` for report forms derived from the reporting contract
- `templates/bookkeeping/` for task-shaped bookkeeping scaffolds derived from the objective, topology, participant roles, and declared bookkeeping paths

Record those templates as authored reusable source artifacts. Filled-in copies or mutable run artifacts belong in declared bookkeeping paths during execution, not back inside the authored template bundle.

Reporting and bookkeeping templates should carry any state schema, evidence requirement, cadence, owner, update rule, or output format that came from the source task or other user-provided source document. If a source rule cannot be safely converted into a reusable template slot, record it in `constraint-coverage-audit.md` as unresolved.

## Agent Notes

Files under `agents/` should use `document-templates/agent-note.md` when role-local notes are generated. Each note should include:
- role
- source constraints carried forward
- hard gates
- SOP verbs
- reporting and evidence duties
- related skill posture

Agent notes support the routing packet contract. They must not replace exact routing packets, child dispatch tables, or result-return instructions.

## Constraint Coverage Audit

Use `constraint-coverage-audit.md` to map each extracted high-salience source rule to its central and runtime projections.

Coverage statuses:
- `covered`: the rule is projected into the canonical plan plus the relevant runtime-facing surfaces
- `unresolved`: the rule is important but needs a user decision, missing source, or unsafe inference
- `excluded`: the rule was intentionally not projected, with a reason

The final plan is not complete if high-salience source rules are missing from the audit or if unresolved rows lack `UNRESOLVED - <reason>`.

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
- `ready`
- `running`
- `paused`
- `recovering`
- `recovered_ready`
- `stopping`
- `stopped`
- `dead`

## Run Memo Material

Every plan using pairwise-v4 managed memory should record:
- initialize memo-slot expectations for the designated master and other participants, typically under slot `initialize`
- run-scoped continuation page namespace such as `loop-runs/pairwise-v4/<run_id>/recover-and-continue.md`
- runtime-owned recovery record path such as `<runtime-root>/loop-runs/pairwise-v2/<run_id>/record.json`
- append-only recovery history path such as `<runtime-root>/loop-runs/pairwise-v2/<run_id>/events.jsonl`
- exact begin and end sentinel convention for memo blocks keyed by `run_id` and slot
- what each initialize memo block must contain for masters versus other participants
- fail-closed replacement handling for duplicate memo blocks

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
- routing-packet validation as the pairwise-v4 prestart strategy
- workspace contract summary or `workspace-contract.md` reference
- graph artifact and packet JSON artifact locations when available
- optional launch-profile references for required participants that `initialize` may launch, plus the rule that mailbox association is checked on those profiles before launch
- email/mailbox verification rule for the designated master and every required participant
- gateway mail-notifier verification or enablement for every required mail-driven participant with supported live gateway and mailbox surfaces
- gateway mail-notifier interval: `5s` unless the user specified otherwise
- ordinary `start` mail-delivery rule, with direct prompt only by explicit user request
- initialize memo-slot expectations for the designated master and other participants
- runtime-owned recovery record path family and continuation page namespace
- exact begin/end sentinel convention for memo reference blocks keyed by `run_id` and slot
- initialize memo write procedure
- routing packet validation rules, root packet location, packet inventory, and child dispatch-table expectations when routing packets are part of the plan
- authored topology or descendant relationships used to verify packet coverage
- generated template inventory or a reference to `templates/README.md`, when reusable templates are part of the bundle
- initialization state transitions: `initializing`, `ready`
- readiness rules for routing-packet validation, participant launch, email/mailbox verification, notifier setup, and memo materialization
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
- Do not keep a reusable template inventory only in conversation state; record it in the authored bundle.
- Do not leave the workspace contract implicit.
- Do not leave the source contract summary implicit when source task notes, user-provided documents with schema-like policy verb patterns, or rulebooks drive the run.
- Do not freeform-organize generated files when a v4 strict document template exists for that file type.
- Do not drop policy-bearing verbs such as `ALWAYS`, `NEVER`, `CHECK`, `RUN`, `READ`, `ANALYZE`, `DECIDE`, `OUTPUT`, `UPDATE`, `COMMIT`, `MERGE`, or `DISPATCH`.
- Do not describe custom bookkeeping as a fixed standard subtree under per-agent `kb/`.
- Do not describe files under `<plan-output-dir>/templates/` as mutable bookkeeping outputs or runtime-owned recovery state.
- Do not generate short reminder-only agent notes when role-specific hard gates exist.
- Do not claim source-rule coverage until `constraint-coverage-audit.md` maps extracted rules to central and runtime projections.
- Do not leave descendant relationships ambiguous when `initialize` needs to validate routing-packet coverage.
- Do not invent launch-profile references for participants the plan did not specify.
- Do not skip initialize memo materialization when managed memory is being used.
- Do not let the run reach `ready` when the designated master or any required participant lacks email/mailbox support.
- Do not infer memo replacement boundaries from headings, nearby prose, or fuzzy text.
- Do not require acknowledgement replies before ordinary `start`.
- Do not require runtime intermediate agents to recompute subtree slices that should have been prepared during authoring.
- Do not mix lifecycle action names and observed state names into one ambiguous status field.
- Do not hide plan-critical policy only inside an unreferenced support file.
- Do not omit the Mermaid control graph from the canonical plan surface.
- Do not treat runtime-owned recovery files as ordinary workspace or bookkeeping surfaces.
- Do not store mutable recovery ledgers only inside the authored plan bundle; the recovery record belongs under the runtime root.
