# Validate Execplan

## Workflow

1. Confirm the inherited actor posture, `<loop-dir>` preconditions, and required inputs, loading only the `## Read First` references.
2. Execute `## Checks` within this command's side-effect boundary.
3. Return the structured report (`## Report`) and stop on any unresolved blocker.

If the request does not map cleanly to these steps, use the native planning tool to build a step-by-step plan from this procedure, its owning skill constraints, and the user request, then execute the plan.

## Read First

- [../../references/markdown-contract-defaults.md](../../references/markdown-contract-defaults.md)
- [../../references/markdown-template-events.md](../../references/markdown-template-events.md)
- [../../references/direct-sqlite-state.md](../../references/direct-sqlite-state.md)
- [../../references/runtime-mail-model.md](../../references/runtime-mail-model.md)
- [../../references/platform-boundaries.md](../../references/platform-boundaries.md)

## Checks

- Required root spine: `intention/`, `execplan/`, and `runs/`.
- Required Markdown contracts exist for selected concerns.
- At least one template exists under `execplan/specs/templates/`.
- Each template starts with `Loop-Template-Type` and `Loop-Template-Version`.
- Generated shared guidance skill exists.
- Each required template type has at least one generated receiver skill naming it.
- Generated sender guidance blocks unresolved `<placeholder` tokens before send.
- `execplan/specs/state/schema.sql` parses with SQLite when durable state is required.
- Generated skills route platform mechanics to maintained Houmao skills.
- `execplan/harness/`, `execplan/docs/`, JSON schema files, and Jinja2 renderer files are absent.

## Report

Report ready, ready with warnings, or blocked; include blockers, warnings, and generated package omissions.

## Constraints

- Do not treat missing optional workspace or run-artifact files as failures.
- Do not require pro-only TOML registries, schemas, renderers, or harness command registries.
