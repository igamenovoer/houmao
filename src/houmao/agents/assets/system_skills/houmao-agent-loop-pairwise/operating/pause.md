# Pause A Pairwise Loop Run

Use this page when the user wants to intentionally stall one running pairwise loop without terminating it.

## Workflow

1. Resolve the designated master and the target `run_id`.
2. Send one normalized pause request to the master through `houmao-agent-messaging`.
3. Tell the master what canonical `pause` means for this run:
   - stop opening new child loops
   - preserve current run state and already-returned partial results
   - suspend the run's wakeup mechanisms until a later `resume`
4. When the run depends on notifier- or reminder-driven wakeups, coordinate the pause through `houmao-agent-gateway` so those wakeup mechanisms stop advancing the run.
5. Treat the run as `paused` after pause handling is in effect.

## Pause Contract

- Canonical `pause` means suspension of the run's wakeup mechanisms.
- Disabling mail notifier alone is not sufficient when reminders or other wakeups can still advance the run.
- `pause` stalls the current run; it does not replace `stop`.

## Guardrails

- Do not treat `pause` as a synonym for muting notifications only.
- Do not discard partial results when pausing the run.
- Do not start a brand-new run when the user asked to pause an existing one.
