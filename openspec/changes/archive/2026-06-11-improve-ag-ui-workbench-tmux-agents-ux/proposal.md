## Why

The AG-UI workbench tmux tab currently wastes vertical space and can leave stale tmux sessions visible after the underlying session exits or is killed outside the browser. The Agents workflow also requires a manual refresh before useful data appears, while the separate `Agents` and `Agent Pane` toolbar controls split one workflow across two top-level buttons.

## What Changes

- Make tmux tabs fill the available Dockview panel height and refit the xterm terminal when the browser or Dockview panel size changes.
- Keep the tmux session list fresh while tmux tabs are open, refresh immediately after attach exit or disconnect, and remove sessions that no longer exist without sending tmux or Houmao lifecycle control commands.
- Refresh discovered agents automatically whenever the Agents picker opens, while preserving manual refresh and visible error handling.
- Merge blank agent-pane creation into the Agents picker by removing the separate top-level `Agent Pane` toolbar control and adding a `New` action inside the picker.
- Update deterministic workbench coverage for tmux resize, dead-session removal, Agents auto-refresh, and the in-picker New action.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `ag-ui-workbench-app`: Tmux tabs gain full-height responsive layout and dead-session removal; the global toolbar no longer exposes a separate `Agent Pane` control.
- `ag-ui-workbench-agent-picker`: The picker refreshes discovery on open and owns blank agent pane creation through an in-picker New action.
- `ag-ui-workbench-runtime-lifecycles`: Runtime tmux effects maintain shared session inventory freshness, react to attach exit/disconnect, and keep polling/teardown ownership outside React components.

## Impact

- `apps/ag-ui-workbench/src/App.tsx`, pane components, picker components, runtime state/selectors/effects, tmux client services, styles, and Playwright/runtime tests.
- No Python package distribution impact.
- No new external dependencies are expected.
