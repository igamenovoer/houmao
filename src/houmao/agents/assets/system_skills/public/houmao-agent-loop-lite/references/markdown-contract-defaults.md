# Markdown Contract Defaults

## Shape

Default lite execplans use:

```text
execplan/
  README.md
  manifest.md
  specs/
    README.md
    objective.md
    organization.md
    process.md
    communication.md
    templates/
    state/
      README.md
      schema.sql
  skills/
    README.md
  agents/
    README.md
    bindings.md
```

Optional files appear only when selected by the loop process:
- `specs/workspace.md`
- `specs/run-artifacts.md`
- `specs/state/seed.sql`
- `specs/state/queries.md`
- notifier prompts
- concrete profile definitions
- tick or operator-control skills

## Rules

- Use Markdown as the authority for manifest, objective, organization, process, communication, generated skill index, and agent bindings.
- Prefer headings, tables, and short bullet lists.
- Mark missing required decisions as `UNRESOLVED - <reason>`.
- Do not create parallel TOML contract registries for lite.
- Do not create `execplan/harness/` or `execplan/docs/`.
