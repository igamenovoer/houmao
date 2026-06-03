# Execplan Specs Process

## Read First

- `../reference/markdown-contract-defaults.md`
- `../reference/runtime-mail-model.md`

## Inputs

Require:
- `<loop-dir>`
- current intention source

## Outputs

Generate or update:
- `execplan/specs/process.md`

## Actions

1. Describe phases, events, handoffs, tick responsibilities, terminal posture, and recovery posture.
2. Include concise pseudocode or Mermaid when it clarifies the loop.
3. Name expected communication template families without finalizing renderer or schema machinery.
4. Identify state facts needed by direct SQLite bookkeeping.
5. Mark unresolved process choices explicitly.

## Constraints

- Do not generate contracts, skills, agent bindings, or runtime side effects from this page.
