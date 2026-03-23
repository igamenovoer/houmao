## 1. Shared Watch Core

- [x] 1.1 Extract the current replay state reducer into a shared stream-driven component that can consume live appended observations and offline replay observations with the same detector and ReactiveX timing semantics.
- [x] 1.2 Add coverage proving the shared reducer handles ready, active, interrupted, known-failure, success-settle, and settle-reset behavior consistently across live-style and replay-style feeds.

## 2. Interactive Driver And Dashboard

- [x] 2.1 Add the interactive watch driver under `scripts/explore/claude-code-state-tracking/` with `start`, `inspect`, and `stop` workflows that build a Claude brain home from `tests/fixtures/agents/brains/` through shared Python builder APIs into a run-local `runtime/` subtree, launch its `launch.sh` in tmux, and manage the recorder, runtime observer, and dashboard process/session without Houmao lifecycle CLI subprocesses.
- [x] 2.2 Implement the live dashboard so it tails recorder/runtime artifacts, renders the simplified public state with colored tokens, and persists `latest_state.json`, `state_samples.ndjson`, and `transitions.ndjson`.
- [x] 2.3 Persist run metadata and attach commands in a stable manifest so `inspect --json` can expose the current run, attach points, and live-state artifact paths.

## 3. Finalization And Debugging Artifacts

- [x] 3.1 Implement interactive-run finalization on `stop`, including groundtruth, replay, comparison, and a developer-readable pass/fail report for that run.
- [x] 3.2 Add optional env-gated dense trace outputs for local detector/reducer/dashboard debugging without making trace mode mandatory for normal runs.

## 4. Validation And Documentation

- [x] 4.1 Add targeted tests for the interactive watch command surface, live artifact persistence, inspect payloads, and finalization/report generation.
- [x] 4.2 Run at least one successful interactive watch session and one interrupted interactive watch session, capture the resulting artifacts/report, and document the operator workflow in `scripts/explore/claude-code-state-tracking/README.md`.
