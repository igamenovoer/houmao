# Stop Modes

Use this reference when the user wants to stop an active run or when the authored plan needs to record the default stop posture.

## Supported Modes

- `interrupt-first`
  - Default for this skill
  - The root owner stops opening new components, interrupts active downstream pairwise or relay work, preserves partial results already returned, and summarizes interrupted state.
- `graceful`
  - Only use when the user explicitly requests graceful termination
  - The root owner stops creating new components and drains the run according to the requested graceful posture.

## Rules

- Default to `interrupt-first`.
- Say the chosen stop mode explicitly in the authored plan and the stop request.
- Keep graceful stop opt-in rather than implicit.
- Apply the chosen mode to the typed component graph, not to an unstructured worker cycle.
