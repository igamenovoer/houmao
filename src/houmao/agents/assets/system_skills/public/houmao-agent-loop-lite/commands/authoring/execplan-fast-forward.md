# Execplan Fast Forward

## Workflow

1. Confirm the inherited actor posture, `<loop-dir>` preconditions, and required inputs, loading only the `## Read First` references.
2. Execute `## Actions` within this command's side-effect boundary.
3. Return the structured report (`## Report`) and stop on any unresolved blocker.

If the request does not map cleanly to these steps, use the native planning tool to build a step-by-step plan from this procedure, its owning skill constraints, and the user request, then execute the plan.

## Read First

- [../../references/scaffold-surface.md](../../references/scaffold-surface.md)
- [../../references/markdown-contract-defaults.md](../../references/markdown-contract-defaults.md)
- [../../references/markdown-template-events.md](../../references/markdown-template-events.md)
- [../../references/direct-sqlite-state.md](../../references/direct-sqlite-state.md)
- [../../references/runtime-mail-model.md](../../references/runtime-mail-model.md)
- [../../references/platform-boundaries.md](../../references/platform-boundaries.md)
- [../../references/system-input-questions.md](../../references/system-input-questions.md)

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
