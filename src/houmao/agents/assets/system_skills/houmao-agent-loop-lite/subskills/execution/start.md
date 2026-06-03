# Start

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
