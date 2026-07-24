# Execplan Agent Bindings

## Workflow

1. **Validate invocation context**. Preserve the actor posture, selected target, operation intent, and predecessor evidence supplied by the owning skill.
2. **Resolve required inputs**. Recover explicit values from current context and stop or ask when a required value remains missing.
3. **Execute the detailed procedure below**. Follow its ordering, gates, side-effect boundary, owned references, and output contract.
4. **Validate and report**. Return changed or inspected artifacts, evidence, blockers, and the command-specific stop condition.

If the request does not map cleanly to these steps, use the native planning tool to build a step-by-step plan from this command procedure, its owning skill constraints, available references, and the user request, then execute the plan.

## Read First

- `../reference/markdown-contract-defaults.md`
- `../reference/runtime-mail-model.md`
- `../reference/platform-boundaries.md`

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
