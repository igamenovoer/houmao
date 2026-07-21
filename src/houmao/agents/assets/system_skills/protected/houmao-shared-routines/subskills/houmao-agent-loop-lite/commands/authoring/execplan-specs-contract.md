# Execplan Specs Contract

## Read First

- `../reference/markdown-contract-defaults.md`
- `../reference/markdown-template-events.md`
- `../reference/direct-sqlite-state.md`
- `../reference/platform-boundaries.md`

## Inputs

Require:
- `<loop-dir>`
- `execplan/specs/process.md`

## Outputs

Generate or update Markdown contracts:
- `execplan/specs/objective.md`
- `execplan/specs/organization.md`
- `execplan/specs/communication.md`
- `execplan/specs/templates/*.md`
- `execplan/specs/state/README.md`
- `execplan/specs/state/schema.sql` when durable state is needed
- optional `workspace.md` and `run-artifacts.md`

## Actions

1. Derive contracts from process and intention source.
2. Define typed Markdown templates with `Loop-Template-Type` and `Loop-Template-Version`.
3. Define direct SQLite state tables when stable bookkeeping is needed.
4. Route workspace requirements to `<public-entrypoint>->houmao-shared-routines->utils-workspace-mgr` when standard workspace setup applies.
5. Keep optional concerns absent when the loop does not need them.

## Constraints

- Do not create TOML registries, JSON schemas, Jinja2 renderers, or harness commands.
