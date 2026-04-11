# Plan Structure

Use this reference to choose between the single-file and bundle plan forms and to keep the canonical entrypoint stable.

## Single-File Form

Use one Markdown file when the run is compact and the plan does not need many supporting notes or scripts.

Minimum sections:

- Objective
- Master / Root Owner
- Participants
- Loop Components
- Component Dependencies
- Graph Policy
- Result Routing Contract
- Completion Condition
- Stop Policy
- Reporting Contract
- Script Inventory, when scripts exist
- Mermaid Generic Loop Graph

## Bundle Form

Use one directory when the run needs supporting Markdown files, script documentation, component tables, or agent-specific notes.

Canonical entrypoint:

- `plan.md`

Suggested bundle contents:

- `plan.md`
- `graph.md`
- `components.md`
- `graph-policy.md`
- `result-routing.md`
- `reporting.md`
- `scripts/README.md`
- `scripts/<files>`
- `agents/<optional notes>.md`

## Component Inventory Fields

For each component, record:

- `component_id`
- `component_type`
- participants
- root, driver, or origin
- downstream target or lane order
- result-return target
- policy
- dependencies
- elemental protocol to use

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
- Do not hide plan-critical component policy only inside an unreferenced support file.
- Do not omit the Mermaid generic loop graph from the canonical plan surface.
