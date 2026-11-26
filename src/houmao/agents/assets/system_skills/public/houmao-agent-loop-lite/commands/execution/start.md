# Start

## Workflow

1. Confirm the inherited actor posture, `<loop-dir>` preconditions, and required inputs, loading only the `## Read First` references.
2. Execute `## Actions` within this command's side-effect boundary.
3. Return the structured report (`## Report`) and stop on any unresolved blocker.

If the request does not map cleanly to these steps, use the native planning tool to build a step-by-step plan from this procedure, its owning skill constraints, and the user request, then execute the plan.

## Read First

- [../../references/direct-sqlite-state.md](../../references/direct-sqlite-state.md)
- [../../references/markdown-template-events.md](../../references/markdown-template-events.md)
- [../../references/runtime-mail-model.md](../../references/runtime-mail-model.md)
- [../../references/platform-boundaries.md](../../references/platform-boundaries.md)

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
