# Init

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
