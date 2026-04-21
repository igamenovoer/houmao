# Recover And Continue A Pairwise Loop Run

Use this page when the user wants to restore one accepted pairwise loop after one or more participants were stopped, killed, or relaunched and the same logical `run_id` should continue.

## Inputs

Before starting, resolve:
- the target `run_id`
- the canonical plan reference and plan revision, digest, or equivalent freshness marker
- the runtime-owned recovery record at `<runtime-root>/loop-runs/pairwise-v2/<run_id>/record.json`
- the append-only recovery history at `<runtime-root>/loop-runs/pairwise-v2/<run_id>/events.jsonl`

## Workflow

1. Resolve the designated master, the stored allowed participant set, and the target `run_id` from the recovery record.
2. Confirm that the recovery record exists and still marks the run recoverable:
   - if the record is missing, fail clearly instead of pretending the run can be recovered safely
   - if the record is marked terminal, reject ordinary `recover_and_continue`
3. Confirm that the intended active plan still matches the recovery record:
   - the canonical plan reference still identifies the same accepted plan
   - the stored plan revision, digest, or equivalent freshness marker still matches
   - if the plan drifted materially, fail closed and direct the operator to start a fresh run instead
4. Enter `recovering` while participant rebinding, durable continuation-material refresh, or declarative wakeup restoration is still in progress.
5. Rebind participants identity-first:
   - use stable managed-agent identity plus current runtime or gateway evidence when available
   - keep the designated master explicit
   - require explicit operator-confirmed mapping when more than one live agent could satisfy the same stored participant identity
   - fail closed when any required participant remains ambiguous or unavailable
6. Verify that the designated master and every required participant have email/mailbox support before continuation proceeds:
   - use the supported Houmao email or mailbox inspection surfaces to confirm that each rebound participant can participate in the run's default email/mailbox communication posture
   - if any required participant lacks that support, fail clearly and do not return the run to `running`
7. For each rebound participant whose managed memory is being used, resolve one run-scoped continuation page path under `HOUMAO_AGENT_PAGES_DIR` through `houmao-memory-mgr`, using a namespace such as `loop-runs/pairwise-v3/<run_id>/recover-and-continue.md`.
8. Write or replace one durable continuation page for each rebound participant through `houmao-memory-mgr` when managed memory is being used:
   - state that this is restart recovery for the same logical `run_id`
   - include the participant's current role, obligations, and any exact packet or result-return context that still matters
   - require inspection of leftover mailbox state, memo or page state, workspace or branch state, notes or logs or tmp outputs, declared bookkeeping paths, and incomplete downstream obligations before fresh work begins
9. Write or replace one compact memo reference block for each rebound participant through `houmao-memory-mgr` when managed memory is being used:
   - use one exact begin sentinel and one exact end sentinel keyed by `run_id` and slot `recover-and-continue`
   - keep the block short and point at `pages/<relative-page>`
   - replace only the bounded block when exactly one matching begin/end pair exists
   - append one new bounded block when no matching begin/end pair exists
   - fail closed and report a conflict when more than one matching begin/end pair exists
10. Restore declarative wakeup posture before the master re-accepts continuation:
   - restore persisted mail-notifier enablement, interval, and appendix posture when those were part of the accepted run
   - for each rebound participant with the required live gateway and mailbox surfaces, verify or enable agent email notification through `houmao-agent-gateway` before continuation proceeds
   - do not replay raw live gateway reminder ids as though they were durable recovery state
   - when prior live reminder timing cannot be durably recovered, tell the master to re-arm the needed live reminder posture after continuation is accepted
11. Refresh the runtime-owned recovery record and append one recovery attempt event:
   - preserve the same user-visible `run_id`
   - increment `recovery_epoch` only when continuation is successfully accepted
   - record participant rebindings, refreshed continuation-page references, initialized memo-slot references when available, restored declarative wakeup posture, and unresolved blockers
12. Enter `recovered_ready` after participant rebinding, email/mailbox verification, continuation-material refresh, and declarative wakeup restoration are complete.
13. Send one compact `recover_and_continue` trigger to the designated master through `houmao-agent-messaging`:
   - identify the `run_id`
   - point the master at the durable continuation page
   - require exactly one explicit reply: `accepted` or `rejected`
14. Return the run to `running` only after the designated master explicitly replies `accepted`.
15. Emit one operator-visible recovery summary that names the run, reports participant rebindings, lists continuation pages and memo material refreshed, describes wakeup posture restored including agent email-notification re-enable results, and calls out any unresolved blockers.

## Durable Continuation Material

Use the durable continuation page as the primary readable recovery contract for participants whose managed memory is being used.

- page namespace: `loop-runs/pairwise-v3/<run_id>/recover-and-continue.md`
- memo block: short pointer surface only
- memo slot: `recover-and-continue`
- memo work: route through `houmao-memory-mgr`

## Recover-And-Continue Contract

- `recover_and_continue` preserves the same `run_id`.
- `recover_and_continue` is distinct from both soft `resume` and terminal `hard-kill`.
- `recover_and_continue` requires a runtime-owned recovery record plus identity-first participant rebinding.
- `recover_and_continue` requires email/mailbox support for the designated master and every required participant before continuation proceeds.
- `recover_and_continue` re-enables agent email notification for rebound participants when the run's stored posture and live gateway/mailbox surfaces support it.
- `recover_and_continue` reuses the authored workspace contract while keeping runtime-owned recovery files outside that contract.
- `recover_and_continue` returns the run to `running` only after the designated master explicitly accepts continuation.

## Guardrails

- Do not treat `recover_and_continue` as a synonym for `resume`.
- Do not mint a replacement `run_id` silently when continuity under the stored `run_id` is unsafe.
- Do not use ordinary `recover_and_continue` after a terminal `hard-kill`.
- Do not continue a recovered run when the designated master or any required participant lacks email/mailbox support.
- Do not skip agent email-notification re-enable work for rebound participants when the recovered run depends on that posture.
- Do not skip leftover-artifact inspection before fresh work begins.
- Do not replay stale reminder ids as though they were durable recovery state.
- Do not store mutable recovery bookkeeping in the authored plan bundle or inside participant memo pages.
