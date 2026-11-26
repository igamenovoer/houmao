# Create Intention

## Workflow

1. Confirm the inherited actor posture, `<loop-dir>` preconditions, and required inputs, loading only the `## Read First` references.
2. Execute `## Actions` within this command's side-effect boundary.
3. Return the structured report (`## Report`) and stop on any unresolved blocker.

If the request does not map cleanly to these steps, use the native planning tool to build a step-by-step plan from this procedure, its owning skill constraints, and the user request, then execute the plan.

## Read First

- [../../references/scaffold-surface.md](../../references/scaffold-surface.md)
- [../../references/system-input-questions.md](../../references/system-input-questions.md)

## Inputs

Require:
- `<loop-dir>`

## Actions

1. Run the packaged scaffold generator with `intention-create`.
2. Keep `intention/README.md` and `intention/loop-overview.md` editable and freeform.
3. Add extra intention Markdown only when it helps organize user-provided source material.
4. Do not inspect project context unless the user asks.
5. Do not generate `execplan/`.

## Report

List created or skipped intention files.
