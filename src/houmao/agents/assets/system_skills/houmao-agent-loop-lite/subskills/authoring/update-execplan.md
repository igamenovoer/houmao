# Update Execplan

## Read First

- `../reference/markdown-contract-defaults.md`
- `../reference/system-input-questions.md`

## Inputs

Require:
- `<loop-dir>`
- changed intention source or accepted clarification decision

## Actions

1. Identify the smallest affected stage.
2. Regenerate downstream lite stages in dependency order.
3. Preserve stable participant, template, skill, and agent identities when still valid.
4. Mark stale generated files or remove them when the concern is no longer selected.
5. Run or request `validate-execplan`.

## Constraints

- Do not change live agents or runtime state.
- Do not add pro-only generated layers while updating lite material.
