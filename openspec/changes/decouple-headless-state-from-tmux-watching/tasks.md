## 1. Durable Execution Evidence

- [ ] 1.1 Extend the tmux-backed headless runner to write runner-owned durable execution metadata, including launch-time process identity sufficient for restart-time liveness and interrupt checks, alongside stdout, stderr, and terminal result markers, and write `process.json` atomically enough for concurrent readers.
- [ ] 1.2 Update managed headless persistence models and read/write helpers to carry the new execution-evidence fields additively and align the public headless status vocabulary with failed-with-diagnostic semantics instead of normal `unknown` outcomes.

## 2. Controller-Owned Headless Lifecycle

- [ ] 2.1 Replace tmux-window-based managed headless reconciliation and finalization with a uniform execution-evidence refresh path across the existing service call sites, using live in-memory execution handles first, durable process metadata second, and failing closed when execution ends without terminal result or interrupt intent.
- [ ] 2.2 Restructure service-layer managed headless interrupt handling to consult the live runner handle first, persisted execution identity second, and tmux kill only as best-effort fallback.
- [ ] 2.3 Update managed headless summary state, detailed state, per-turn status projection, and demo-facing reporting so tmux liveness is auxiliary diagnostic posture rather than turn-truth authority.

## 3. Regression Coverage

- [ ] 3.1 Add unit tests for managed headless completion, missing-exit-marker finalization failure, interruption, legacy/no-metadata failure, and no-longer-live execution using controller-owned evidence instead of tmux watching.
- [ ] 3.2 Add restart-recovery coverage proving that active-turn reconciliation no longer depends on tmux window matching and that live execution, dead-with-no-exitcode, and legacy-metadata gaps reconcile cleanly.
- [ ] 3.3 Re-run managed-headless integration or demo coverage, including the mail ping-pong flow and reporting surfaces that previously drifted into tmux-watch-driven `unknown` state.
