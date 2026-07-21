# Execplan Fast Forward

## Workflow

1. **Validate invocation context**. Preserve the actor posture, selected target, operation intent, and predecessor evidence supplied by the owning skill.
2. **Resolve required inputs**. Recover explicit values from current context and stop or ask when a required value remains missing.
3. **Execute the detailed procedure below**. Follow its ordering, gates, side-effect boundary, owned references, and output contract.
4. **Validate and report**. Return changed or inspected artifacts, evidence, blockers, and the command-specific stop condition.

If the request does not map cleanly to these steps, use the native planning tool to build a step-by-step plan from this command procedure, its owning skill constraints, available references, and the user request, then execute the plan.

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
