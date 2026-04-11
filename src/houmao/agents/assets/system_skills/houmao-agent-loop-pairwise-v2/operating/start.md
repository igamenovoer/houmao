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
   - selected prestart strategy
   - routing packet inventory and root packet location for `precomputed_routing_packets`
   - preparation target policy only when explicit `operator_preparation_wave` is selected
   - completion condition
   - stop posture
   - reporting contract
3. If any of those control fields is still unclear, return to the authoring lane before sending a start request.
4. Confirm that `initialize` is already complete:
   - for `precomputed_routing_packets`, root and child packet coverage is valid and the root packet is available for the charter
   - for explicit `operator_preparation_wave`, notifier preflight is complete and the targeted preparation wave has been sent to the resolved preparation recipients
   - if explicit `operator_preparation_wave` uses `require_ack`, required replies from targeted preparation recipients have arrived
   - the run is `ready`
5. If initialization is not yet complete, return to `prestart/prepare-run.md` instead of collapsing `initialize` into `start`.
6. Derive or recover the user-visible `run_id`.
7. Build one normalized charter from `references/run-charter.md`.
8. Include the root routing packet or exact root packet reference in that charter when the plan uses `precomputed_routing_packets`.
9. Deliver that charter to the master through `houmao-agent-messaging`.
10. Require an explicit master response:
   - `accepted`
   - `rejected`
11. After acceptance, treat the run as `running`.
12. After the master accepts the run, the master owns liveness, supervision, downstream pairwise dispatch, completion evaluation, and stop handling.
13. Direct the master and any intermediate driver to append the exact prepared child routing packet to each ordinary pairwise edge request, without editing, merging, or summarizing it unless the authored plan explicitly permits that transformation.
14. Require fail-closed handling for packet mismatches: if a child packet is missing, has the wrong intended recipient, or carries a stale plan revision or digest, the driver stops that downstream dispatch and reports the mismatch to its immediate driver, or to the operator when the driver is the master.
15. If the accepted run needs live reminders or mailbox follow-up, let the master use `houmao-agent-gateway`, `houmao-agent-email-comms`, and the elemental pairwise pattern in `houmao-adv-usage-pattern` for each immediate driver-worker edge while keeping composed run topology in the accepted plan.
16. When the plan enables timeout-watch policy for selected participants or edges, keep it reminder-driven and non-blocking:
   - persist overdue-check state in local bookkeeping
   - end the current live turn after downstream dispatch and follow-up setup
   - reopen the state later through a reminder-driven review round
   - check mailbox first
   - route overdue downstream peeking through `houmao-agent-inspect` only after mailbox review still shows the expected signal missing

## Start Contract

- The user agent is outside the pairwise execution loop.
- `initialize` remains separate from `start`.
- The start charter is a control-plane message, not a root pairwise execution edge.
- For default `precomputed_routing_packets`, the start charter carries the root packet or exact root packet reference.
- The master should keep the run alive until the completion condition is satisfied or a stop signal arrives.
- Later `peek` remains read-only and does not keep the run alive.

## Guardrails

- Do not send the raw user goal alone when the plan has already been normalized.
- Do not trigger the master before the run is `ready`.
- Do not make the master or intermediate drivers recompute child routing packets from the full plan at runtime.
- Do not edit, merge, or summarize prepared child routing packets by default.
- Do not treat leaf participants as readiness blockers unless explicit `operator_preparation_wave` included them in the preparation target set.
- Do not start when the topology is too unclear to validate routing-packet coverage or explicit preparation-wave targets used by `initialize`.
- Do not ask the user agent to keep the run alive after the master accepted it.
- Do not block one live turn after downstream dispatch merely because timeout-watch policy exists.
- Do not silently widen delegation authority while constructing the charter.
