# Stop Modes

Use this reference when the user wants to stop an active run or when the authored plan needs to record the default stop posture.

## Supported Modes

- `interrupt-first`
  - Default for this skill
  - The master stops opening new work, interrupts active downstream work, preserves partial results already returned, and summarizes interrupted state.
- `graceful`
  - Only use when the user explicitly requests graceful termination
  - The master stops creating new work and drains the run according to the requested graceful posture

## Rules

- Default to `interrupt-first`.
- Say the chosen stop mode explicitly in the authored plan and the stop request.
- Keep graceful stop opt-in rather than implicit.
- Treat `hard-kill` as a separate operator action, not as another stop mode.
