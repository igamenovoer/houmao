# Update Execplan

## Workflow

1. Confirm the inherited actor posture, `<loop-dir>` preconditions, and required inputs, loading only the `## Read First` references.
2. Execute `## Actions` within this command's side-effect boundary.
3. Return the structured report (`## Report`) and stop on any unresolved blocker.

If the request does not map cleanly to these steps, use the native planning tool to build a step-by-step plan from this procedure, its owning skill constraints, and the user request, then execute the plan.

## Read First

- [../../references/markdown-contract-defaults.md](../../references/markdown-contract-defaults.md)
- [../../references/system-input-questions.md](../../references/system-input-questions.md)

## Inputs

Require:
- `<loop-dir>`
- changed intention source or accepted clarification decision

## Actions

1. Identify the smallest affected stage.
2. Regenerate downstream lite stages in dependency order.
3. Preserve stable participant, template, skill, and agent identities when still valid.
4. Mark stale generated files or remove them when the concern is no longer selected.
5. Run or request `validate-execplan`.

## Constraints

- Do not change live agents or runtime state.
- Do not add pro-only generated layers while updating lite material.
