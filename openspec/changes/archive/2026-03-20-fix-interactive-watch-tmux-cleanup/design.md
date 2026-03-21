## Context

The interactive-watch workflow in `src/houmao/explore/claude_code_state_tracking/interactive_watch.py` starts a run by creating a run root, launching a tmux-backed Claude session, starting a passive terminal recorder, writing watch metadata, launching a dashboard tmux session, and then waiting for the dashboard to report `running`.

That flow currently behaves like a plain sequence of side effects rather than a resource-owning transaction. `stop_interactive_watch()` already contains explicit cleanup for successful runs, but `start_interactive_watch()` does not unwind partially created resources when a later startup step fails. It also does not handle operator interruption during startup as a cleanup path. Because the shared tmux launcher enables `remain-on-exit`, a failed or abandoned startup can leave visible `cc-track-watch-*`, `cc-track-dashboard-*`, and `HMREC-*` sessions behind even when the run never reached a usable steady state.

The design constraint is to fix that leak without changing the intended operator workflow for successful runs: `start` remains long-lived and manual, and the operator still owns the later `stop` call for a healthy interactive run.

## Goals / Non-Goals

**Goals:**
- Make interactive-watch startup transactional so partial runs do not leak tmux or recorder sessions.
- Clean up best-effort on both ordinary startup failures and operator interruption during startup.
- Preserve run-local artifacts and failure evidence on disk even when live tmux resources are reaped.
- Keep successful `start` behavior unchanged: a healthy run remains active until explicit `stop`.
- Add tests that lock down the startup failure and interruption cleanup contract.

**Non-Goals:**
- Changing the steady-state `start` / `inspect` / `stop` user workflow into an auto-closing workflow.
- Removing `remain-on-exit` globally from the shared tmux launcher.
- Redesigning terminal-record controller internals beyond what interactive-watch needs for reliable cleanup.
- Deleting failed run roots or suppressing failure artifacts that are still useful for debugging.

## Decisions

### Decision 1: Startup becomes an owned-resource transaction

**Decision:** Track which workflow-owned resources were created during `start_interactive_watch()` and unwind them in reverse order if a later startup step fails.

Tracked resources include:
- the Claude tmux session name
- the dashboard tmux session name
- the terminal-record run root and derived `HMREC-*` session identity
- whether watch manifest/live-state files were already written

**Rationale:** The leak is caused by partial success, not by the steady-state stop path. A startup transaction is the smallest change that addresses the real failure mode.

**Alternatives considered:**
- Rely only on `stop_interactive_watch()` and require callers to invoke it after failed `start`: rejected because startup callers often do not have a valid, fully returned result to stop.
- Remove `remain-on-exit` so dead panes disappear automatically: rejected because that hides evidence rather than fixing lifecycle ownership.

### Decision 2: Cleanup uses best-effort recorder stop first, tmux kill fallback second

**Decision:** When startup cleanup sees that terminal-record state exists, it first attempts `stop_terminal_record(run_root=...)`. If that path cannot run or does not fully reap the recorder session, cleanup falls back to killing the deterministic `HMREC-*` tmux session directly. Claude and dashboard sessions are then killed best-effort if they exist.

**Rationale:** `stop_terminal_record()` is the authoritative path because it finalizes recorder metadata correctly. A direct tmux kill is still necessary as a fallback for partially initialized or failed recorder starts.

**Alternatives considered:**
- Only kill tmux sessions directly: rejected because it bypasses recorder finalization when the recorder is healthy enough to stop normally.
- Only call `stop_terminal_record()`: rejected because startup failure can happen before recorder state is fully usable.

### Decision 3: Startup interruption is treated as a cleanup-triggering failure class

**Decision:** Wrap startup in a guard that performs the same best-effort cleanup for both ordinary exceptions and `KeyboardInterrupt`, then re-raises the original failure.

**Rationale:** Operator interruption during startup is a primary source of leaked sessions, and Python does not route `KeyboardInterrupt` through a normal `except Exception` block.

**Alternatives considered:**
- Let `KeyboardInterrupt` escape without cleanup: rejected because it preserves the current bug.
- Install process-global signal handlers: rejected because a local startup guard is simpler and less invasive for this CLI.

### Decision 4: Failed startup preserves artifact evidence but marks the run failed

**Decision:** If watch manifest/live-state files already exist, startup cleanup updates live-state to `failed` with `last_error`, preserves logs and artifacts under the run root, and removes only live tmux/recorder resources.

**Rationale:** The workflow exists for debugging state tracking. Operators still need the failure evidence even when live resources are reaped.

**Alternatives considered:**
- Delete the entire run root on failed startup: rejected because it discards the exact evidence needed to debug the failure.

### Decision 5: Successful runs remain manual and docs must say so explicitly

**Decision:** Keep the successful run contract unchanged: `start` leaves the run active, `inspect` reports current state, and `stop` is required to finalize analysis and reap owned sessions. Update the workflow docs to distinguish this intentional long-lived state from failed-startup leaks.

**Rationale:** The current live-debugging workflow depends on the operator being able to keep Claude and the dashboard open for manual prompting.

**Alternatives considered:**
- Auto-stop after dashboard start or after a timeout: rejected because it breaks the core purpose of interactive watch.

## Risks / Trade-offs

- [Cleanup path masks the original startup error] -> Mitigation: preserve and re-raise the original exception, record it in live-state, and treat cleanup failures as secondary details.
- [Best-effort cleanup kills a session not owned by this run] -> Mitigation: only target deterministic names derived from the run root and only after the run has claimed them during startup.
- [Recorder fallback kill leaves incomplete recorder metadata] -> Mitigation: attempt normal `stop_terminal_record()` first and preserve run-root evidence when fallback is necessary.
- [Docs still confuse intentional long-lived runs with leaks] -> Mitigation: update interactive-watch usage docs to say that successful `start` is expected to leave tmux sessions alive until explicit `stop`.

## Migration Plan

1. Add startup resource tracking and cleanup helpers to `interactive_watch.py`.
2. Update startup exception handling to clean up on ordinary failure and `KeyboardInterrupt`.
3. Mark partially initialized runs failed when metadata exists, while preserving logs and run artifacts.
4. Add unit tests for dashboard-start failure, recorder-start failure, and startup interruption cleanup.
5. Update interactive-watch workflow docs to state that only failed or interrupted startup is auto-reaped; healthy runs still require explicit `stop`.

Rollback is straightforward: revert the interactive-watch cleanup changes and tests. No data migration is required.

## Open Questions

None for proposal readiness. The behavioral boundary is clear: successful runs remain manual; failed or interrupted startup must not leave owned tmux resources behind.
