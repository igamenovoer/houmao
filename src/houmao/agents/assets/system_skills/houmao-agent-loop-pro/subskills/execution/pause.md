# Pause

## Read First

- MUST READ: `../reference/runtime-mail-model.md`
- `../reference/platform-boundaries.md`

## Preconditions

- Operator wants to pause normal loop scheduling, wakeup, or dispatch.
- The loop should remain intact.

## Inputs

Require:
- `<loop-dir>`
- run identity

## Actions

1. Validate the execplan enough to locate pause-capable surfaces.
2. Use generated operator-control guidance or harness `control pause` when the execplan defines a pause record or pause command.
3. Confirm whether the operator wants `pause` or `manual` mode; manual mode changes wakeup authority but is not pause.
4. Use `houmao-agent-messaging` for direct pause prompts when required.
5. Use `houmao-agent-gateway` for reminder or mail-notifier suspension when the loop relies on those wakeup paths.
6. Report what was paused, current execution mode when known, and what remains live.

## Constraints

- Do not stop agents unless the user asks to stop.
- Do not treat pause as recovery.
- Do not treat manual mode as pause.
- Do not delete mailbox, runtime, or generated execplan state.
