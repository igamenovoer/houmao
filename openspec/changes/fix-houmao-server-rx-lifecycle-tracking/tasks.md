## 1. Safety-First Server Contract Hardening

- [x] 1.1 Extend `houmao-server` tracked-state models, route payloads, and client surfaces with structured lifecycle authority metadata for `turn_anchored` vs `unanchored_background` monitoring, including default emitted `unanchored_background` plus `absent` values.
- [x] 1.2 Record and manage server-owned turn anchors by wiring the existing `POST /terminals/{terminal_id}/input` success path through `note_prompt_submission()`, including anchor-active vs anchor-absent or lost state and auto-expiry on terminal outcome.
- [x] 1.3 Keep continuous watch authoritative for readiness, blocked, failed, unknown, stalled, and visible-state stability while suppressing unanchored `candidate_complete` and `completed` in the same payload revision that adds lifecycle authority metadata.

## 2. Shared Rx Lifecycle Kernel

- [x] 2.1 Introduce a shared lifecycle observation and anchor contract for ordered parsed TUI events plus server/runtime-owned turn anchors, with evidence scoped per anchored cycle rather than per long-lived tracker lifetime.
- [x] 2.2 Extract or refactor the ReactiveX timing logic into a shared lifecycle kernel under `src/houmao/lifecycle/` that covers unknown-to-stalled timing, stalled recovery, and completion debounce without hand-rolled mutable timestamp reducers.

## 3. Server Tracker Migration And CAO Convergence

- [x] 3.1 Replace the imperative server lifecycle reducer in `src/houmao/server/tui/tracking.py` with an adapter that feeds the shared Rx kernel from the existing worker-owned observation stream.
- [x] 3.2 Wire anchored completion monitoring through the server service path so turn-anchored sessions can still expose `candidate_complete` and `completed` with existing stability window semantics, using anchor-scoped completion subscriptions or equivalent anchor-scoped reducer state.
- [x] 3.3 Update demo or monitor consumers that currently assume the server lifecycle state is always turn-authoritative so they read the new lifecycle authority metadata instead of recreating timer semantics locally.
- [x] 3.4 Re-point the existing CAO runtime monitor to the shared kernel while preserving current runtime behavior and test coverage, but only after the server adapter and parity tests are in place.

## 4. Verification And Documentation

- [x] 4.1 Add deterministic scheduler-driven unit tests for the shared lifecycle kernel and the server adapter covering startup churn, stalled recovery, debounce reset, anchored vs unanchored completion behavior, and anchor expiry after terminal outcome.
- [x] 4.2 Update server route, client, and integration tests to verify lifecycle authority metadata, default unanchored values, server-owned turn anchoring on supported control paths, and the successful-input hook path.
- [x] 4.3 Refresh relevant docs and troubleshooting references so they describe the server’s ReactiveX timing model, the continuous-watch vs turn-anchored split, the limits of unanchored background completion, and the cross-reference from issue-002 to this fix.
