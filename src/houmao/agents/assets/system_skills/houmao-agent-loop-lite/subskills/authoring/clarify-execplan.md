# Clarify Execplan

## Read First

- `../reference/markdown-contract-defaults.md`
- `../reference/markdown-template-events.md`
- `../reference/direct-sqlite-state.md`
- `../reference/runtime-mail-model.md`
- `../reference/platform-boundaries.md`

## Inputs

Require:
- `<loop-dir>`
- generated lite `execplan/` material

## Actions

1. Read generated Markdown contracts, templates, state README/schema, generated skills, and agent bindings.
2. Identify implementation-level ambiguity or contradiction.
3. Ask one high-impact question at a time; prefer questions that unblock validation or execution readiness.
4. Update affected generated Markdown files after accepted answers.
5. If the ambiguity belongs to user intent, send the operator back to `clarify-intent` or intention edits.

## Constraints

- Do not introduce JSON schemas, Jinja2, harness commands, or generated docs.
- Do not patch around unresolved intent by inventing hidden policy.
