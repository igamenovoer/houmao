# Execplan Finalize

## Read First

- `../reference/markdown-contract-defaults.md`

## Inputs

Require:
- `<loop-dir>`
- current generated lite execplan artifacts

## Actions

1. Update `execplan/README.md` and `execplan/manifest.md`.
2. Record generated artifact inventory, omissions, unresolved items, and validation notes in concise Markdown.
3. Ensure README files use only `Purpose` and `Contents` unless a file is itself the contract.
4. Ensure optional absent files are intentional, not silent omissions.

## Constraints

- Do not create `execplan/docs/`.
- Do not duplicate contract authority into final notes.
