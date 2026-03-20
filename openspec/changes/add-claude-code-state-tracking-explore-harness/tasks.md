## 1. Harness Scaffold And Live Capture

- [ ] 1.1 Create the `scripts/explore/claude-code-state-tracking/` module and CLI scaffold for live capture, replay, and comparison commands.
- [ ] 1.2 Implement tmux-based live session startup for `claude-yunwu`, including preflight checks, isolated run-root creation, and scenario-step driving.
- [ ] 1.3 Integrate the existing terminal recorder in default `passive` mode and persist harness-owned `drive_events.ndjson` alongside the recorder run artifacts.
- [ ] 1.4 Add subprocess-owned fault-injection launch support for deliberate Claude startup and mid-turn network-error scenarios, preferring syscall-level injection in the first pass.
- [ ] 1.5 Add runtime liveness observation artifacts that distinguish tmux-target availability, pane availability, and Claude child-process liveness during scenario capture.

## 2. Detector And Groundtruth Pipeline

- [ ] 2.1 Implement a closest-compatible Claude detector abstraction with a first family detector for nearby Claude Code `2.1.x` surfaces.
- [ ] 2.2 Implement current-region, recency-aware, ANSI-aware signal extraction over recorded `pane_snapshots.ndjson`.
- [ ] 2.3 Implement the offline groundtruth classifier that derives foundational observables, current turn state, terminal outcomes, and abrupt process-loss diagnostics from recorded content plus runtime observations without importing `houmao-server` tracker code.
- [ ] 2.4 Add a maintained state-discovery signal-note workflow so newly discovered stable Claude signals from harness work are recorded formally rather than left implicit in code.

## 3. ReactiveX Replay Tracker And Comparison

- [ ] 3.1 Implement a ReactiveX-driven replay observation stream over recorded pane snapshots and runtime diagnostics without manual timer bookkeeping.
- [ ] 3.2 Implement the independent replay tracker that emits the simplified turn model, success-settle timing, and abrupt process-loss diagnostics from recorded observations.
- [ ] 3.3 Implement comparison artifacts that highlight first divergence, transition-order mismatches, missed intervals, false positive terminal outcomes, and diagnostics mismatches such as `tui_down` versus `unavailable`.

## 4. Initial Scenario Corpus And Verification

- [ ] 4.1 Add the initial scenario set for success, interruption, slash-noise-during-active, current known failure, stale-known-failure-before-later-success, ready-noise-without-submit, ambiguous-surface-unknown-and-recovery, settle-reset-before-success, startup-network-failure-injected, mid-turn-network-failure-injected, process-killed-tmux-still-alive, and target-disappeared-unavailable.
- [ ] 4.2 Ensure the scenario corpus covers the important public paths `ready`, `active`, `unknown`, `success`, `interrupted`, and `known_failure`, plus stale-history suppression, settle reset behavior, and abrupt diagnostics paths for process-down versus target-unavailable.
- [ ] 4.3 Produce one operator-oriented run workflow that captures a live scenario, replays it, and writes `groundtruth_timeline`, `replay_timeline`, and comparison artifacts under `tmp/explore/claude-code-state-tracking/`.
- [ ] 4.4 Validate the harness against at least one real Claude recording plus the deliberate injected-failure and abrupt process-loss paths, document the observed version plus any known limitations of the closest-compatible detector selection, and formalize any newly discovered stable signals as state-discovery notes.
