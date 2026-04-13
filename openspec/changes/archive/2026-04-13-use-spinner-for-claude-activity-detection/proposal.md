## Why

Claude Code TUI tracking can still report `surface.ready_posture=no` and `turn.phase=active` when the visible prompt is actually ready because the Claude profile treats fixed thinking/tool prose such as `Musing...` or `Reading...` as active evidence. This is too brittle for Claude's drift-prone status text: the spinner/status structure is the reliable active signal, not the incidental words attached to it.

## What Changes

- Remove Claude Code active-turn inference from fixed thinking and tool-activity phrase lists.
- Preserve active-turn inference from structural current-turn evidence, including spinner glyph rows, current interruptable footer state, current active block shape, and other non-prose UI structure.
- Keep latest-turn scoping so structural active evidence from older scrollback does not make a current submit-ready prompt look active.
- Add regression coverage for a Claude prompt-ready surface that includes stale or incidental thinking/tool prose but no current spinner signal, verifying it stays ready.
- Add coverage that a current spinner row still makes the Claude surface active.
- Do not change gateway notifier readiness policy, public tracked-state schema, or stale-active recovery timing.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `versioned-tui-signal-profiles`: tighten Claude Code activity interpretation so fixed thinking/tool prose is not active evidence by itself; current spinner and structural activity signals remain authoritative.

## Impact

- Affected code: `src/houmao/shared_tui_tracking/apps/claude_code/profile.py`.
- Affected tests: Claude shared TUI tracking tests under `tests/unit/shared_tui_tracking/`, with possible live-tracker regression coverage under `tests/unit/server/test_tui_parser_and_tracking.py`.
- Affected systems: attached gateway and direct server TUI tracking benefit because they consume the same shared Claude profile output.
- No public API, dependency, or storage format changes are intended.
