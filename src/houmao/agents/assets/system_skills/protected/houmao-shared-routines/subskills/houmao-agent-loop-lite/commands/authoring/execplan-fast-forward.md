# Execplan Fast Forward

## Read First

- `../reference/scaffold-surface.md`
- `../reference/markdown-contract-defaults.md`
- `../reference/markdown-template-events.md`
- `../reference/direct-sqlite-state.md`
- `../reference/runtime-mail-model.md`
- `../reference/platform-boundaries.md`
- `../reference/system-input-questions.md`

## Inputs

Require:
- `<loop-dir>`
- `<loop-dir>/intention/README.md`
- `<loop-dir>/intention/loop-overview.md`

## Actions

1. Run the packaged scaffold generator with `execplan-shell`.
2. Generate lite artifacts in order:

```text
execplan-specs-process
  -> execplan-specs-contract
      -> execplan-skills
          -> execplan-agent-bindings
              -> execplan-finalize
```

3. Preserve unresolved decisions as `UNRESOLVED - <reason>`.
4. Request `validate-execplan` before reporting completion.

## Constraints

- Do not run an `execplan-harness` stage.
- Do not create JSON schemas, Jinja2 renderers, `execplan/harness/`, or `execplan/docs/`.
- Do not perform platform launch, mailbox delivery, gateway, lifecycle, or workspace side effects.
