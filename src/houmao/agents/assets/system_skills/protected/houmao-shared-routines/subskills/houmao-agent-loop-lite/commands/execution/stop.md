# Stop

## Read First

- `../reference/direct-sqlite-state.md`
- `../reference/platform-boundaries.md`

## Actions

1. Confirm the target run and stop authority.
2. Record stop intent according to generated state guidance.
3. Route live-agent lifecycle actions through `<public-entrypoint>->houmao-shared-routines->agent-instance` only when stop policy requires them.
4. Route notifier disablement through `<public-entrypoint>->houmao-shared-routines->agent-gateway` when needed.
5. Report stopped, partially stopped, or blocked posture.

## Constraints

- Do not delete run artifacts or SQLite state as part of normal stop.
