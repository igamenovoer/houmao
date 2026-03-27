## Why

Several tmux-facing paths still rely on raw tmux command strings and session-name targets whose semantics depend on the current window. That caused a real foreground gateway failure, and the same pattern appears in other tracking and recorder-adjacent code. We now have `libtmux` available locally, so this is a good point to define a safer tmux integration boundary around session, window, and pane objects instead of continuing to hand-roll raw command usage everywhere.

## What Changes

- Introduce a repo-owned libtmux-first tmux integration layer for session, window, and pane discovery, lookup, capture, and control.
- Define that session-scoped pane enumeration must operate across all panes in the addressed session rather than only the current window.
- Define that tracked or controlled multi-window tmux flows must bind to explicit pane or window identity instead of falling back to current-window heuristics when the contract requires a specific surface.
- Keep fallback tmux operations available when libtmux does not expose a needed feature, but route those fallbacks through libtmux-owned command dispatch or object-bound commands rather than direct raw subprocess usage where practical.
- Update foreground gateway lifecycle behavior, live tracked-TUI observation, and recorder target resolution to follow the new tmux integration contract.

## Capabilities

### New Capabilities
- `tmux-integration-runtime`: Defines the libtmux-first tmux interface contract, including session-wide pane enumeration, id-based lookup, and bounded fallback rules for unsupported tmux operations.

### Modified Capabilities
- `agent-gateway`: Foreground same-session gateway lifecycle must resolve and monitor the auxiliary gateway pane correctly in multi-window tmux sessions.
- `official-tui-state-tracking`: Live tracked-TUI observation must resolve the intended tmux surface explicitly for multi-window sessions instead of depending on current active window behavior.
- `terminal-record-session-control`: Recorder target resolution must enumerate and validate panes across the addressed tmux session rather than implicitly limiting discovery to the current window.

## Impact

- Affected code: tmux runtime helpers, gateway lifecycle/runtime control, shared TUI tracking transport resolution, recorder target resolution, and tmux-facing explore/demo helpers.
- Affected dependency surface: `libtmux` becomes the preferred tmux integration library for repo-owned tmux interaction.
- Affected systems: runtime-owned local interactive sessions, foreground gateway attach/control, live tracked-TUI observation, and terminal recorder session targeting.
