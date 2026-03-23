## 1. Ownership Artifact And Recovery Helpers

- [x] 1.1 Add a typed run-local ownership artifact model and atomic load/save helpers for shared tracked-TUI demo runs, including workflow kind, status, recorder run root, and owned resource roles/session names.
- [x] 1.2 Add shared tmux-session-environment publication helpers for demo-owned recovery pointers and constants for the ownership marker variables.
- [x] 1.3 Add shared discovery helpers that resolve owned tmux resources for one run from the ownership artifact first and supplement them from tmux session-environment recovery when needed.
- [x] 1.4 Add shared role-aware cleanup helpers that prefer `stop_terminal_record(run_root=...)` when recorder state is known and fall back to direct tmux session kill for remaining owned resources.

## 2. Workflow Integration

- [x] 2.1 Update `recorded-capture` to create and update the ownership artifact before `launch_tmux_session()` and as tool/recorder resources are created.
- [x] 2.2 Refactor `recorded-capture` cleanup to use the shared ownership-based recovery helpers so early startup failures and normal teardown use the same session-resolution path.
- [x] 2.3 Update live-watch startup to create and update the ownership artifact before startup completes, including tool, dashboard, and recorder-backed resources when present.
- [x] 2.4 Update live-watch failed-start cleanup, `inspect`, and `stop` to resolve workflow-owned sessions through the shared ownership bookkeeping instead of relying only on happy-path startup metadata.
- [x] 2.5 Tag recorder-owned tmux sessions with the same demo recovery pointers after recorder startup so recorder cleanup can be recovered through the shared ownership flow.

## 3. Operator Surface And Documentation

- [x] 3.1 Add a `cleanup` command to the demo driver and shell wrapper, with targeted run selection and machine-readable output suitable for recovery automation.
- [x] 3.2 Keep `stop` as the graceful live-watch finalization path and ensure `cleanup` reports recovery-oriented results without claiming finalized analysis artifacts.
- [x] 3.3 Update the demo README to document the new ownership bookkeeping, the difference between `stop` and `cleanup`, and how stale demo-owned tmux sessions are recovered.
- [x] 3.4 Update the demo config/reference docs anywhere they describe cleanup behavior so the documented session-reaping story matches the new manifest-plus-tmux-env recovery model.

## 4. Tests

- [x] 4.1 Add unit coverage for ownership artifact serialization, atomic persistence, tmux-env publication, and manifest-first plus tmux-env-fallback discovery behavior.
- [x] 4.2 Add recorded-capture tests covering failures after tmux launch but before final capture-manifest persistence, proving the run remains recoverable and cleanup reaps the owned session.
- [x] 4.3 Add live-watch tests covering failed-start cleanup, stop-time session recovery, and inspect-time liveness reporting through recovered ownership metadata.
- [x] 4.4 Add CLI-level tests for the new `cleanup` command, including recorder-backed runs and forceful recovery that does not claim graceful finalization.
