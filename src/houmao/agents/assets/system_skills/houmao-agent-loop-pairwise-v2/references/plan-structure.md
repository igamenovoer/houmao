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
- Preparation Targets
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

## Participant Preparation Briefs

Each participant brief should record:

- participant identity and role
- resources, artifacts, or tools available to that participant
- allowed delegation targets or allowed delegation set
- delegation-pattern expectations for work categories, when that distinction matters
- mailbox, reminder, receipt, or result obligations
- forbidden actions

Participant preparation briefs must stay standalone. Do not require a participant to know which upstream participant may later contact it during the preparation stage.

Preparation material and preparation mail recipients are separate. Plans may retain preparation material for all participants, but the default preparation mail recipient set is the participants that have descendants in the authored topology. Leaf participants are included only when the user explicitly asks to prepare leaf agents, prepare all participants, or names leaf participants in the preparation target set.

## `prestart.md`

For bundle plans, `prestart.md` should record:

- notifier preflight expectations
- authored topology or descendant relationships used to identify delegating/non-leaf participants
- preparation target policy: `delegating_non_leaf` by default, `all_participants` only when explicitly requested, or a named explicit target set
- preparation-mail posture: `fire_and_proceed` or `require_ack`
- operator reply policy for preparation mail
- initialization state transitions: `initializing`, `awaiting_ack`, `ready`
- readiness barrier rules for targeted preparation recipients, when acknowledgements are required
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
- Do not leave descendant relationships ambiguous when `initialize` needs to determine the default preparation target set.
- Do not treat participant preparation material as proof that every participant should receive preparation mail.
- Do not mix lifecycle action names and observed state names into one ambiguous status field.
- Do not hide plan-critical policy only inside an unreferenced support file.
- Do not omit the Mermaid control graph from the canonical plan surface.
