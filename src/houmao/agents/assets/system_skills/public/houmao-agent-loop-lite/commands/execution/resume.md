# Resume

## Workflow

1. **Validate invocation context**. Preserve the actor posture, selected target, operation intent, and predecessor evidence supplied by the owning skill.
2. **Resolve required inputs**. Recover explicit values from current context and stop or ask when a required value remains missing.
3. **Execute the detailed procedure below**. Follow its ordering, gates, side-effect boundary, owned references, and output contract.
4. **Validate and report**. Return changed or inspected artifacts, evidence, blockers, and the command-specific stop condition.

If the request does not map cleanly to these steps, use the native planning tool to build a step-by-step plan from this command procedure, its owning skill constraints, available references, and the user request, then execute the plan.

## Read First

- `../reference/direct-sqlite-state.md`
- `../reference/platform-boundaries.md`

## Actions

1. Confirm the generated loop is paused or manually held.
2. Record resume intent according to `execplan/specs/state/README.md`.
3. Route notifier or prompt posture restoration through maintained gateway or messaging surfaces.
4. Report resumed posture and next expected trigger.

## Constraints

- Do not invent work that the generated process does not select.
