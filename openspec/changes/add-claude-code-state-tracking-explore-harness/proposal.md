## Why

The proposed `houmao-server` state model needs an external verification harness that can validate turn-state semantics without depending on the server's current tracker implementation. Right now we can record tmux sessions and we can inspect them manually, but we do not have a minimal, repeatable way to drive Claude Code, classify raw TUI state from content, and check whether an independent replay tracker reaches the same conclusions.

## What Changes

- Add a minimal explore harness under `scripts/explore/claude-code-state-tracking/` that launches `claude-yunwu` in tmux, drives scripted scenarios, and records the session with the existing terminal recorder.
- Add a content-first Claude state classifier that derives foundational observables and turn-state groundtruth from raw recorded pane snapshots, including ANSI-aware and recency-aware signal matching.
- Add an independent ReactiveX-driven replay tracker that consumes recorded snapshots and emits the simplified turn states without importing `houmao-server` tracker code.
- Add a comparison/report step that highlights mismatches between offline groundtruth and replay-detected state timelines.
- Add a small initial scenario set focused on the proposed model's highest-value cases: success, interruption, and active-turn noise such as slash-menu churn during an active turn.

## Capabilities

### New Capabilities

- `claude-code-state-tracking-explore-harness`: Capture, replay, classify, and compare Claude Code tmux sessions outside of `houmao-server` so the proposed simplified state model can be validated independently.

### Modified Capabilities

- None.

## Impact

- New explore tooling under `scripts/explore/claude-code-state-tracking/`
- New run artifacts under `tmp/explore/claude-code-state-tracking/`
- Reuse of existing `tools/terminal_record` and tmux/libtmux-based capture workflows
- New dependency on the locally available `claude-yunwu` wrapper as the live Claude launch path for scenario capture
- New dependency on `reactivex` for replay-timing semantics in the external harness
