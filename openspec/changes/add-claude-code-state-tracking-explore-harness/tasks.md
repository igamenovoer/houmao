## 1. Harness Scaffold And Live Capture

- [ ] 1.1 Create the `scripts/explore/claude-code-state-tracking/` module and CLI scaffold for live capture, replay, and comparison commands.
- [ ] 1.2 Implement tmux-based live session startup for `claude-yunwu`, including preflight checks, isolated run-root creation, and scenario-step driving.
- [ ] 1.3 Integrate the existing terminal recorder in default `passive` mode and persist harness-owned `drive_events.ndjson` alongside the recorder run artifacts.

## 2. Detector And Groundtruth Pipeline

- [ ] 2.1 Implement a closest-compatible Claude detector abstraction with a first family detector for nearby Claude Code `2.1.x` surfaces.
- [ ] 2.2 Implement current-region, recency-aware, ANSI-aware signal extraction over recorded `pane_snapshots.ndjson`.
- [ ] 2.3 Implement the offline groundtruth classifier that derives foundational observables, current turn state, and terminal outcomes from recorded content without importing `houmao-server` tracker code.

## 3. ReactiveX Replay Tracker And Comparison

- [ ] 3.1 Implement a ReactiveX-driven replay observation stream over recorded pane snapshots without manual timer bookkeeping.
- [ ] 3.2 Implement the independent replay tracker that emits the simplified turn model and success-settle timing from recorded observations.
- [ ] 3.3 Implement comparison artifacts that highlight first divergence, transition-order mismatches, missed intervals, and false positive terminal outcomes.

## 4. Initial Scenario Corpus And Verification

- [ ] 4.1 Add the initial scenario set for success, interruption, and slash-noise-during-active Claude runs.
- [ ] 4.2 Produce one operator-oriented run workflow that captures a live scenario, replays it, and writes `groundtruth_timeline`, `replay_timeline`, and comparison artifacts under `tmp/explore/claude-code-state-tracking/`.
- [ ] 4.3 Validate the harness against at least one real Claude recording and document the observed version plus any known limitations of the closest-compatible detector selection.
