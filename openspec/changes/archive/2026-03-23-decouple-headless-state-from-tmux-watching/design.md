## Context

The repository already has a clear architectural split between interactive TUI agents and managed headless agents.

- TUI agents are observation-driven. `houmao-server` continuously reduces raw host-observed terminal state through the tracked-TUI pipeline and explicitly assumes that users may interact with the terminal surface at any time.
- Managed headless agents are intended to be controller-driven. `houmao-server` accepts a headless turn, starts a background worker, runs the underlying CLI tool, and persists durable turn artifacts such as stdout, stderr, and exit status.

The current headless implementation still leaks one TUI-style assumption into that controller-owned path: `_reconcile_headless_active_turn()` inspects tmux session topology and can mutate active turn truth from tmux window visibility. That makes tmux observation an implicit authority for headless state even though headless turns are supposed to be owned by server actions and underlying CLI execution.

This drift showed up concretely in the ping-pong demo: a headless Claude turn was still running and emitting machine-readable output, but the server downgraded the turn to `unknown` because reconciliation did not see the expected tmux window identity. The problem is not the use of tmux itself; the problem is letting tmux watching define headless turn truth.

## Goals / Non-Goals

**Goals:**
- Make managed headless turn state controller-owned and execution-evidence-driven.
- Use underlying CLI tool reporting, return codes, and durable runner artifacts as the primary headless truth source.
- Preserve tmux as an execution container, attach surface, and best-effort control transport for headless sessions.
- Support restart recovery for active headless turns without requiring tmux pane or window watching.
- Treat unexpected headless process death as normal terminal execution failure or interruption handling rather than as a TUI-style observation anomaly.

**Non-Goals:**
- Change the tracked-TUI architecture or reduce TUI state from anything other than host-observed surface evidence.
- Remove tmux from the headless runtime model.
- Introduce a new public streaming protocol for managed headless turns.
- Classify whether an unexpected process death came from a human operator versus any other external cause.

## Decisions

### Decision: Headless turn truth is execution-owned, not tmux-observed

Managed headless turn state will be determined from server-owned execution evidence in this order:

1. durable terminal-result artifacts written by the headless runner,
2. underlying CLI exit or return status,
3. parsed machine-readable stdout events,
4. explicit server-owned interrupt intent, and
5. durable process-liveness evidence for restart recovery.

tmux visibility may still be used for attach, cleanup, and last-resort control, but it is not allowed to finalize, downgrade, or reinterpret a headless turn outcome.

Rationale:

- This matches the intended headless control model: `houmao-server` owns turn admission and the underlying CLI tool owns the execution result.
- It avoids reintroducing TUI watch semantics under a different name.
- It makes unexpected process death a normal execution condition rather than a terminal-surface inference problem.

Alternatives considered:

- Keep tmux-window reconciliation and only fix the current naming bug: rejected because it preserves the wrong authority boundary.
- Remove tmux entirely from headless execution: rejected because tmux inspectability and operator attachment are still useful and already part of the runtime contract.

### Decision: Extend durable runner evidence with explicit process metadata for restart recovery

The headless runner will continue writing durable output artifacts (`stdout`, `stderr`, exit marker) and will also persist durable execution metadata sufficient for post-restart reconciliation. That metadata should include the live execution identity needed to answer “is the CLI still running?” without looking at tmux panes.

The design target is an additive artifact set such as:

- `stdout.jsonl`
- `stderr.log`
- `exitcode` or richer terminal-result marker
- `process.json` written by the runner and containing launch-time process identity and launch timing

`process.json` is part of the same runner-owned artifact family as `stdout`, `stderr`, and exit status markers. It should capture whichever launch-time execution identity is reliably available for restart-time liveness and interrupt checks, ideally including both wrapper-shell and child-tool identity when practical. A one-time launch-time tmux metadata lookup is acceptable if needed to capture that identity, but the metadata must be persisted as durable execution evidence and must not depend on later tmux observation.

The runner owns writing `process.json`; the service layer mirrors the needed fields additively into managed-headless persistence models. Live in-process control handles remain the first choice while the server is still running, but after restart the server uses durable process metadata plus durable result artifacts instead of tmux window names.

Rationale:

- Durable result artifacts already exist; restart recovery needs only one more authority source for “still active” versus “died before completion.”
- Persisted process metadata fits the user’s stated model that an externally killed one-off `claude -p` or `codex exec` is just ordinary process death.

Alternatives considered:

- Treat every restart-time active turn with no result marker as unrecoverable/blocked: rejected because it would make restart behavior unnecessarily pessimistic.
- Recover liveness by scanning tmux windows or panes: rejected because that is exactly the watch-plane leakage this change is removing.

### Decision: Reconciliation becomes execution refresh, not watch-plane inference

The current `_reconcile_headless_active_turn()` style logic will be conceptually replaced by a refresh step that only asks:

