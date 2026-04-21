# pairwise-v2-run-recovery Specification

## Purpose
Define the runtime-owned recovery record, restart recovery flow, durable continuation material, and declarative wakeup-restoration contract for accepted pairwise-v2 runs.

## Requirements
### Requirement: Pairwise-v2 accepted runs persist a runtime-owned recovery record
The system SHALL persist one durable pairwise-v2 recovery record under the effective runtime root for each pairwise-v2 run that the designated master accepts.

That recovery record SHALL remain outside the authored plan bundle and outside participant-local memo or page files.

The recovery record SHALL identify at minimum:

- `run_id`,
- `recovery_epoch`,
- canonical plan reference and plan digest or equivalent freshness marker,
- designated master and allowed participant set,
- latest known runtime-manifest or gateway references for each participant when available,
- durable initialize or start-charter page references needed to continue the run,
- mailbox bindings and declarative wakeup posture needed for recovery,
- whether the run remains recoverable or terminal.

#### Scenario: Accepted start creates one recovery record
- **WHEN** the designated master explicitly accepts pairwise-v2 run `run-1`
- **THEN** the system persists one runtime-owned recovery record for `run-1`
- **AND THEN** that record includes the accepted plan reference, participant set, durable page references, wakeup posture, and recovery eligibility state

#### Scenario: Hard-kill marks the recovery record terminal
- **WHEN** pairwise-v2 run `run-1` later ends through `hard-kill`
- **THEN** the recovery record for `run-1` is marked terminal
- **AND THEN** ordinary `recover_and_continue` is no longer allowed for that record

### Requirement: Pairwise-v2 recover_and_continue rebinds participants under the same logical run
The system SHALL resolve `recover_and_continue` by `run_id` against the durable recovery record for that accepted run.

The system SHALL preserve the same user-visible `run_id` during `recover_and_continue` and SHALL fail closed rather than silently minting a replacement run when continuity under that `run_id` is unsafe.

When one or more stored participants are no longer backed by the original live runtime session, the system SHALL require rebinding through stable managed-agent identity or explicit operator-confirmed mapping before continuation can proceed.

The recovered run SHALL enter `recovering` while participant rebinding, continuation-material refresh, or wakeup restoration is still in progress.

After participant rebinding, continuation-material refresh, and declarative wakeup restoration are complete, the recovered run SHALL enter `recovered_ready`.

The system SHALL return the recovered run to `running` only after the designated master explicitly replies `accepted` to the compact `recover_and_continue` trigger.

#### Scenario: Successful restart recovery rebinds relaunched participants
- **WHEN** pairwise-v2 run `run-1` has one or more participants that were relaunched under new live runtime sessions
- **AND WHEN** each stored participant can be matched through stable identity or explicit operator-confirmed mapping
- **THEN** `recover_and_continue` rebinds those participants under the same logical run `run-1`
- **AND THEN** the run enters `recovered_ready` before the master re-accepts continuation

#### Scenario: Unsafe continuity fails closed
- **WHEN** pairwise-v2 run `run-1` is addressed for `recover_and_continue`
- **AND WHEN** the stored plan digest no longer matches the intended active plan or participant rebinding remains ambiguous
- **THEN** the system rejects restart recovery for `run-1`
- **AND THEN** it does not silently mint a replacement run id or continue unsafe work

### Requirement: Pairwise-v2 recovery materializes durable continuation guidance
For each rebound participant whose managed memory is being used, `recover_and_continue` SHALL write or refresh one run-scoped continuation page under a namespace such as `pages/loop-runs/pairwise-v2/<run_id>/recover-and-continue.md`.

For each rebound participant whose managed memory is being used, `recover_and_continue` SHALL write or refresh one exact-sentinel memo reference block keyed by `run_id` and slot `recover-and-continue`.

The continuation material SHALL state that the run is resumed after restart and SHALL require inspection of leftover mailbox state, memo or page state, workspace or branch state, notes or logs or tmp outputs, and incomplete downstream obligations before fresh work begins.

For the designated master, `recover_and_continue` SHALL send a compact control-plane trigger that points at the durable continuation page and requires explicit `accepted` or `rejected`.

#### Scenario: Recovery writes a durable participant continuation page
- **WHEN** `recover_and_continue` restores participant `worker-a`
- **AND WHEN** `worker-a` exposes managed memory
- **THEN** the recovery flow writes or refreshes `worker-a`'s run-scoped continuation page and matching memo reference block
- **AND THEN** that durable material tells `worker-a` to inspect leftover artifacts before fresh work

#### Scenario: Recovery trigger stays compact for the master
- **WHEN** the designated master's durable continuation page for run `run-1` has already been written
- **THEN** `recover_and_continue` sends a compact control-plane trigger that points at that page
- **AND THEN** the master must reply `accepted` or `rejected` before the run returns to `running`

### Requirement: Pairwise-v2 recovery restores declarative wakeup posture and reports one summary
Before the designated master re-accepts continuation, `recover_and_continue` SHALL restore the stored declarative wakeup posture needed for that accepted run, including persisted mail-notifier enablement, polling interval, and stored notifier appendix text when those were part of the accepted run.

`recover_and_continue` SHALL NOT blindly replay raw live gateway reminder identifiers as if they were durable recovery state.

When prior live reminder timing cannot be durably recovered, the continuation material SHALL tell the designated master to re-arm the needed live reminder posture after continuation is accepted.

The recovery flow SHALL emit one operator-visible recovery summary that identifies the run, reports participant rebindings, lists durable pages refreshed, describes wakeup posture restored, and names any unresolved blockers.

#### Scenario: Recovery restores notifier posture from stored declarative state
- **WHEN** one recoverable pairwise-v2 run previously used gateway mail-notifier polling with stored interval and appendix posture
- **THEN** `recover_and_continue` restores that declarative notifier posture before the master re-accepts continuation
- **AND THEN** the operator-visible summary reports the notifier restoration outcome

#### Scenario: Recovery does not replay stale live reminder ids
- **WHEN** one recoverable pairwise-v2 run previously relied on live gateway reminders that no longer exist after restart
- **THEN** `recover_and_continue` does not replay stale reminder ids as durable state
- **AND THEN** the continuation material tells the master to re-arm the needed live reminder posture after acceptance
