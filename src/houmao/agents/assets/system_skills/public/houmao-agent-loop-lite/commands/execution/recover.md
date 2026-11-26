# Recover

## Workflow

1. Confirm the inherited actor posture, `<loop-dir>` preconditions, and required inputs, loading only the `## Read First` references.
2. Execute `## Actions` within this command's side-effect boundary.
3. Return the structured report (`## Report`) and stop on any unresolved blocker.

If the request does not map cleanly to these steps, use the native planning tool to build a step-by-step plan from this procedure, its owning skill constraints, and the user request, then execute the plan.

## Read First

- [../../references/direct-sqlite-state.md](../../references/direct-sqlite-state.md)
- [../../references/runtime-mail-model.md](../../references/runtime-mail-model.md)
- [../../references/platform-boundaries.md](../../references/platform-boundaries.md)

## Actions

1. Read manifest, run artifacts, SQLite state, mailbox refs, and live-agent posture.
2. Identify the last durable event and incomplete handoff.
3. Use generated recovery instructions from Markdown contracts and state README.
4. Route live-agent, gateway, mailbox, and inspection work to maintained skills.
5. Record recovery decisions in SQLite or operator notes when the generated contract requires it.

## Constraints

- Do not rewrite history to hide partial sends or failed actions.
- Do not call a generated harness.
