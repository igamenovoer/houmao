# Resume

## Workflow

1. Confirm the inherited actor posture, `<loop-dir>` preconditions, and required inputs, loading only the `## Read First` references.
2. Execute `## Actions` within this command's side-effect boundary.
3. Return the structured report (`## Report`) and stop on any unresolved blocker.

If the request does not map cleanly to these steps, use the native planning tool to build a step-by-step plan from this procedure, its owning skill constraints, and the user request, then execute the plan.

## Read First

- [../../references/direct-sqlite-state.md](../../references/direct-sqlite-state.md)
- [../../references/platform-boundaries.md](../../references/platform-boundaries.md)

## Actions

1. Confirm the generated loop is paused or manually held.
2. Record resume intent according to `execplan/specs/state/README.md`.
3. Route notifier or prompt posture restoration through maintained gateway or messaging surfaces.
4. Report resumed posture and next expected trigger.

## Constraints

- Do not invent work that the generated process does not select.
