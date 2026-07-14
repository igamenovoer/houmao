## Why

We need labeled tmux recordings of Claude Code, Codex CLI, and Kimi Code sessions to train and validate a detector that predicts two binary states from raw terminal snapshots:

- `can_accept_input` — the CLI is non-busy and a new prompt would start immediately.
- `has_pending_message` — the CLI already holds a user prompt in its own queue for a later turn.

The target lifecycle is: CLI ready → first prompt submitted → CLI processing → second prompt submitted while processing → prompt becomes pending in the CLI → pending prompt is dequeued and processed → CLI ready again. The existing shared TUI tracking demo pack can drive only isolated tmux input actions and has no lifecycle-shaped harness for this sequence. We need a small, tracker-blind capture runner that produces frozen recordings and a per-snapshot label template.

## What Changes

- Add a new capture runner under `scripts/qualification/tui-prompt-admission/` that drives the full ready→processing→pending→processing→ready lifecycle for one provider.
- The runner launches an unattended managed agent, discovers the provider tmux pane, and starts a 20 Hz active terminal recording before the first input event.
- The lifecycle is driven entirely through tmux `send_text` / `send_key` actions and fixed or pattern-based waits. No gateway commands are required for the core capture.
- After the recording is frozen, the runner emits a label template (`labels.json`) with two binary flags per snapshot: `can_accept_input` and `has_pending_message`.
- The runner freezes source evidence (`pane_snapshots.ndjson`, `input_events.ndjson`, `session.cast`, scenario manifest) with SHA-256 digests before any labeling or replay.
- All runner code lives under `scripts/qualification/tui-prompt-admission/`; this change does not modify `src/houmao/`.
- Add unit tests for the runner's lifecycle compiler and freeze gate.

## Capabilities

### New Capabilities
- `tui-pending-state-capture-runner`: Live tmux capture runner that produces detector-training recordings and binary per-snapshot labels (`can_accept_input`, `has_pending_message`) for Claude, Codex, and Kimi.

### Modified Capabilities
- (none — this change is strictly test-data collection under `scripts/`; it does not change gateway control APIs, tracker public state schemas, or `houmao-mgr` CLI semantics.)

## Impact

- Affects `scripts/qualification/tui-prompt-admission/` with new runner scripts, lifecycle manifests, and label templates.
- Reuses existing capabilities: `shared-tui-tracking-demo-pack`, `terminal-record-artifacts`, and the long-horizon launcher.
- Does not modify `src/houmao/`, gateway control APIs, tracker schemas, or CLI semantics.
