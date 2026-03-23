## 1. Startup Cleanup Plumbing

- [x] 1.1 Add interactive-watch startup resource tracking in `src/houmao/explore/claude_code_state_tracking/interactive_watch.py` so the workflow knows which tmux and recorder resources it owns during `start`
- [x] 1.2 Implement best-effort startup cleanup helpers that stop terminal-record via `stop_terminal_record()` when possible and fall back to direct tmux session kill for the run-owned `HMREC-*`, dashboard, and Claude sessions
- [x] 1.3 Wrap `start_interactive_watch()` so ordinary startup failures and `KeyboardInterrupt` both trigger cleanup before the original failure is re-raised
- [x] 1.4 Update watch live-state handling so partially initialized runs that already wrote metadata are marked `failed` with retained failure evidence under the run root

## 2. Verification Coverage

- [x] 2.1 Add unit tests in `tests/unit/explore/test_claude_code_state_tracking_interactive_watch.py` for dashboard-start failure after Claude and recorder startup
- [x] 2.2 Add unit tests for startup interruption cleanup and for recorder-stop fallback behavior when the recorder did not initialize cleanly
- [x] 2.3 Run the relevant focused test suite for interactive-watch and terminal-record lifecycle behavior

## 3. Operator Lifecycle Documentation

- [x] 3.1 Update `scripts/explore/claude-code-state-tracking/README.md` to state that successful `start` runs remain live until explicit `stop`
- [x] 3.2 Document that failed or interrupted startup is expected to auto-reap `cc-track-*` and `HMREC-*` tmux sessions while preserving run-root artifacts for debugging
