# Execplan Skills

## Workflow

1. **Validate invocation context**. Preserve the actor posture, selected target, operation intent, and predecessor evidence supplied by the owning skill.
2. **Resolve required inputs**. Recover explicit values from current context and stop or ask when a required value remains missing.
3. **Execute the detailed procedure below**. Follow its ordering, gates, side-effect boundary, owned references, and output contract.
4. **Validate and report**. Return changed or inspected artifacts, evidence, blockers, and the command-specific stop condition.

If the request does not map cleanly to these steps, use the native planning tool to build a step-by-step plan from this command procedure, its owning skill constraints, available references, and the user request, then execute the plan.

## Read First

- `../reference/markdown-contract-defaults.md`
- `../reference/markdown-template-events.md`
- `../reference/direct-sqlite-state.md`
- `../reference/runtime-mail-model.md`
- `../reference/platform-boundaries.md`

## Inputs

Require:
- `<loop-dir>`
- generated process, communication, state, and participant Markdown contracts

## Outputs

Generate or update flat skill directories under `execplan/skills/`.

## Actions

1. Always generate one shared guidance skill for read order, placeholder replacement, Houmao envelope boundaries, direct SQLite usage, and bounded turns.
2. For every required `Loop-Template-Type`, generate at least one receiver skill whose trigger names that exact type.
3. Generate sender, tick, role, and operator-control skills only when the process requires them.
4. Require sender skills to block unresolved `<placeholder` tokens before sending.
5. Route platform mechanics to maintained Houmao skills.

## Constraints

- Do not create nested category directories under `execplan/skills/`.
- Do not generate harness-usage skills; lite has no generated harness.
