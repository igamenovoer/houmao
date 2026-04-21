## 1. Recovery Record Contract

- [x] 1.1 Add a runtime-owned pairwise-v2 recovery record contract under the effective runtime root, including the latest `record.json` shape and append-only recovery history.
- [x] 1.2 Persist or refresh the recovery record when a pairwise-v2 run is accepted, recovered, stopped, or hard-killed, including recoverable-versus-terminal state.
- [x] 1.3 Add targeted tests for recovery-record creation, recovery-epoch updates, and terminal marking after `hard-kill`.

## 2. Recover And Continue Flow

- [x] 2.1 Implement `recover_and_continue` eligibility checks that preserve the same `run_id`, reject terminal or stale-plan runs, and fail closed on ambiguous participant rebinding.
- [x] 2.2 Implement identity-first participant rebinding plus any required operator-confirmed mapping for relaunched participants.
- [x] 2.3 Materialize durable `recover-and-continue` page and memo-slot guidance for rebound participants and send the compact master continuation trigger that requires `accepted` or `rejected`.
- [x] 2.4 Restore declarative wakeup posture during recovery, avoid replaying raw live reminder ids, and emit one operator-visible recovery summary.
- [x] 2.5 Add targeted tests for successful restart recovery, ambiguous-rebinding rejection, stale-plan rejection, and notifier/restoration behavior.

## 3. Pairwise-V2 Skill And Docs

- [x] 3.1 Update the packaged `houmao-agent-loop-pairwise-v2` assets to add `recover_and_continue`, `recovering`, and `recovered_ready`, and to keep `resume` pause-only.
- [x] 3.2 Add or revise pairwise-v2 operating guidance so `hard-kill` stays terminal and restart recovery uses the new durable continuation-material flow.
- [x] 3.3 Update loop-authoring and related operator-facing docs to explain `resume` versus `recover_and_continue`, the runtime-owned recovery record, and the recovery-page contract.
- [x] 3.4 Add or refresh targeted content tests that guard the new pairwise-v2 recovery vocabulary and lifecycle boundaries.
