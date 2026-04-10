# Plan Structure

Use this reference to choose between the single-file and bundle plan forms and to keep the canonical entrypoint stable.

## Single-File Form

Use one Markdown file when the run is compact and the plan does not need many supporting notes or scripts.

Minimum sections:

- Objective
- Master / Loop Origin
- Participants
- Route Policy
- Result Return Contract
- Relay Lanes
- Completion Condition
- Stop Policy
- Reporting Contract
- Script Inventory, when scripts exist
- Mermaid Relay Graph

## Bundle Form

Use one directory when the run needs supporting Markdown files, script documentation, route tables, or agent-specific notes.

Canonical entrypoint:

- `plan.md`

Suggested bundle contents:

- `plan.md`
- `graph.md`
- `routes.md`
- `reporting.md`
- `results.md`
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
- Do not hide plan-critical routing policy only inside an unreferenced support file.
- Do not omit the Mermaid relay graph from the canonical plan surface.
