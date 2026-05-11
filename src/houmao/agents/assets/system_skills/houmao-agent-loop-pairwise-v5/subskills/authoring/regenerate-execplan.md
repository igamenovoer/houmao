# Regenerate Execplan

Use this page when intention source changed and generated `execplan/` needs to be rebuilt.

## Inputs

Require:
- `<loop-dir>`
- current `<loop-dir>/intention/`
- existing or target `<loop-dir>/execplan/`

## Procedure

1. Read current intention files.
2. Check whether a loop run is active or in an uncertain execution state.
3. If execution is active or uncertain, pause and ask the user whether to stop or recover before regeneration.
4. Regenerate `execplan/` from intention source.
5. Preserve stable generated names where the meaning is unchanged.
6. Assign new identifiers or mark migration needs where generated meaning changes incompatibly.
7. Run `validate-execplan`.

## Boundaries

- Do not silently live-migrate active agents onto regenerated material.
- Do not preserve generated files merely because a user hand-edited `execplan/`; intention is the source.
- Do not require ADR files.
- Do not introduce domain policy that is absent from intention source.
