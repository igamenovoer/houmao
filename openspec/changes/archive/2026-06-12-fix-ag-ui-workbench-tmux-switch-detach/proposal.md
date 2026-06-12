## Why

The AG-UI workbench tmux pane can switch its visible terminal from one tmux session to another while mouse-wheel scroll remains unreliable or appears bound to the first attached session. The switch path needs to replace the tmux attachment identity, not only replace the xterm surface, because scroll is intentionally handled by the server-side tmux command path for reliable browser repaint behavior.

## What Changes

- Treat tmux session selection in a workbench tmux pane as an explicit detach-and-reattach operation.
- Ensure selecting a different tmux session closes the previous browser WebSocket attachment, releases the previous server-side tmux attach client, and opens a fresh attachment for the selected session.
- Keep input, resize, and server-handled scroll routed only to the current attachment after a switch.
- Ignore stale output, exit, close, or error events from an older attachment generation after a newer session has been selected.
- Use the local Tailmux reference under `extern/tracked/tailmux/` as the primary behavioral reference for explicit tmux client detach on WebSocket close.
- Preserve the existing server-side scroll implementation; do not fall back to PTY passthrough scrolling.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `ag-ui-workbench-app`: A tmux pane must replace its active attachment when the user selects a different session, and all pane commands must target the newly selected attachment.
- `ag-ui-workbench-local-server`: The tmux bridge must release the previous tmux attach client on attachment close and keep scroll commands scoped to the WebSocket attachment that owns the current session.

## Impact

- Affected frontend code: `apps/ag-ui-workbench/src/panes/TmuxTabPanel.tsx`, runtime tmux effects, and workbench Playwright tests.
- Affected local server code: `apps/ag-ui-workbench/src/server/tmuxBridge.ts` and tmux bridge tests.
- Affected reference material: `extern/tracked/tailmux/server.js` and `extern/tracked/tailmux/public/app.js` for attach cleanup and session-owned routing patterns.
- No AG-UI protocol change, no durable tmux byte persistence, no managed-agent lifecycle control, and no change to the decision that mouse scroll is handled by server tmux commands rather than raw PTY passthrough.
