# Bundle Pairwise Loop Plan Template

Use this form when the run needs supporting Markdown files or scripts but still needs one canonical entrypoint.

## Suggested Layout

```text
loop-plan/
  plan.md
  graph.json
  graph.md
  delegation.md
  reporting.md
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

# Master
<designated master>

# Participants
<named set>

# Delegation Policy
See `delegation.md`.

# Completion Condition
<user-defined operational success condition>

# Stop Policy
Default stop mode: interrupt-first

# Mail-Notifier Setup
- gateway mail-notifier interval: `5s` unless the user specified otherwise

# Reporting Contract
See `reporting.md`.

# Graph-Tool Preflight
- graph artifact: <none | `graph.json` or external NetworkX node-link graph path>
- `analyze`: <none | summary or reference>
- `slice`: <none | summary or reference>
- `render-mermaid scaffold`: <none | summary or reference>

# Supporting Files
- `graph.json` when a graph artifact exists
- `graph.md`
- `delegation.md`
- `reporting.md`
- `scripts/README.md`

# Mermaid Control Graph
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
