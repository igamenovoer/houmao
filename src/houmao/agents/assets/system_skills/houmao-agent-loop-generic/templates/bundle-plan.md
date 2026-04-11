# Bundle Generic Loop Graph Plan Template

Use this form when the run needs supporting Markdown files or scripts but still needs one canonical entrypoint.

## Suggested Layout

```text
loop-plan/
  plan.md
  graph.md
  components.md
  graph-policy.md
  result-routing.md
  reporting.md
  scripts/
    README.md
    <script files>
  agents/
    <optional per-agent notes>.md
```

## Canonical Entrypoint

`plan.md` is the canonical entrypoint. The user agent should point the root owner at `plan.md` or at the bundle root with an explicit instruction to open `plan.md` first.

## `plan.md` Skeleton

```md
# Objective
<summary>

# Master / Root Owner
<designated master or root owner>

# Participants
<named set>

# Loop Components
See `components.md`.

# Component Dependencies
See `components.md`.

# Graph Policy
See `graph-policy.md`.

# Result Routing Contract
See `result-routing.md`.

# Completion Condition
<user-defined operational success condition>

# Stop Policy
Default stop mode: interrupt-first

# Reporting Contract
See `reporting.md`.

# Supporting Files
- `graph.md`
- `components.md`
- `graph-policy.md`
- `result-routing.md`
- `reporting.md`
- `scripts/README.md`

# Mermaid Generic Loop Graph
<top-level mermaid graph>
```

## `components.md` Inventory

List each component with:

- `component_id`
- `component_type`
- participants
- root, driver, or origin
- downstream target or lane order
- elemental protocol
- result routing
- policy
- dependencies

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
- Do not leave component policy or result routing only in unreferenced support files.
- Do not leave script behavior undocumented when scripts are part of the plan.
