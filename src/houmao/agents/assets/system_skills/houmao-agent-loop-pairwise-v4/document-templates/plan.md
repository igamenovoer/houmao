# V4 Plan Document Template

Fill this template as `<plan-output-dir>/plan.md`. Keep headings in this order. If a required value is unknown, write `UNRESOLVED - <reason>` instead of deleting the field.

## Required Policy Verbs

Preserve policy-bearing verbs from source material when they define gates, required actions, forbidden actions, evidence, output format, or dispatch behavior: `ALWAYS`, `NEVER`, `CHECK`, `RUN`, `READ`, `ANALYZE`, `DECIDE`, `OUTPUT`, `UPDATE`, `COMMIT`, `MERGE`, `DISPATCH`.

```md
# Objective
<what the run is trying to accomplish>

# Master
<designated master and why this participant owns final coordination>

# Participants
| Agent | Role | Delegates To | Result Returns To |
| --- | --- | --- | --- |
| <agent> | <role> | <none or named children> | <operator or immediate driver> |

# Source Contract Summary
## Referenced Sources
- `<source path or explicit user instruction>`: <why it governs this plan>

## Preserved Policy Verbs
- `<VERB>`: <source phrase or normalized rule>

## Source Constraints Carried Forward
| ID | Verb | Scope | Rule | Projected to |
| --- | --- | --- | --- | --- |
| SC-001 | `<VERB>` | `<central | role | reporting | bookkeeping | routing>` | `<source rule>` | `<plan.md section or support file>` |

## Unresolved Source Inputs
- `UNRESOLVED - <reason>`

# Workspace Contract
<workspace contract mode, allowed write surfaces, shared writable surfaces, bookkeeping paths, read-only paths, ad hoc worktree posture, and runtime-owned recovery boundary>

# Topology
<descendant relationships that identify delegating participants and leaves>

# Delegation Policy
<normalized delegation rules and forbidden delegation behavior>

# Prestart Procedure
<initialize readiness, packet validation, mailbox checks, notifier checks, memo materialization, and master trigger separation>

# Routing Packets
<root packet plus child packet inventory, exact forwarding rules, freshness marker, and mismatch handling>

# Lifecycle Vocabulary
- operator actions: `plan`, `initialize`, `start`, `peek`, `ping`, `pause`, `resume`, `recover_and_continue`, `stop`, `hard-kill`
- observed states: `authoring`, `initializing`, `ready`, `running`, `paused`, `recovering`, `recovered_ready`, `stopping`, `stopped`, `dead`

# Completion Condition
<user-defined operational success condition>

# Stop Policy
<default stop mode and any hard-kill posture>

# Reporting Contract
<peek, completion, recovery, stop, and hard-kill reporting expectations>

# Constraint Coverage Audit
See `constraint-coverage-audit.md`, or include the coverage table inline for single-file plans.

# Template Inventory
<reporting templates, bookkeeping templates, and which participants may instantiate or fill them>

# Supporting Files
<workspace, prestart, routing, graph, delegation, reporting, coverage audit, agent notes, templates, and scripts>

# Mermaid Control Graph
<top-level mermaid graph>
```
