# Execplan Agent Bindings

## Workflow

1. Confirm the inherited actor posture, `<loop-dir>` preconditions, and required inputs, loading only the `## Read First` references.
2. Execute `## Actions` within this command's side-effect boundary.
3. Return the structured report (`## Report`) and stop on any unresolved blocker.

If the request does not map cleanly to these steps, use the native planning tool to build a step-by-step plan from this procedure, its owning skill constraints, and the user request, then execute the plan.

## Read First

- [../../references/markdown-contract-defaults.md](../../references/markdown-contract-defaults.md)
- [../../references/runtime-mail-model.md](../../references/runtime-mail-model.md)
- [../../references/platform-boundaries.md](../../references/platform-boundaries.md)

## Inputs

Require:
- `<loop-dir>`
- generated participant or organization contract
- generated skills

## Outputs

Generate or update:
- `execplan/agents/bindings.md`
- optional profile source material
- optional notifier prompts

## Actions

1. Map participant roles or instances to concrete Houmao agent ids or profile names.
2. Record generated skill groups for each participant.
3. Record selected tool, credential posture, launch mode, memo posture, workdir or workspace policy, and notifier prompt path when known.
4. Record unknown launch facts as `UNRESOLVED - <reason>` for `prepare-agents`.
5. Leave actual profile creation, launch, mailbox setup, gateway setup, and workspace creation to execution pages.

## Constraints

- Do not enumerate ordinary Houmao system skills as generated skill requirements.
- Do not install another participant's generated skills into the wrong binding.
