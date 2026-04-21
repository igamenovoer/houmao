# Hard-Kill A Pairwise Loop Run

Use this page when the user wants an emergency operator override that forcefully halts one accepted pairwise loop and clears participant wakeups or open mailbox backlog.

## Workflow

1. Resolve the target `run_id` plus the full currently known participant set:
   - the designated master
   - every named participant in the accepted plan
   - any additional live participant that current run inspection already surfaced explicitly
2. Treat `hard-kill` as participant-wide direct intervention, not as canonical master-owned `stop`.
3. Send a direct interrupt to every currently known participant through `houmao-agent-messaging`.
4. For every participant with a live gateway, disable gateway mail-notifier polling through `houmao-agent-gateway`.
5. For every participant with a live gateway reminder set, remove every live reminder through `houmao-agent-gateway`:
   - list the current reminder ids
   - delete each reminder id explicitly
   - do not leave paused reminders behind
6. For every participant mailbox, drain open inbox work through `houmao-agent-email-comms`:
   - list open inbox messages
   - archive every open `message_ref`
   - repeat until the open inbox snapshot is empty or an exact blocker is returned
   - do this regardless of whether the mail is related to the loop
7. Report a participant-by-participant hard-kill summary:
   - interrupt result
   - notifier disabled, unsupported, or blocked
   - reminder cleanup result
   - open counts drained or residual open-mail blockers
8. Mark the runtime-owned recovery record under `<runtime-root>/loop-runs/pairwise-v2/<run_id>/record.json` terminal and append a hard-kill event to `events.jsonl`.
9. Treat the run as terminal after `hard-kill`. If later human-readable reconciliation is still wanted, document it separately instead of waiting for canonical `stop` handling.

## Hard-Kill Contract

- `hard-kill` is an emergency operator override.
- `hard-kill` fans out directly to the master and every other currently known participant.
- `hard-kill` disables mail-notifier polling and removes live reminders instead of merely pausing them.
- `hard-kill` archives every open inbox message for each participant, even when that mail is unrelated to the current loop.
- `hard-kill` is distinct from canonical `stop`, which still asks the master to reconcile partial results and unfinished work.
- `hard-kill` marks the recovery record terminal, so ordinary `recover_and_continue` should reject that run.

## Guardrails

- Do not collapse `hard-kill` into canonical `stop`.
- Do not interrupt only the master and assume the rest of the participant set will quiesce on its own.
- Do not leave paused reminders in place after `hard-kill`; remove them.
- Do not preserve unrelated open mail; `hard-kill` intentionally clears the entire open inbox snapshot for each participant.
- Do not claim a clean final state when notifier shutdown, reminder cleanup, or open-mail draining still failed for one participant.
- Do not leave the recovery record marked recoverable after `hard-kill`.
