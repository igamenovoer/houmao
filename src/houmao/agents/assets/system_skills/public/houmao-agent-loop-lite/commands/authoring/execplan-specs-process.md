# Execplan Specs Process

## Workflow

1. Confirm the inherited actor posture, `<loop-dir>` preconditions, and required inputs, loading only the `## Read First` references.
2. Execute `## Actions` within this command's side-effect boundary.
3. Return the structured report (`## Report`) and stop on any unresolved blocker.

If the request does not map cleanly to these steps, use the native planning tool to build a step-by-step plan from this procedure, its owning skill constraints, and the user request, then execute the plan.

## Read First

- [../../references/markdown-contract-defaults.md](../../references/markdown-contract-defaults.md)
- [../../references/runtime-mail-model.md](../../references/runtime-mail-model.md)

## Inputs

Require:
- `<loop-dir>`
- current intention source

## Outputs

Generate or update:
- `execplan/specs/process.md`

## Actions

1. Describe phases, events, handoffs, tick responsibilities, terminal posture, and recovery posture.
2. Include concise pseudocode or Mermaid when it clarifies the loop.
3. Name expected communication template families without finalizing renderer or schema machinery.
4. Identify state facts needed by direct SQLite bookkeeping.
5. Mark unresolved process choices explicitly.

## Constraints

- Do not generate contracts, skills, agent bindings, or runtime side effects from this page.
