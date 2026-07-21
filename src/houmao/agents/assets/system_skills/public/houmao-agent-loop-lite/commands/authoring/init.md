# Init

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

Optional:
- loop goal or initial intention;
- project root or project-context notes.

If `<loop-dir>` is missing, ask with `Required: <loop-dir>` and optional project context values.

## Actions

1. Run the packaged scaffold generator with `intention-init`.
2. Fill `intention/project-context.md` from explicit user context or lightweight nearby project inspection.
3. If the user provided loop intent, update `intention/loop-overview.md` with concise source notes.
4. Do not generate `execplan/`.

## Report

List created or skipped intention files and any unresolved project context.
