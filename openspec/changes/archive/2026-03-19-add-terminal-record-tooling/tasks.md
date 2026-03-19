## 1. Recorder Lifecycle

- [x] 1.1 Create the `tools/terminal_record/` module structure, CLI entrypoint, and recorder run-root/state models.
- [x] 1.2 Implement `start`, `status`, and `stop` flows that target an existing tmux session or explicit pane and persist live recorder state.
- [x] 1.3 Add validation and tests for target-session discovery, ambiguous multi-pane failures, and orderly shutdown/finalization.

## 2. Capture Pipelines

- [x] 2.1 Integrate visual recording through the repo-owned `pixi run asciinema` task backed by `extern/orphan/bin/asciinema-x86_64-unknown-linux-gnu`.
- [x] 2.2 Implement continuous tmux pane snapshot sampling plus final-stop snapshot capture for the targeted pane.
- [x] 2.3 Persist synchronized run artifacts including manifest, live/finalized state, cast output, pane snapshots, and structured input-event files.

## 3. Active And Passive Modes

- [x] 3.1 Implement `active` mode so the recorder exposes a recorder-owned attach path and records managed interactive input posture.
- [x] 3.2 Implement `passive` mode so the recorder observes a live tmux session without requiring users to abandon direct tmux inspection.
- [x] 3.3 Add capture-authority and taint metadata so downstream tooling can distinguish authoritative active runs from passive or degraded runs.

## 4. Managed Control Input Integration

- [x] 4.1 Extend repo-owned managed `send-keys` delivery so active recorder runs receive structured managed control-input events for the same tmux-backed session.
- [x] 4.2 Persist recorder-aware managed control-input events with stable timing/session references and cover the integration with runtime tests.

## 5. Replay, Labels, And Validation

- [x] 5.1 Implement replay/analyze flows that derive parser-facing and state-tracking observations from recorded pane snapshots without requiring a live tmux session.
- [x] 5.2 Implement structured label artifacts for recorded samples or sample ranges and support storing them in the run root or exported fixture layout.
- [x] 5.3 Add end-to-end tests and maintainer docs covering recorder lifecycle, artifact semantics, active/passive guarantees, and replay usage.
