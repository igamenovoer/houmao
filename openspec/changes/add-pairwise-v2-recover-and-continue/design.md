## Context

`houmao-agent-loop-pairwise-v2` already has a useful durability model for long-running runs:
- `initialize` writes durable participant guidance into managed-memory pages plus exact-sentinel memo reference blocks
- `start` writes a durable master-facing start-charter page and uses a compact live trigger
- managed-agent runtime manifests, gateway status, relaunch, and managed-memory roots already provide stable building blocks for restart-aware control

What is missing is the layer that ties those building blocks together after a real participant stop or restart. Today `resume` is explicitly soft-pause-only, `hard-kill` is terminal, reminders are live gateway state rather than durable recovery state, and the authored plan bundle is intentionally static operator-owned material rather than mutable run bookkeeping.

That leaves a gap for the operational case raised in upstream issues `#33` and `#30`: one accepted logical pairwise-v2 run should be recoverable after participants die or are relaunched, without asking the operator to manually reconstruct plan state, mailbox bindings, durable page pointers, and wakeup posture from scratch.

## Goals / Non-Goals

**Goals:**
- Add one first-class `recover_and_continue` recovery action to pairwise-v2, distinct from soft `resume`.
- Persist enough runtime-owned state to recover one accepted logical run after participant restart without storing mutable state in the authored plan bundle.
- Reuse existing runtime manifests, gateway status, relaunch, and managed-memory surfaces instead of inventing a parallel loop engine.
- Preserve the same user-visible `run_id` across restart recovery and track recovery attempts separately.
- Materialize durable recovery guidance that tells participants to inspect leftover artifacts before doing fresh work.
- Restore declarative wakeup posture safely and produce one operator-visible recovery summary.

**Non-Goals:**
- Generalizing restart recovery to the stable pairwise skill or generic loop skill in this change.
- Turning `hard-kill` into a recoverable or partially reversible action.
- Persisting raw live gateway reminder ids as durable recovery state.
- Allowing `recover_and_continue` to silently widen the participant set, change the plan digest, or mint a replacement run under a new `run_id`.

## Decisions

### Decision: Pairwise-v2 recovery state lives under the effective runtime root, not in the plan bundle or agent memo

The change will introduce a runtime-owned pairwise-v2 recovery record under the effective runtime root, using a run-scoped location such as:

- `<effective-runtime-root>/loop-runs/pairwise-v2/<run_id>/record.json`
- `<effective-runtime-root>/loop-runs/pairwise-v2/<run_id>/events.jsonl`

`record.json` is the latest durable recovery contract for one accepted logical run. `events.jsonl` is the append-only history of start acceptance, recovery attempts, and terminal transitions.

The recovery record will include at minimum:
- `run_id`
- `recovery_epoch`
- canonical plan reference and plan digest/freshness marker
- designated master and allowed participant set
- latest known runtime-manifest or gateway references for each participant when available
- mailbox bindings and durable page references needed to continue the run
- declarative wakeup posture needed for recovery
- last known terminal or recoverable status

Rationale:
- The authored bundle is explicitly static and must not accumulate mutable run ledgers.
- Agent memo/pages are durable participant-facing context, but they are not the right source of truth for cross-participant recovery bookkeeping.
- Session-local artifacts are too narrow because a recovered participant may get a new runtime session root after relaunch.

Alternatives considered:
- Store recovery state in the authored plan bundle.
  Rejected because the plan bundle is intentionally static operator-owned material.
- Store recovery state only in participant memo/pages.
  Rejected because memo/pages are participant context, not the authority for cross-run rebinding and wakeup restoration.
- Store recovery state only in per-session runtime roots.
  Rejected because restart recovery must survive replacement runtime sessions.

### Decision: `recover_and_continue` is distinct from `resume` and preserves the same `run_id`

The new action vocabulary will be:
- `resume`: restore one previously paused run whose participant set remained logically live
- `recover_and_continue`: restore one accepted run after participant stop, kill, or relaunch

`recover_and_continue` will preserve the same user-visible `run_id`. Each successful recovery increments `recovery_epoch` inside the recovery record instead of minting a new run id. If continuity under the stored `run_id` is unsafe, the action fails closed and instructs the operator to start a new run instead.

The recovery flow will reject ordinary continuation when:
- the run was marked terminal by `hard-kill`
- the stored plan digest no longer matches the intended active plan
- participant rebinding is ambiguous or incomplete
- required durable continuation material cannot be refreshed safely

Rationale:
- Existing initialize/start page and memo conventions are already keyed by `run_id`.
- Reusing the same `run_id` keeps the logical run identity stable for operators and participants.
- A fail-closed posture is safer than silently turning restart recovery into an implicit new run.

Alternatives considered:
- Broaden `resume` to cover restart recovery.
  Rejected because the current `resume` contract is pause-only and widening it would blur operator intent.
- Mint a new run id during recovery.
  Rejected because it weakens continuity and complicates durable page/memo naming without improving the main user story.

### Decision: Recovery writes durable `recover-and-continue` material before the master re-accepts the run

`recover_and_continue` will materialize durable continuation guidance for participants whose managed memory is being used. Each participant gets:
- one run-scoped continuation page under `pages/loop-runs/pairwise-v2/<run_id>/recover-and-continue.md`
- one exact-sentinel memo reference block keyed by `run_id` and slot `recover-and-continue`

