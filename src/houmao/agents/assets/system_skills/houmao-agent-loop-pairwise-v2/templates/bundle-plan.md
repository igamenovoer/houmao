# Bundle Pairwise Loop Plan Template

Use this form when the run needs supporting Markdown files or scripts but still needs one canonical entrypoint.

## Suggested Layout

```text
loop-plan/
  plan.md
  prestart.md
  graph.md
  delegation.md
  reporting.md
  scripts/
    README.md
    <script files>
  agents/
    <participant-a>.md
    <participant-b>.md
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

# Prestart Procedure
See `prestart.md`.

# Lifecycle Vocabulary
- operator actions: `plan`, `initialize`, `start`, `peek`, `ping`, `pause`, `resume`, `stop`, `hard-kill`
- observed states: `authoring`, `initializing`, `awaiting_ack`, `ready`, `running`, `paused`, `stopping`, `stopped`, `dead`

# Completion Condition
<user-defined operational success condition>

# Stop Policy
Default stop mode: interrupt-first

# Reporting Contract
See `reporting.md`.

# Supporting Files
- `prestart.md`
- `graph.md`
- `delegation.md`
- `reporting.md`
- `scripts/README.md`

# Mermaid Control Graph
<top-level mermaid graph>
```

## `prestart.md`

Record:

- notifier preflight procedure
- participant preparation-mail procedure
- acknowledgement posture: `fire_and_proceed` or `require_ack`
- operator reply policy: `none` or `operator_mailbox`
- initialization state transitions: `initializing`, `awaiting_ack`, `ready`
- readiness barrier behavior when acknowledgement is required
- how the master trigger remains separate from the preparation wave

## `agents/<participant>.md`

Each participant brief should be standalone and should record:

- the participant role
- resources and tools available locally
- allowed delegation targets
- work-type-specific delegation patterns, when needed
- mailbox, reminder, receipt, or result obligations
- forbidden actions
- optional timeout-watch policy for that participant

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
- Do not leave participant preparation only in a shared upstream-aware matrix.
- Do not leave script behavior undocumented when scripts are part of the plan.
