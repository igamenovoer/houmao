# Pause

## Read First

- `../reference/direct-sqlite-state.md`
- `../reference/platform-boundaries.md`

## Actions

1. Confirm the generated loop defines pause control.
2. Record pause intent in direct SQLite state or operator notes as defined by `execplan/specs/state/README.md`.
3. Route notifier posture changes through `<public-entrypoint>->houmao-shared-routines->agent-gateway`.
4. Report paused posture and remaining live-agent state.

## Constraints

- Do not stop live agents unless the generated loop or operator explicitly asks.
