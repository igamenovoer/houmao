# Plan Structure

Use this reference to choose between the single-file and bundle plan forms and to keep the canonical entrypoint stable.

## Single-File Form

Use one Markdown file when the run is compact and the plan does not need many supporting notes or scripts.

Minimum sections:

- Objective
- Master
- Participants
- Delegation Policy
- Completion Condition
- Stop Policy
- Reporting Contract
- Script Inventory, when scripts exist
- Mermaid Control Graph

## Bundle Form

Use one directory when the run needs supporting Markdown files, script documentation, or agent-specific notes.

Canonical entrypoint:

- `plan.md`

Suggested bundle contents:

- `plan.md`
- `graph.md`
- `delegation.md`
- `reporting.md`
- `scripts/README.md`
- `scripts/<files>`
- `agents/<optional notes>.md`

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
- Do not hide plan-critical policy only inside an unreferenced support file.
- Do not omit the Mermaid control graph from the canonical plan surface.
