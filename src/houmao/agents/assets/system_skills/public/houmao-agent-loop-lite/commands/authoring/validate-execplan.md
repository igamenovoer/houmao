# Validate Execplan

## Workflow

1. **Validate invocation context**. Preserve the actor posture, selected target, operation intent, and predecessor evidence supplied by the owning skill.
2. **Resolve required inputs**. Recover explicit values from current context and stop or ask when a required value remains missing.
3. **Execute the detailed procedure below**. Follow its ordering, gates, side-effect boundary, owned references, and output contract.
4. **Validate and report**. Return changed or inspected artifacts, evidence, blockers, and the command-specific stop condition.

If the request does not map cleanly to these steps, use the native planning tool to build a step-by-step plan from this command procedure, its owning skill constraints, available references, and the user request, then execute the plan.

## Read First

- `../reference/markdown-contract-defaults.md`
- `../reference/markdown-template-events.md`
- `../reference/direct-sqlite-state.md`
- `../reference/runtime-mail-model.md`
- `../reference/platform-boundaries.md`

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
