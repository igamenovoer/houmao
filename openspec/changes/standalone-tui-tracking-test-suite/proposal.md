## Why

The standalone shared TUI tracker now has focused unit coverage, but it still lacks replay-grade validation against real recorded sessions and a maintained live watch workflow for developers. That gap makes detector and reducer regressions hard to catch, especially across Claude and Codex state transitions that only show up in actual tmux-backed sessions.

## What Changes

- Add a repo-owned recorded-session validation demo pack under `scripts/demo/shared-tui-tracking-demo-pack/` for the standalone tracker that captures real tmux sessions, probes tmux directly, preserves replay-grade artifacts, expands labeled ground truth into per-sample timelines, and compares tracker output against that ground truth without depending on `houmao-server`.
- Add an initial recorded fixture corpus with at least four critical state-transition cases across Claude and Codex, using permissive launch posture so normal fixture capture does not stall on unexpected approval or sandbox prompts.
- Add review-video generation that renders the exact recorded pane snapshots into staged 1080p frames and encodes a `libx264` `.mp4` with visible ground-truth state changes for human verification.
- Add a tool-agnostic live interactive watch workflow in the same demo pack for Claude and Codex that launches fresh runtime homes from `tests/fixtures/agents/`, records the live session, and renders a `rich` dashboard in a separate tmux session.
- Persist stable machine-readable artifacts for replay, comparison, transition logs, and live watch state under repo-owned `tmp/` subtrees so automated tests and manual investigation consume the same evidence.

## Capabilities

### New Capabilities
- `shared-tui-tracking-recorded-validation`: Capture, label, replay, compare, and visually review recorded standalone-tracker sessions for Claude and Codex.
- `shared-tui-tracking-live-watch`: Launch permissive fixture-backed live Claude and Codex sessions with recorder-backed observation and a standalone shared-tracker dashboard.

### Modified Capabilities

## Impact

- Affected code: `src/houmao/shared_tui_tracking/`, `src/houmao/terminal_record/`, direct tmux/runtime helper code used by the demo pack, `scripts/demo/shared-tui-tracking-demo-pack/`, and any supporting demo-owned Python package needed to back that demo pack.
- Affected tests and fixtures: new recorded-session fixtures, replay assertions, live-watch unit coverage, and human-review video artifacts/metadata.
- Affected tooling: terminal recorder integration, fixture-backed brain launch flows from `tests/fixtures/agents/`, and staged frame plus `ffmpeg`/`libx264` review-video generation.
- Operational posture: live capture and watch flows default to the most permissive supported tool settings to avoid unexpected operator-blocked stalls during normal validation runs.
