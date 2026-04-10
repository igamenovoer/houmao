## Why

Codex TUI tracking can remain stuck in `turn.phase=active` after the visible surface has already returned to a prompt-ready posture. In the observed failure, a historical `• Working (... esc to interrupt)` row preserved in tmux scrollback kept gateway mail notifications suppressed even though the live prompt was stable and ready for input.

## What Changes

- Narrow Codex single-snapshot activity detection so live activity is derived from the live edge of the current TUI surface rather than from arbitrary historical scrollback rows.
- Preserve spinnerless active-turn detection by continuing to use recent transcript growth as temporal active evidence when the live response region is still changing.
- Add a tracker-owned stale-active recovery path that forces `turn.phase` out of `active` after a configurable submit-ready stability window when the prompt is visibly ready, no live activity remains, and the surface stays stable.
- Set the stale-active recovery window to 5 seconds by default and implement it through the existing ReactiveX-based tracking pipeline rather than through ad hoc manual timers.
- Expose explicit tracker notes or transition evidence when stale-active recovery is what clears a stuck active turn, so drift investigation remains visible.

## Capabilities

### New Capabilities
None.

### Modified Capabilities
- `codex-tui-state-tracking`: Codex active-turn evidence must come from the live surface edge instead of stale transcript rows, while still treating live transcript growth as active work.
- `official-tui-state-tracking`: The shared live tracker must recover stuck active turns to `ready` after 5 seconds of stable submit-ready posture without manufacturing a success result.

## Impact

- Affected code: `src/houmao/shared_tui_tracking/apps/codex_tui/*`, `src/houmao/shared_tui_tracking/session.py`, `src/houmao/server/tui/tracking.py`, and related tracking configuration or reducer plumbing.
- Affected behavior: gateway prompt-readiness for tmux-backed Codex sessions, especially mail-notifier wakeups gated on tracked prompt-ready posture.
- Dependencies: reuse the existing `reactivex`-based tracking pipeline and scheduler infrastructure; do not introduce a separate manual timeout mechanism for stale-active recovery.
