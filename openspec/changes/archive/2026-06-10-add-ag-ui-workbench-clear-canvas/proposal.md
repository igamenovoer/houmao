## Why

Agent panes can accumulate rendered AG-UI graphics, transcript entries, diagnostics, and cached watched-target events during manual testing. Testers need a direct way to clear the visible canvas without disconnecting the agent, changing the target, or sending lifecycle commands to Houmao.

## What Changes

- Add a clear-canvas control on AG-UI workbench agent panes.
- Make clear-canvas reset the pane's visible AG-UI display state: transcript, graphics/tool calls, diagnostics, raw timeline, and visible errors.
- For watched agent targets, make clear-canvas also clear that target's browser-owned event cache and in-memory watched runtime state so old graphics do not reappear after reconnect or pane reopen.
- Preserve active connections, watcher reconnect loops, target configuration, prompt text, gateway state, and managed agent lifecycle when clearing the canvas.
- Use one user-facing concept, "Clear canvas", instead of exposing cache mechanics as the primary pane action.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `ag-ui-workbench-app`: agent panes expose a clear-canvas action that clears client-side AG-UI display evidence without controlling the agent.
- `ag-ui-workbench-client-event-cache`: watched-target canvas clearing removes cached stream events and resets in-memory reduced state immediately while keeping watcher ownership and connection semantics intact.

## Impact

- Affected code is primarily the AG-UI workbench agent pane header, display-state reset handling, watched-target cache clearing, and browser tests under `apps/ag-ui-workbench/`.
- No gateway API, AG-UI protocol, Houmao agent lifecycle, or Python package behavior needs to change.
- Browser coverage should verify that clearing removes rendered graphics from the pane and does not send detach, stop, restart, shutdown, or interrupt requests.
