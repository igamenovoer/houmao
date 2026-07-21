# Start

## Workflow

1. **Validate invocation context**. Preserve the actor posture, selected target, operation intent, and predecessor evidence supplied by the owning skill.
2. **Resolve required inputs**. Recover explicit values from current context and stop or ask when a required value remains missing.
3. **Execute the detailed procedure below**. Follow its ordering, gates, side-effect boundary, owned references, and output contract.
4. **Validate and report**. Return changed or inspected artifacts, evidence, blockers, and the command-specific stop condition.

If the request does not map cleanly to these steps, use the native planning tool to build a step-by-step plan from this command procedure, its owning skill constraints, available references, and the user request, then execute the plan.

## Read First

- `../reference/direct-sqlite-state.md`
- `../reference/markdown-template-events.md`
- `../reference/runtime-mail-model.md`
- `../reference/platform-boundaries.md`

## Inputs

Require:
- `<loop-dir>`
- current validation evidence
- launch-agent report or equivalent live-session facts
- target run id when required

## Actions

1. Confirm readiness and live-agent facts.
2. Create or select `runs/<run-id>/`.
3. Initialize `runs/<run-id>/state.sqlite3` from `execplan/specs/state/schema.sql` when needed.
4. Follow `execplan/specs/state/README.md` for any start-time seed or validation action.
5. Send the first trigger through maintained messaging or mailbox surfaces according to the generated process.
6. Confirm the next wakeup is notifier- or operator-prompt-driven.

## Constraints

- Do not launch agents.
- Do not call generated harness commands.
- Do not ask agents to keep a chat turn open while waiting for future mail or ticks.
