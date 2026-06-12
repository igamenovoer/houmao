## Why

The AG-UI workbench tmux pane still shows stale-looking edge regions during long autonomous Claude TUI output, even without mouse scrolling. Investigation points to the browser xterm instance parsing a real tmux PTY stream with `convertEol: true`, which xterm documents as inappropriate for PTY-backed streams and which can corrupt full-screen TUI cursor and clear semantics.

## What Changes

- Treat tmux attachment output as raw PTY terminal bytes in the browser xterm surface.
- Remove browser-side newline conversion from tmux panes so `\n`, `\r`, cursor movement, alternate-screen redraws, and line clears are interpreted exactly as emitted by tmux.
- Keep the existing server bridge behavior of forwarding tmux PTY chunks without transformation.
- Add deterministic coverage for PTY-style terminal control output that reproduces newline-sensitive edge-cell behavior.
- Add or update manual smoke guidance for real tmux Claude/Kimi TUI output so this class of rendering issue can be validated without relying on mouse scroll.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `ag-ui-workbench-app`: Tmux terminal panes must parse tmux attachment output as a PTY stream without browser-side newline conversion and must render long alternate-screen TUI output without stale edge cells caused by newline rewriting.

## Impact

- Affected app code: `apps/ag-ui-workbench/src/panes/TmuxTabPanel.tsx`.
- Affected tests: focused workbench tmux E2E coverage, runtime/browser terminal fixture coverage, and optional real tmux smoke evidence.
- No public protocol change is required.
- No persistent storage migration is required.
