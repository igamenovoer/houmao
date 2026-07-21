# Validate Execplan

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
