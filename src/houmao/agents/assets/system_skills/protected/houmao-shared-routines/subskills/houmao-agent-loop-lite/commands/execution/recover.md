# Recover

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
