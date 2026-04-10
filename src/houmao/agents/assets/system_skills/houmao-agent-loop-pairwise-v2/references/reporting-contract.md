# Reporting Contract

Use this reference when the authored plan or run charter needs to define what the master or operator should report for `peek`, completion, `stop`, or `hard-kill`.

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

## Hard-Kill Summary Fields

- final observed state when the participant set is quiesced or partially quiesced
- which participants accepted direct interrupt handling
- which participants still reported cleanup or liveness blockers
- notifier disable result for each participant
- reminder removal result for each participant
- unread counts drained and any residual unread blockers for each participant

## Guardrails

- Keep `peek` current and operational rather than historical by default.
- Keep observed states distinct from lifecycle actions such as `start`, `peek`, or `stop`.
- Keep `dead` as an observed condition, not an operator control verb.
- Keep completion and stop summaries tied to the authored completion and stop conditions.
- Keep `hard-kill` summaries participant-explicit rather than pretending the master reconciled the run normally.
