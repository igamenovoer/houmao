## Why

The current repo can inspect live tmux-backed agent sessions and can parse `shadow_only` TUI snapshots, but it does not have a repo-owned way to record a live session as reusable test evidence. We need a long-running recorder that can target an already-running agent tmux session, preserve both what the terminal showed and what managed inputs were delivered, and turn those recordings into replay-grade artifacts for parser and state-tracking tests.

## What Changes

- Add a repo-owned terminal recording tool under `tools/terminal_record/` that targets an existing tmux session or pane and runs as a long-lived recorder process with explicit `start`, `status`, and `stop` control.
- Add two recorder modes:
  - `active`, where the recorder becomes the managed interactive entrypoint and captures recorder-mediated manual input plus repo-owned managed control input for the target session.
  - `passive`, where the recorder observes an active tmux session without owning the user's normal workflow and records the visible terminal state plus exact pane snapshots.
- Persist synchronized recorder artifacts including a human-facing `asciinema` cast, exact tmux pane snapshots, structured metadata, and normalized input-event logs with explicit capture guarantees.
- Define replay/analyze artifacts so recorded tmux sessions can be labeled and reused by parser and state-tracking tests instead of relying only on hand-written static text fixtures.
- Modify managed tmux control-input behavior as needed so repo-owned `send-keys` can append recorder-visible input events when an `active` recording is targeting the same tmux session.

## Capabilities

### New Capabilities
- `terminal-record-session-control`: Start, inspect, and stop a long-running recorder process that targets an existing tmux session or pane in `active` or `passive` mode.
- `terminal-record-artifacts`: Persist recorder outputs and metadata with explicit authority boundaries for visual capture, pane snapshots, and managed input events.
- `terminal-record-replay`: Analyze and replay recorded pane snapshots as parser/state-tracking fixtures with operator-provided labels.

### Modified Capabilities
- `brain-launch-runtime`: Managed `send-keys` delivery may emit recorder-aware control-input events when a live `active` terminal recorder targets the same tmux-backed session.

## Impact

- New repo-owned tooling under `tools/terminal_record/`.
- Integration with tmux session discovery/control and possibly existing `send-keys` plumbing in `src/houmao/agents/realm_controller/backends/tmux_runtime.py` and related CLI/runtime surfaces.
- Continued use of the repo-owned `pixi run asciinema` task backed by `extern/orphan/bin/asciinema-x86_64-unknown-linux-gnu` rather than the conda package.
- New checked-in or generated replay fixtures and metadata for TUI parser/state regression testing.
