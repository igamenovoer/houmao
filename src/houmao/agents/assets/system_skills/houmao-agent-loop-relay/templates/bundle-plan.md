# Bundle Relay Loop Plan Template

Use this form when the run needs supporting Markdown files or scripts but still needs one canonical entrypoint.

## Suggested Layout

```text
loop-plan/
  plan.md
  graph.md
  routes.md
  reporting.md
  results.md
  scripts/
    README.md
    <script files>
  agents/
    <optional per-agent notes>.md
```

## Canonical Entrypoint

`plan.md` is the canonical entrypoint. The user agent should point the master at `plan.md` or at the bundle root with an explicit instruction to open `plan.md` first.

## `plan.md` Skeleton

```md
# Objective
<summary>

# Master / Loop Origin
<designated master>

# Participants
<named set>

# Route Policy
See `routes.md`.

# Result Return Contract
See `results.md`.

# Completion Condition
<user-defined operational success condition>

# Stop Policy
Default stop mode: interrupt-first

# Reporting Contract
See `reporting.md`.

# Supporting Files
- `graph.md`
- `routes.md`
- `reporting.md`
- `results.md`
- `scripts/README.md`

# Mermaid Relay Graph
<top-level mermaid graph>
```

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
- Do not leave script behavior undocumented when scripts are part of the plan.
