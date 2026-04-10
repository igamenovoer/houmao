# Reporting Contract

Use this reference when the authored plan or run charter needs to define what the master should report for `peek`, completion, or stop.

## Canonical Observed States

- `authoring`
- `initializing`
- `awaiting_ack`
- `ready`
- `running`
- `paused`
- `stopping`
- `stopped`
- `dead`

Treat these state names as observations, not operator actions.

## Peek Fields

- observed state
- active pairwise edges or owned child loops
- completed results so far
- blockers or late conditions
- next planned actions
- completion-condition posture
- stop-condition posture when relevant
- timeout-watch or wakeup-control posture, when used

## Completion Fields

- final synthesized result
- why the completion condition is satisfied
- final observed state when useful
- relevant plan or run references when needed

## Stop Summary Fields

- observed state at stop completion
- stop mode used
- which edges completed before stop
- which active edges were interrupted or drained
- preserved partial results
- remaining unfinished work or known blockers

## Guardrails

- Keep `peek` current and operational rather than historical by default.
- Keep observed states distinct from lifecycle actions such as `start`, `peek`, or `stop`.
- Keep `dead` as an observed condition, not an operator control verb.
- Keep completion and stop summaries tied to the authored completion and stop conditions.
