# Reporting Contract

Use this reference when the authored plan or run charter needs to define what the master or operator should report for `peek`, `recover_and_continue`, completion, `stop`, or `hard-kill`.

## Canonical Observed States

- `authoring`
- `initializing`
- `awaiting_ack`
- `ready`
- `running`
- `paused`
- `recovering`
- `recovered_ready`
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

## Recovery Summary Fields

- `run_id`
- `recovery_epoch`
- current observed state during restart recovery
- participant rebindings, including any operator-confirmed mapping
- durable pages or memo slots refreshed
- declarative wakeup posture restored
- unresolved blockers or follow-up actions

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
- open inbox counts drained and any residual open-mail blockers for each participant

## Guardrails

- Keep `peek` current and operational rather than historical by default.
- Keep `peek` unintrusive: do not send prompts, email job messages, acknowledgements, or keepalive signals merely to produce a peek report.
- Keep observed states distinct from lifecycle actions such as `start`, `peek`, or `stop`.
- Keep `dead` as an observed condition, not an operator control verb.
- Keep recovery summaries explicit about what was rebound, refreshed, restored, or still blocked before the run returns to `running`.
- Keep completion and stop summaries tied to the authored completion and stop conditions.
- Keep `hard-kill` summaries participant-explicit rather than pretending the master reconciled the run normally.
