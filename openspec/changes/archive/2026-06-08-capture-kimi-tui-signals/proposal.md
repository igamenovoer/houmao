## Why

Kimi Code TUI tracking should be built from recorded, manually labeled live evidence rather than from guessed string heuristics. The next Kimi TUI step is to capture high-rate and low-rate replay data, design minimal stable signals from that data, and verify the Kimi tracking module against labels before folding it into broader Kimi TUI support.

## What Changes

- Capture logged-in live Kimi Code TUI sessions under repo-local `tmp/` with replay-grade tmux pane snapshots.
- Record high-rate snapshots at about 10 fps and derive low-rate snapshots at about 2 fps from the high-rate stream.
- Preserve ANSI/style data and other timing/runtime metadata needed for style-aware signal design.
- Manually label Kimi readiness, activity, draft editing, approval-blocked, interruption, failure, and completion states over sample ranges.
- Investigate Kimi TUI source code so signal contracts distinguish stable component structure from accidental rendered text.
- Require at least 5 labeled live sessions for detector development and at least 3 separate labeled live sessions held out as a test set.
- Ensure every captured session spans multiple TUI state changes rather than representing a single static surface.
- Create provider-specific Kimi TUI signal design artifacts that describe stable structural, style, temporal, and bounded semantic signals.
- Update terminal recorder and replay tooling as needed so `kimi` runs can be captured, sampled, decimated, labeled, replayed, and validated.
- Implement the Kimi shared TUI tracking profile only after the labeled capture corpus exists.
- Verify Kimi tracker output against both 10 fps and derived 2 fps labeled timelines, including the held-out test sessions.
- Treat this change as the evidence-first prerequisite for the broader `add-kimi-tui-support` change.

## Capabilities

### New Capabilities

- `kimi-tui-signal-corpus`: Capture-first Kimi TUI evidence corpus, Kimi signal design artifacts, and label-driven Kimi tracker verification.

### Modified Capabilities

- `terminal-record-artifacts`: Recorder artifacts support high-rate Kimi captures, derived low-rate streams, style-preserving snapshots, and repo-local `tmp/` corpus roots.
- `terminal-record-replay`: Replay and analysis support Kimi-labeled runs and compare derived parser/tracker state against labels.
- `shared-tui-tracking-recorded-validation`: Recorded validation uses Kimi labeled timelines as public tracked-state ground truth for both high-rate and low-rate replay.
- `versioned-tui-signal-profiles`: Kimi signal profile design and implementation are gated by recorded, labeled evidence and style-aware signal contracts.
- `official-tui-state-tracking`: Kimi live TUI state tracking is verified from recorded snapshots before being treated as maintained supported tracking behavior.

## Impact

- Affected tooling includes `tools/terminal_record`, `src/houmao/terminal_record`, replay/analyze commands, label schema handling, and recorded-validation helpers.
- Affected tracking code includes `src/houmao/shared_tui_tracking/` Kimi app profile registration, detector implementation, temporal hints, and tests.
- Affected artifacts include repo-local capture roots under `tmp/kimi-tui-tracking/`, Kimi signal design notes under the change context/design/contracts area, and committed or fixture-ready labeled samples when implementation promotes evidence to tests.
- The active `add-kimi-tui-support` change should be updated later to depend on this evidence-first work rather than starting with Kimi parser/profile heuristics.
