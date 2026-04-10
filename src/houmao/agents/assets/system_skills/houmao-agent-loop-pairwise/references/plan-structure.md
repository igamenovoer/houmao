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
- Participant Preparation
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

## Participant Preparation Briefs

Each participant brief should record:

- participant identity and role
- resources, artifacts, or tools available to that participant
- allowed delegation targets or allowed delegation set
- delegation-pattern expectations for work categories, when that distinction matters
- mailbox, reminder, receipt, or result obligations
- forbidden actions

Participant preparation briefs must stay standalone. Do not require a participant to know which upstream participant may later contact it during the preparation stage.

## `prestart.md`

For bundle plans, `prestart.md` should record:

- notifier preflight expectations
- preparation-mail posture: `fire_and_proceed` or `require_ack`
- operator reply policy for preparation mail
- initialization state transitions: `initializing`, `awaiting_ack`, `ready`
- readiness barrier rules, when acknowledgements are required
- how the master trigger is kept separate from the preparation wave

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
- Do not leave the bundle form without `prestart.md` when preparation mail is part of the run contract.
- Do not mix lifecycle action names and observed state names into one ambiguous status field.
- Do not hide plan-critical policy only inside an unreferenced support file.
- Do not omit the Mermaid control graph from the canonical plan surface.
