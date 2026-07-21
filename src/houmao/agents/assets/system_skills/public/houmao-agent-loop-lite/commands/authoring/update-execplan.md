# Update Execplan

## Workflow

1. **Validate invocation context**. Preserve the actor posture, selected target, operation intent, and predecessor evidence supplied by the owning skill.
2. **Resolve required inputs**. Recover explicit values from current context and stop or ask when a required value remains missing.
3. **Execute the detailed procedure below**. Follow its ordering, gates, side-effect boundary, owned references, and output contract.
4. **Validate and report**. Return changed or inspected artifacts, evidence, blockers, and the command-specific stop condition.

If the request does not map cleanly to these steps, use the native planning tool to build a step-by-step plan from this command procedure, its owning skill constraints, available references, and the user request, then execute the plan.

## Read First

- `../reference/markdown-contract-defaults.md`
- `../reference/system-input-questions.md`

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
