# Init

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
