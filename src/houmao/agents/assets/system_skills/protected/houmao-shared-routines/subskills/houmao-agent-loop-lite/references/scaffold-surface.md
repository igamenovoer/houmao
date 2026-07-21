# Scaffold Surface

## Contract

- Use `scripts/scaffold.py` for scaffold-owned starter files.
- Use `assets/scaffolds/` as the template authority.
- Keep operation pages focused on when to scaffold, not on full starter file bodies.
- Lite scaffold profiles must not create `execplan/harness/`, `execplan/docs/`, JSON schema directories, or Jinja2 renderer directories.

## Profiles

- `intention-create`: create `intention/README.md` and `intention/loop-overview.md`.
- `intention-init`: create the intention files plus `intention/project-context.md`.
- `execplan-shell`: create the Markdown/direct-SQL `execplan/` shell.

## Rules

- Preserve user edits when a file already exists; report skipped files.
- Treat `intention/` as editable source and `execplan/` as generated material.
- Use placeholders only where the next authoring stage is expected to fill values.
