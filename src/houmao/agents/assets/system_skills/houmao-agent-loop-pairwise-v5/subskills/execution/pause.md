# Pause

## Preconditions

- Operator wants to pause normal loop scheduling, wakeup, or dispatch.
- The loop should remain intact.

## Inputs

Require:
- `<loop-dir>`
- run identity

## Actions

1. Validate the execplan enough to locate pause-capable surfaces.
2. Use generated harness or generated operator skill guidance when the execplan defines a pause record or pause command.
3. Use `houmao-agent-messaging` for direct pause prompts when required.
4. Use `houmao-agent-gateway` for reminder or mail-notifier suspension when the loop relies on those wakeup paths.
5. Report what was paused and what remains live.

## Constraints

- Do not stop agents unless the user asks to stop.
- Do not treat pause as recovery.
- Do not delete mailbox, runtime, or generated execplan state.
