# Execplan Skills

## Workflow

1. Confirm the inherited actor posture, `<loop-dir>` preconditions, and required inputs, loading only the `## Read First` references.
2. Execute `## Actions` within this command's side-effect boundary.
3. Return the structured report (`## Report`) and stop on any unresolved blocker.

If the request does not map cleanly to these steps, use the native planning tool to build a step-by-step plan from this procedure, its owning skill constraints, and the user request, then execute the plan.

## Read First

- [../../references/markdown-contract-defaults.md](../../references/markdown-contract-defaults.md)
- [../../references/markdown-template-events.md](../../references/markdown-template-events.md)
- [../../references/direct-sqlite-state.md](../../references/direct-sqlite-state.md)
- [../../references/runtime-mail-model.md](../../references/runtime-mail-model.md)
- [../../references/platform-boundaries.md](../../references/platform-boundaries.md)

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
