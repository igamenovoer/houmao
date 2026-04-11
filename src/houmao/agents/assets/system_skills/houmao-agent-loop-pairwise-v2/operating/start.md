# Start A Pairwise Loop Run

Use this page when the user already has one authored plan and wants to perform the canonical `start` action after `initialize` is complete.

## Workflow

1. Resolve the designated master and the plan reference:
   - one plan file for the single-file form
   - `plan.md` or the bundle root for the bundle form
2. Confirm that the plan already defines:
   - designated master
   - participants
   - delegation policy
   - authored topology and descendant relationships
   - prestart procedure
   - preparation target policy
   - participant preparation material
   - completion condition
   - stop posture
   - reporting contract
3. If any of those control fields is still unclear, return to the authoring lane before sending a start request.
4. Confirm that `initialize` is already complete:
   - the participant set and standalone preparation material are valid
   - notifier preflight is complete
   - the targeted preparation wave has been sent to the resolved preparation recipients
   - if the plan uses `require_ack`, required replies from targeted preparation recipients have arrived and the run is `ready`
5. If initialization is not yet complete, return to `prestart/prepare-run.md` instead of collapsing `initialize` into `start`.
6. Derive or recover the user-visible `run_id`.
7. Build one normalized charter from `references/run-charter.md`.
8. Deliver that charter to the master through `houmao-agent-messaging`.
9. Require an explicit master response:
   - `accepted`
   - `rejected`
10. After acceptance, treat the run as `running`.
11. After the master accepts the run, the master owns liveness, supervision, downstream pairwise dispatch, completion evaluation, and stop handling.
12. If the accepted run needs live reminders or mailbox follow-up, let the master use `houmao-agent-gateway`, `houmao-agent-email-comms`, and the elemental pairwise pattern in `houmao-adv-usage-pattern` for each immediate driver-worker edge while keeping composed run topology in the accepted plan.
13. When the plan enables timeout-watch policy for selected participants or edges, keep it reminder-driven and non-blocking:
   - persist overdue-check state in local bookkeeping
   - end the current live turn after downstream dispatch and follow-up setup
   - reopen the state later through a reminder-driven review round
   - check mailbox first
   - route overdue downstream peeking through `houmao-agent-inspect` only after mailbox review still shows the expected signal missing

## Start Contract

- The user agent is outside the pairwise execution loop.
- `initialize` remains separate from `start`.
- The start charter is a control-plane message, not a root pairwise execution edge.
- The master should keep the run alive until the completion condition is satisfied or a stop signal arrives.
- Later `peek` remains read-only and does not keep the run alive.

## Guardrails

- Do not send the raw user goal alone when the plan has already been normalized.
- Do not trigger the master before the run is `ready`.
- Do not make one participant's preparation brief depend on hidden upstream-specific information from another participant.
- Do not treat leaf participants as readiness blockers unless the user explicitly included them in the preparation target set.
- Do not start when the topology is too unclear to identify the targeted preparation recipients used by `initialize`.
- Do not ask the user agent to keep the run alive after the master accepted it.
- Do not block one live turn after downstream dispatch merely because timeout-watch policy exists.
- Do not silently widen delegation authority while constructing the charter.