The continuation material will say that this is resumed work after restart and will require inspection of:
- mailbox state
- `houmao-memo.md` and linked pages
- worktree, branch, or local workspace state
- notes, logs, tmp outputs, or partial artifacts
- incomplete downstream obligations or pending result-return duties

The designated master also gets a compact control-plane `recover_and_continue` trigger that points at the durable continuation page and requires explicit `accepted` or `rejected`. The recovered run does not return to `running` until recovery completes and the master accepts.

Rationale:
- Restart recovery should not depend on ad hoc prompts that can be lost after relaunch.
- The existing page-plus-memo pattern is already the durable pairwise-v2 contract for initialize/start.
- Recovery needs a durable place to explain the “inspect leftovers before fresh work” rule from the upstream issue.

Alternatives considered:
- Reuse the old initialize page without a distinct recovery slot.
  Rejected because recovery instructions are operationally different from initial setup and should remain auditable.
- Send only one live recovery prompt with no durable page.
  Rejected because that recreates the same fragility the change is meant to remove.

### Decision: Recovery restores declarative wakeup posture, not raw live reminder ids

The recovery record will persist declarative wakeup posture such as:
- whether mail-notifier polling was enabled
- notifier interval
- notifier appendix text or equivalent continuation appendix
- any recovery-relevant acknowledgement or reporting posture

The system will not treat raw gateway reminder ids as durable recovery artifacts. If the prior run depended on live reminders, the recovered continuation material will tell the master to re-arm the needed reminder posture after continuation is accepted.

Rationale:
- The gateway already treats reminders as live process state, not durable recovery state.
- Restoring declarative wakeup posture is sufficient to avoid the current manual notifier choreography.
- Blindly replaying stale reminder ids across gateway restart would be unsafe and brittle.

Alternatives considered:
- Persist and replay raw reminder ids.
  Rejected because reminder ids are tied to live gateway state and do not survive restart safely.
- Ignore wakeup restoration entirely and recover only page/memo state.
  Rejected because notifier restoration is one of the main operator pain points in issue `#33`.

### Decision: Participant rebinding is identity-first with explicit operator confirmation when needed

Recovery will first try to match stored participants to current live managed agents by stable managed identity and current runtime/gateway evidence. When that is insufficient, the flow requires explicit operator-confirmed rebinding before the run can enter `recovered_ready`.

The recovery summary will report:
- which stored participant mapped cleanly
- which participant required explicit rebinding
- which participant could not be rebound
- what wakeup posture was restored
- which durable pages or memo blocks were refreshed

Rationale:
- Agent names and mailbox addresses may survive restart, but they are not always enough to prove safe continuity.
- Operator confirmation is the right boundary when a replacement runtime instance is plausible but not provable automatically.

Alternatives considered:
- Match only by friendly agent name.
  Rejected because friendly names alone are too weak for safe restart recovery.
- Require manual mapping for every participant.
  Rejected because the common case should remain streamlined when identities still line up.

## Risks / Trade-offs

- [Risk] Recovery records can drift from live participant reality after repeated relaunches. → Mitigation: require identity-first rebinding, fail closed on ambiguity, and record the new recovery epoch only after successful continuation acceptance.
- [Risk] Operators may expect `recover_and_continue` to revive hard-killed runs. → Mitigation: keep `hard-kill` explicitly terminal in the pairwise-v2 skill and reject recovery from terminal records.
- [Risk] Participants may ignore leftover local artifacts and start fresh work too early. → Mitigation: make the durable continuation page explicitly require leftover-artifact inspection before fresh work and require master re-acceptance.
- [Risk] Not restoring raw live reminders may leave some timing posture incomplete. → Mitigation: restore notifier configuration declaratively and instruct the master to re-arm any live reminder posture after acceptance.
- [Risk] Older accepted runs will not have the new recovery record. → Mitigation: fail clearly for runs without recovery records and direct operators to start a fresh run or use the older manual recovery choreography.

## Migration Plan

No external dependency or schema migration is required.

Implementation should:
1. Add the recovery-record contract under the effective runtime root and create it for newly accepted pairwise-v2 runs.
2. Add `recover_and_continue` guidance plus recovery-state vocabulary to the pairwise-v2 packaged skill and supporting references.
3. Add durable continuation-page and memo-slot guidance that reuses the existing exact-sentinel memo replacement model.
4. Update pairwise-v2 docs/specs to make `resume`, `recover_and_continue`, and `hard-kill` non-overlapping lifecycle actions.

Existing accepted runs without a recovery record are not automatically backfilled. For those runs, the new workflow should fail clearly instead of pretending it can recover state that was never recorded.

Rollback is straightforward: revert the skill/docs/runtime changes. Any new recovery files left under the runtime root remain inert runtime-owned artifacts and do not corrupt plan bundles or managed-memory pages.

## Open Questions

- Whether the operator-facing recovery entrypoint should accept only `run_id`, or also allow plan-ref resolution when one plan currently owns exactly one recoverable accepted run.
- Whether the recovery summary should remain a human-oriented report only, or also expose a small machine-readable CLI/JSON shape during implementation.
