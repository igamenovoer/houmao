# Start A Pairwise Loop Run

Use this page when the user already has an authored pairwise-v3 plan and wants to perform the canonical `start` action after `initialize` is complete.

## Inputs

Resolve the canonical plan reference first:
- `<plan-output-dir>/plan.md` for the single-file form
- `<plan-output-dir>/plan.md` for the bundle form, with supporting files beside it

Before sending `start`, confirm the plan defines:
- designated master
- participants
- workspace contract
- delegation policy
- authored topology and descendant relationships
- prestart procedure
- selected prestart strategy
- plan revision, digest, or equivalent freshness marker
- exact memo sentinel convention keyed by `run_id` and slot `initialize`
- initialize memo-slot expectations for the designated master when managed memory is being used
- explicit `operator_preparation_wave` target policy and acknowledgement posture when that strategy is selected
- routing packet inventory and root packet location when routing packets are part of the plan
- completion condition
- stop posture
- reporting contract

## Workflow

1. If any control field is still unclear, return to the authoring lane before sending a start request.
2. Confirm that `initialize` is already complete:
   - when routing packets are part of the plan, root and child packet coverage is valid and the root packet is available for the designated master's initialize memo guidance
   - the designated master and every required participant have email/mailbox support for the run's default communication posture
   - run-owned initialize memo blocks have been written or refreshed for participants whose managed memory is being used
   - if explicit `operator_preparation_wave` is selected, targeted notifier and preparation-mail work is complete
   - if explicit `require_ack` is selected for `operator_preparation_wave`, required replies from targeted preparation recipients have arrived
   - the run is `ready`
3. If initialization is not yet complete, return to `prestart/prepare-run.md` instead of collapsing `initialize` into `start`.
4. Derive or recover the user-visible `run_id`.
5. Confirm that the designated master's initialize memo guidance already contains the organization rules, workspace posture, completion posture, stop posture, and root routing guidance needed to supervise the run.
6. Build one compact kickoff trigger from `references/run-charter.md`.
7. Choose kickoff delivery transport:
   - default: send the kickoff trigger to the designated master through `houmao-agent-email-comms`
   - explicit override: use `houmao-agent-messaging` only when the user explicitly requests direct prompt delivery
8. Initialize or refresh the runtime-owned recovery record under `<runtime-root>/loop-runs/pairwise-v2/<run_id>/record.json` and append a `start_dispatched` event to `events.jsonl`:
   - keep the record outside the authored plan bundle and outside participant-local memo or page files
   - record `run_id`, `recovery_epoch=0`, canonical plan reference, plan revision or digest, designated master, allowed participant set, initialize memo-slot references, continuation-page references when available, mailbox bindings, declared workspace contract summary, declarative wakeup posture, and recoverable-versus-terminal state
9. After the kickoff trigger is sent, treat the run as `running`.
10. After `start` fires, the master owns liveness, supervision, downstream pairwise dispatch, completion evaluation, and stop handling.
11. Direct the master and any intermediate driver to advise all downstream agents to use email/mailbox for job communication by default, including in-loop pairwise edge requests, receipts, and results.
12. When routing packets are part of the plan, append the exact prepared child routing packet to each pairwise edge request email without editing, merging, or summarizing it unless the authored plan explicitly permits that transformation.
13. Require fail-closed handling for packet mismatches: if a child packet is missing, has the wrong intended recipient, or carries a stale plan revision or digest, the driver stops that downstream dispatch and reports the mismatch.
14. Do not ask the master or intermediate drivers to run graph analysis, infer descendants, or recompute child packet content after `start`; graph-tool checks belong before `ready`.
15. Let the master use `houmao-agent-gateway`, `houmao-agent-email-comms`, and the elemental pairwise pattern in `houmao-adv-usage-pattern` for each immediate driver-worker edge while keeping composed run topology in the authored plan.
16. When the plan enables timeout-watch policy for selected participants or edges, keep it reminder-driven and non-blocking:
   - persist overdue-check state in local bookkeeping
   - end the current live turn after downstream dispatch and follow-up setup
   - reopen the state later through a reminder-driven review round
   - check mailbox first
   - route overdue downstream peeking through `houmao-agent-inspect` only after mailbox review still shows the expected signal missing

## Start Kickoff Material

Use the designated master's initialize memo block as the primary readable control-plane charter for ordinary `start`.

- memo slot: `initialize`
- memo block: the durable master-facing run contract written during `initialize`
- memo work: route through `houmao-memory-mgr`

When the user asks to inspect or edit the designated master's agent memo, `houmao-memo.md`, or memo-linked managed-memory pages while preparing `start`, route that work to `houmao-memory-mgr`.

## Runtime-Owned Recovery Record

Started pairwise-v3 runs create or refresh one runtime-owned recovery record for that logical run:

- record path: `<runtime-root>/loop-runs/pairwise-v2/<run_id>/record.json`
- history path: `<runtime-root>/loop-runs/pairwise-v2/<run_id>/events.jsonl`
- ownership: runtime-owned, not authored-plan-owned

The recovery record should capture the authored plan reference and freshness marker, participant set, initialize memo-slot references, continuation-page references when available, mailbox bindings, declared workspace contract summary, declarative wakeup posture, and whether the run is still recoverable.

## Compact Start Trigger

The live `start` trigger is intentionally compact. It should:
- identify the `run_id`
- tell the designated master to read its initialize memo and begin work
- state that the operator remains outside the execution loop
- avoid requiring an explicit reply
- travel through mail by default unless the user explicitly requests direct prompt delivery

## Start Contract

- The user agent is outside the pairwise execution loop.
- `initialize` remains separate from `start`.
- The designated master's initialize memo block is the primary readable control-plane charter when the designated master's managed memory is being used.
- The live start trigger is a compact control-plane mail by default, not a root pairwise execution edge.
- Fired `start` initializes or refreshes the runtime-owned recovery record for the same `run_id`.
- The authored workspace contract travels with the started run, but runtime-owned recovery files remain outside that contract.
- For plans with routing packets, the designated master's initialize memo block carries the root packet or exact root packet reference.
- In-loop job communication uses email/mailbox by default for pairwise edge requests, receipts, and results.
- The master should keep the run alive until the completion condition is satisfied or a stop signal arrives.
- Later `peek` remains unintrusive, read-only, and does not keep the run alive.

## Guardrails

- Do not send the raw user goal alone when the plan has already been normalized.
- Do not trigger the master before the run is `ready`.
- Do not proceed with ordinary `start` when the designated master or any required participant lacks email/mailbox support.
- Do not default ordinary `start` to direct prompt delivery.
- Do not use the compact start trigger as the only copy of the full run contract when the designated master's managed memory is being used.
- Do not make the master or intermediate drivers run graph analysis or recompute child routing packets from the full plan at runtime.
- Do not edit, merge, or summarize prepared child routing packets by default.
- Do not treat acknowledgement replies as readiness blockers unless `require_ack` was explicitly selected.
- Do not start when the topology is too unclear to validate routing-packet coverage or initialize memo material used by `initialize`.
- Do not ask the user agent to keep the run alive after the master starts the run.
- Do not block one live turn after downstream dispatch merely because timeout-watch policy exists.
- Do not silently widen delegation authority while constructing the charter.
- Do not wait for ordinary `start` to return `accepted` or `rejected`.
- Do not skip recovery-record initialization when the master kickoff trigger is sent.
