# Create Intention

## Workflow

1. **Validate invocation context**. Preserve the actor posture, selected target, operation intent, and predecessor evidence supplied by the owning skill.
2. **Resolve required inputs**. Recover explicit values from current context and stop or ask when a required value remains missing.
3. **Execute the detailed procedure below**. Follow its ordering, gates, side-effect boundary, owned references, and output contract.
4. **Validate and report**. Return changed or inspected artifacts, evidence, blockers, and the command-specific stop condition.

If the request does not map cleanly to these steps, use the native planning tool to build a step-by-step plan from this command procedure, its owning skill constraints, available references, and the user request, then execute the plan.

## Read First

- `../reference/scaffold-surface.md`
- `../reference/system-input-questions.md`

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
