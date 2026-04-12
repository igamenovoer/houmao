## Why

Claude local-interactive gateway mail notification can starve when the shared TUI tracker keeps `turn.phase=active` after the visible Claude prompt has returned to idle freeform input. The current Claude Code signal profile can scan full tmux scrollback for historical thinking/spinner rows, so stale transcript text can make a submit-ready prompt look busy indefinitely.

## What Changes

- Scope Claude Code activity detection to the current latest-turn region rather than arbitrary historical scrollback.
- Treat historical Claude thinking/spinner/tool rows above the current prompt anchor as non-current evidence so they cannot downgrade prompt readiness or keep `turn.phase=active`.
- Preserve real live Claude activity detection for current spinner/tool rows, interruptable footers, slash overlays, and active draft surfaces.
- Add regression coverage using a full-scrollback Claude capture shape with old thinking/spinner rows followed by a current `Worked for ...` completion marker and empty prompt.
- Keep gateway mail-notifier readiness gating unchanged; the notifier should resume once tracked TUI state correctly reports prompt readiness.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `versioned-tui-signal-profiles`: tighten Claude Code profile signal scoping so current active evidence comes from the latest turn region rather than stale transcript history.
- `official-tui-state-tracking`: require authoritative tracked state to report ready posture for submit-ready Claude surfaces even when older scrollback still contains historical activity rows.

## Impact

- Affected code: `src/houmao/shared_tui_tracking/apps/claude_code/profile.py`, related Claude prompt/activity helper code, and shared tracker tests.
- Affected tests: Claude shared TUI tracking unit tests and live tracker regression tests; optional fixture additions under `tests/fixtures/shared_tui_tracking/claude/`.
- Affected systems: attached gateway and direct server fallback TUI state both benefit because they consume the shared tracker core.
- No public API shape changes, dependency changes, or breaking changes are intended.
