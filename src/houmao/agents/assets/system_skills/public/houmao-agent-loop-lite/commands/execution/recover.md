# Recover

## Workflow

1. **Validate invocation context**. Preserve the actor posture, selected target, operation intent, and predecessor evidence supplied by the owning skill.
2. **Resolve required inputs**. Recover explicit values from current context and stop or ask when a required value remains missing.
3. **Execute the detailed procedure below**. Follow its ordering, gates, side-effect boundary, owned references, and output contract.
4. **Validate and report**. Return changed or inspected artifacts, evidence, blockers, and the command-specific stop condition.

If the request does not map cleanly to these steps, use the native planning tool to build a step-by-step plan from this command procedure, its owning skill constraints, available references, and the user request, then execute the plan.

## Read First

- `../reference/direct-sqlite-state.md`
- `../reference/runtime-mail-model.md`
- `../reference/platform-boundaries.md`

## Actions

1. Read manifest, run artifacts, SQLite state, mailbox refs, and live-agent posture.
2. Identify the last durable event and incomplete handoff.
3. Use generated recovery instructions from Markdown contracts and state README.
4. Route live-agent, gateway, mailbox, and inspection work to maintained skills.
5. Record recovery decisions in SQLite or operator notes when the generated contract requires it.

## Constraints

- Do not rewrite history to hide partial sends or failed actions.
- Do not call a generated harness.
