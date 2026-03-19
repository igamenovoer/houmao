## 1. Shared Rx Lifecycle Kernel

- [ ] 1.1 Introduce a shared lifecycle observation and anchor contract for ordered parsed TUI events plus server/runtime-owned turn anchors.
- [ ] 1.2 Extract or refactor the ReactiveX timing logic into a shared lifecycle kernel that covers unknown-to-stalled timing, stalled recovery, and completion debounce without hand-rolled mutable timestamp reducers.
- [ ] 1.3 Re-point the existing CAO runtime monitor to the shared kernel while preserving current runtime behavior and test coverage.

## 2. Server Lifecycle Contract

- [ ] 2.1 Extend `houmao-server` tracked-state models, route payloads, and client surfaces with structured lifecycle authority metadata for `turn_anchored` vs `unanchored_background` monitoring.
- [ ] 2.2 Record and manage server-owned turn anchors for supported control paths such as terminal input submission, including anchor-active vs anchor-absent or lost state.

## 3. Server Tracker Migration

- [ ] 3.1 Replace the imperative server lifecycle reducer in `src/houmao/server/tui/tracking.py` with an adapter that feeds the shared Rx kernel from the existing worker-owned observation stream.
- [ ] 3.2 Keep continuous watch authoritative for readiness, blocked, failed, unknown, stalled, and visible-state stability while suppressing unanchored `candidate_complete` and `completed`.
- [ ] 3.3 Wire anchored completion monitoring through the server service path so turn-anchored sessions can still expose `candidate_complete` and `completed` with the existing stability window semantics.
- [ ] 3.4 Update demo or monitor consumers that currently assume the server lifecycle state is always turn-authoritative so they read the new lifecycle authority metadata instead of recreating timer semantics locally.

## 4. Verification And Documentation

- [ ] 4.1 Add deterministic scheduler-driven unit tests for the shared lifecycle kernel and the server adapter covering startup churn, stalled recovery, debounce reset, and anchored vs unanchored completion behavior.
- [ ] 4.2 Update server route, client, and integration tests to verify lifecycle authority metadata and server-owned turn anchoring on supported control paths.
- [ ] 4.3 Refresh relevant docs and troubleshooting references so they describe the server’s ReactiveX timing model, the continuous-watch vs turn-anchored split, and the limits of unanchored background completion.
