# Execplan Fast Forward

## Preconditions

- User wants generated execution material in one non-interactive pass.
- Current intention source exists.
- `execplan/` should be generated or regenerated from `intention/`.

## Inputs

Require:
- `<loop-dir>`
- `<loop-dir>/intention/README.md`
- `<loop-dir>/intention/loop-overview.md`

Read:
- relevant files under `<loop-dir>/intention/`
- accepted intention ADRs under `<loop-dir>/adrs/` when present
- existing `execplan/` only as generated material to replace, update, or preserve by stable identity

## Outputs

Generate all execplan artifacts in one command using the standard staged order:

```text
execplan-specs-process
  -> execplan-specs-contract
      -> execplan-harness
          -> execplan-skills
              -> execplan-agent-bindings
                  -> execplan-finalize
```

`execplan-fast-forward` is the explicit all-stages, non-interactive generation path.

## Actions

1. Confirm `<loop-dir>` and required intention files exist.
2. Use the packaged scaffold generator with the `execplan-shell` profile to create the standard `execplan/` directory shell and the provisional `manifest.toml` seed before emitting stage artifacts.
3. Treat the scaffold profile output as the authoritative starter shape for shell-owned directories and files.
4. Run every staged generation page in dependency order:
  - `execplan-specs-process`
  - `execplan-specs-contract`
  - `execplan-harness`
  - `execplan-skills`
  - `execplan-agent-bindings`
  - `execplan-finalize`
5. Use defaults from the skill when intention source is silent and the default is already defined.
6. Preserve unresolved assumptions as `UNRESOLVED - <reason>` entries in the affected generated artifact.
7. Do not stop for optional design questions when a documented default is sufficient.
8. Ask the user only for hard blockers that prevent coherent generation, such as a missing `<loop-dir>`, missing intention source, contradictory accepted decisions, or an execution state that must be paused before overwriting generated material.
9. Run or request `validate-execplan` before reporting completion.

## Constraints

- Do not perform platform launch, mailbox delivery, gateway, memory, lifecycle, or workspace creation side effects.
- Do not create `execplan/adrs/` just to explain routine defaults; reserve execplan-local ADRs for interactive `execplan-step-by-step` decisions or explicitly requested decision records.
- Do not ask a questionnaire before generation.
- Do not invent domain policy that is absent from intention source or documented defaults.
