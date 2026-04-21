# Start A Pairwise Loop Run

Use this page when the user already has an authored pairwise-v2 plan and wants to perform the canonical `start` action after `initialize` is complete.

## Inputs

Resolve the canonical plan reference first:
- `<plan-output-dir>/plan.md` for the single-file form
- `<plan-output-dir>/plan.md` for the bundle form, with supporting files beside it

Before sending `start`, confirm the plan defines:
- designated master
- participants
- delegation policy
- authored topology and descendant relationships
- prestart procedure
- selected prestart strategy
- plan revision, digest, or equivalent freshness marker
- durable start-charter page namespace when the designated master's managed memory is being used
- exact memo sentinel convention keyed by `run_id` and slot `start-charter`
- explicit `operator_preparation_wave` target policy and acknowledgement posture when that strategy is selected
- routing packet inventory and root packet location when routing packets are part of the plan
- completion condition
- stop posture
- reporting contract

## Workflow

1. If any control field is still unclear, return to the authoring lane before sending a start request.
2. Confirm that `initialize` is already complete:
   - when routing packets are part of the plan, root and child packet coverage is valid and the root packet is available for the charter
   - durable initialize pages and exact-sentinel memo reference blocks have been written or refreshed for participants whose managed memory is being used
   - if explicit `operator_preparation_wave` is selected, targeted notifier and preparation-mail work is complete
   - if explicit `require_ack` is selected for `operator_preparation_wave`, required replies from targeted preparation recipients have arrived
   - the run is `ready`
3. If initialization is not yet complete, return to `prestart/prepare-run.md` instead of collapsing `initialize` into `start`.
4. Derive or recover the user-visible `run_id`.
5. Resolve the durable start-charter page path under `HOUMAO_AGENT_PAGES_DIR` through `houmao-memory-mgr`, using a run-scoped namespace such as `loop-runs/pairwise-v2/<run_id>/start-charter.md`.
6. Build one normalized start-charter page from `references/run-charter.md`.
7. Include the root routing packet or exact root packet reference in that page when the plan uses routing packets.
8. Write or replace the start-charter page through `houmao-memory-mgr` when the designated master's managed memory is being used.
9. Write or replace the designated master's compact memo reference block through `houmao-memory-mgr` when the designated master's managed memory is being used:
   - use one exact begin sentinel and one exact end sentinel keyed by `run_id` and slot `start-charter`
   - replace only the bounded block when exactly one matching begin/end pair exists
   - append one new bounded block when no matching begin/end pair exists
   - fail closed and report a conflict when more than one matching begin/end pair exists
10. Deliver the compact start trigger to the master through `houmao-agent-messaging`.
11. Require an explicit master response:
   - `accepted`
   - `rejected`
12. After acceptance, initialize or refresh the runtime-owned recovery record under `<runtime-root>/loop-runs/pairwise-v2/<run_id>/record.json` and append a `start_accepted` event to `events.jsonl`:
   - keep the record outside the authored plan bundle and outside participant-local memo or page files
   - record `run_id`, `recovery_epoch=0`, canonical plan reference, plan revision or digest, designated master, allowed participant set, durable initialize/start page references, mailbox bindings, declarative wakeup posture, and recoverable-versus-terminal state
13. After acceptance, treat the run as `running`.
14. After the master accepts the run, the master owns liveness, supervision, downstream pairwise dispatch, completion evaluation, and stop handling.
15. Direct the master and any intermediate driver to advise all downstream agents to use email/mailbox for job communication by default, including in-loop pairwise edge requests, receipts, and results.
16. When routing packets are part of the plan, append the exact prepared child routing packet to each pairwise edge request email without editing, merging, or summarizing it unless the authored plan explicitly permits that transformation.
17. Require fail-closed handling for packet mismatches: if a child packet is missing, has the wrong intended recipient, or carries a stale plan revision or digest, the driver stops that downstream dispatch and reports the mismatch.
18. Do not ask the master or intermediate drivers to run graph analysis, infer descendants, or recompute child packet content after `start`; graph-tool checks belong before `ready`.
19. Let the master use `houmao-agent-gateway`, `houmao-agent-email-comms`, and the elemental pairwise pattern in `houmao-adv-usage-pattern` for each immediate driver-worker edge while keeping composed run topology in the accepted plan.
20. When the plan enables timeout-watch policy for selected participants or edges, keep it reminder-driven and non-blocking:
   - persist overdue-check state in local bookkeeping
   - end the current live turn after downstream dispatch and follow-up setup
   - reopen the state later through a reminder-driven review round
   - check mailbox first
   - route overdue downstream peeking through `houmao-agent-inspect` only after mailbox review still shows the expected signal missing

## Durable Start Material

Use the durable start-charter page as the primary readable control-plane charter for the designated master.

- page namespace: `loop-runs/pairwise-v2/<run_id>/start-charter.md`
- memo block: short pointer surface only
- memo work: route through `houmao-memory-mgr`

When the user asks to inspect or edit the designated master's agent memo, `houmao-memo.md`, or memo-linked managed-memory pages while preparing `start`, route that work to `houmao-memory-mgr`.

## Runtime-Owned Recovery Record

Accepted pairwise-v2 starts create or refresh one runtime-owned recovery record for that logical run:

- record path: `<runtime-root>/loop-runs/pairwise-v2/<run_id>/record.json`
- history path: `<runtime-root>/loop-runs/pairwise-v2/<run_id>/events.jsonl`
- ownership: runtime-owned, not authored-plan-owned

The recovery record should capture the accepted plan reference and freshness marker, participant set, durable page references, mailbox bindings, declarative wakeup posture, and whether the run is still recoverable.

## Compact Start Trigger

The live `start` trigger is intentionally compact. It should:
- identify the `run_id`
- point the master at the durable start-charter page
- state that the operator remains outside the execution loop
- require one explicit `accepted` or `rejected` reply

## Start Contract

- The user agent is outside the pairwise execution loop.
- `initialize` remains separate from `start`.
- The durable start-charter page is the primary readable control-plane charter when the designated master's managed memory is being used.
- The live start trigger is a compact control-plane message, not a root pairwise execution edge.
- Accepted `start` initializes or refreshes the runtime-owned recovery record for the same `run_id`.
- For plans with routing packets, the start-charter page carries the root packet or exact root packet reference.
- In-loop job communication uses email/mailbox by default for pairwise edge requests, receipts, and results.
- The master should keep the run alive until the completion condition is satisfied or a stop signal arrives.
- Later `peek` remains unintrusive, read-only, and does not keep the run alive.

## Guardrails

- Do not send the raw user goal alone when the plan has already been normalized.
- Do not trigger the master before the run is `ready`.
- Do not use the compact start trigger as the only copy of the full charter when the designated master's managed memory is being used.
- Do not infer memo replacement boundaries from headings, nearby prose, or fuzzy text; use exact begin/end sentinels keyed by `run_id` and slot `start-charter`.
- Do not make the master or intermediate drivers run graph analysis or recompute child routing packets from the full plan at runtime.
- Do not edit, merge, or summarize prepared child routing packets by default.
- Do not treat acknowledgement replies as readiness blockers unless `require_ack` was explicitly selected.
- Do not start when the topology is too unclear to validate routing-packet coverage or durable initialize material used by `initialize`.
- Do not ask the user agent to keep the run alive after the master accepted it.
- Do not block one live turn after downstream dispatch merely because timeout-watch policy exists.
- Do not silently widen delegation authority while constructing the charter.
- Do not skip recovery-record initialization when the master accepts the run.
