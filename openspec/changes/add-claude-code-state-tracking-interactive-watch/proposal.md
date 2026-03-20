## Why

The current Claude Code state-tracking explore harness proves the model through scripted batch scenarios, but it does not provide the operator-facing interactive workflow needed to watch state changes live while prompting Claude manually. We need a companion interactive watch pack so developers can drive a real Claude session, observe the simplified state model on a live dashboard, and capture replay-grade artifacts when behavior looks wrong.

## What Changes

- Add an interactive explore workflow under `scripts/explore/claude-code-state-tracking/` that launches `claude-yunwu` in tmux, starts recorder-backed observation, and keeps the session available for manual prompting.
- Add a live dashboard that renders the simplified state model and updates as the interactive Claude session changes, including turn phase, last terminal result, diagnostics posture, and detector notes/signals.
- Add inspect/report artifacts for interactive runs so a developer can correlate dashboard state with raw recorder snapshots, runtime liveness evidence, and replay/groundtruth output after the session ends.
- Add an interactive operator workflow for start, attach, observe, inspect, stop, and post-run analysis, following the same style as the existing shadow-watch demo but without depending on `houmao-server`.
- Add guidance for debugging interactive mismatches by reusing raw capture artifacts and, when needed, adding dense harness-local tracing rather than guessing.

## Capabilities

### New Capabilities
- `claude-code-state-tracking-interactive-watch`: Interactive tmux-backed Claude watch workflow with a live dashboard, inspectable artifacts, and post-run replay/groundtruth analysis for the simplified state model.

### Modified Capabilities
- None.

## Impact

- Affected code: `scripts/explore/claude-code-state-tracking/`, `src/houmao/explore/claude_code_state_tracking/`, and interactive dashboard/reporting helpers.
- Affected systems: tmux session management, terminal recorder integration, ReactiveX replay/observation flow, and developer-facing explore docs.
- Affected workflows: manual Claude state-observation and debugging for the simplified state model.