- Is there durable terminal result evidence?
- If not, is there a live in-memory execution handle while the server is still running?
- If not, does durable process metadata indicate that the underlying execution is still live?
- If not, was an interrupt requested?

The resulting status mapping is:

- successful terminal result -> `completed`
- non-zero terminal result -> `failed`
- execution ended after server-recorded interrupt -> `interrupted`
- execution ended without terminal result and without interrupt intent -> `failed`
- no terminal result and execution still live -> `active`

The same refresh rules apply uniformly across existing managed-headless call sites unless a specific exception is documented. They also apply to worker finalization when a turn ends without an exit marker: missing terminal result plus no live execution plus no interrupt intent fails closed to `failed`, not `unknown`.

`unknown` is no longer part of the normal managed-headless lifecycle. Legacy or corrupt records that lack the new execution evidence should fail closed to `failed` with explicit diagnostics rather than preserving `unknown` as a public recovery bucket.

Rationale:

- This makes headless state machine transitions explicit and testable.
- It matches the desired semantics that user intervention does not need a special classification; it is just execution death unless the server itself requested interrupt.

Alternatives considered:

- Preserve `unknown` as a common fallback for any inconclusive headless recovery: rejected because it weakens the controller-owned contract and makes automation harder to reason about.

### Decision: Interrupt remains layered, with tmux only as a fallback transport

Managed headless interrupt should use the most authoritative control path available:

1. live in-memory execution handle, when the server still owns it,
2. persisted process identity after restart, when available,
3. tmux-targeted kill as a best-effort fallback.

This layering applies to the service-layer interrupt path as well as the runner internals. The service must first attempt the live execution handle it already owns, then fall back to persisted process identity after restart or thread loss, and only then use tmux-targeted kill as a last-resort transport.

The interrupt outcome is still recorded through server-owned interrupt intent plus later execution termination, not through tmux observation.

Rationale:

- This preserves current operational utility without elevating tmux to state authority.
- It also gives restart-time interrupt a clean path if durable process metadata is available.

Alternatives considered:

- Keep tmux kill as the only interrupt path: rejected because it overloads the execution container with lifecycle authority.

### Decision: Detailed headless state continues exposing tmux inspectability as auxiliary posture

Managed headless detail should still expose `tmux_session_live` and similar inspectability fields, because those are useful for operators. But those fields are auxiliary diagnostics, not turn truth.

This means:

- `last_turn_status`, `last_turn_result`, `last_turn_returncode`, and related fields come from turn records and execution evidence,
- `can_accept_prompt_now` comes from controller operability plus active-turn authority, and
- tmux liveness may explain degraded operability without rewriting a turn result.

Rationale:

- Operators still want to know whether a headless session is attachable.
- Callers should not have to reverse-engineer whether tmux liveness changed the meaning of a turn result.

## Risks / Trade-offs

- [PID identity can become stale or be reused] → Mitigation: persist launch timestamps and whichever runner and child identity is reliably available, and prefer explicit terminal-result markers over liveness checks whenever artifacts exist.
- [Durable artifact writes may be observed mid-flight] → Mitigation: write `process.json` and other small result markers via temp-file-and-rename or equivalent atomic-enough discipline, and prefer monotonic refresh rules that never downgrade a confirmed terminal state.
- [Legacy active-turn records may lack the new execution metadata] → Mitigation: fail closed to `failed` with explicit diagnostics rather than preserving `unknown`, accepting that very old in-flight turns may not survive restart cleanly in exchange for a simpler public contract.
- [Interrupt after restart may still need tmux fallback in some cases] → Mitigation: document tmux as fallback control transport only and keep that fallback isolated from state reconciliation.

## Migration Plan

1. Extend the headless runner artifact contract with durable execution metadata suitable for restart-time liveness checks.
2. Update managed headless persistence models to carry the new evidence paths or fields additively and align public status vocabulary with the new failed-with-diagnostic semantics.
3. Replace tmux-window-based headless reconciliation and finalization with uniform execution-evidence refresh logic.
4. Update service-layer and runner interrupt handling to prefer live or persisted execution identity before tmux fallback.
5. Update managed headless state/detail projection and demo-facing reporting so tmux liveness is auxiliary diagnostic posture only.
6. Add regression coverage for successful completion, failure, missing-exit-marker finalization, restart recovery, legacy no-metadata records, and externally killed process scenarios.
7. Re-run headless demo and managed-agent flows that previously observed `unknown` drift from tmux watching.

Rollback strategy:

- If rollout reveals an issue in the new recovery logic, revert reconciliation to a simpler artifact-only rule while keeping the new metadata additive.
- Do not reintroduce tmux watching as turn-truth authority during rollback; if necessary, fail closed to explicit `failed` or temporarily unavailable behavior instead.
