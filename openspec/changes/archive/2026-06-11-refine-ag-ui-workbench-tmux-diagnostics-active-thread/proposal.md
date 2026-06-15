## Why

The AG-UI workbench currently spends pane width on a persistent tmux session list, keeps diagnostics visible for every agent pane, and shows confusing active-thread status when a live gateway does not expose the active-thread extension. These issues make the main terminal and transcript surfaces harder to use and can present unsupported active-thread polling as an application error.

## What Changes

- Replace the tmux pane's permanent left session list with a top combobox that supports typing to search and opens a dropdown only when the user needs to choose a session.
- Refresh tmux session inventory when the combobox opens, when the user manually refreshes, and after tmux attachment exit/error, rather than continuously polling solely because a tmux pane exists.
- Let the tmux terminal use the pane's full available width after fixed controls are laid out.
- Hide the always-visible diagnostics panel from normal agent panes.
- Add an info control to each transcript message in normal agent panes; clicking it opens a side inspector with diagnostics scoped to that message and related events/tool calls.
- Preserve Debug Agent diagnostic/raw-evidence behavior unless explicitly changed by a later Debug Agent-focused change.
- Treat gateways that do not support `/active-thread` as unsupported instead of inactive/error, stop polling unsupported gateways, and avoid abort-driven polling flicker.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `ag-ui-workbench-app`: Update tmux session picking, normal agent diagnostics presentation, and active-thread unsupported-state UI requirements.
- `ag-ui-workbench-runtime-lifecycles`: Update tmux inventory refresh triggers and active-thread poll lifecycle behavior.
- `ag-ui-workbench-rxjs-runtime`: Clarify active-thread polling concurrency and unsupported-extension handling in the RxJS runtime.

## Impact

- Affected UI code: `apps/ag-ui-workbench/src/panes/TmuxTabPanel.tsx`, `apps/ag-ui-workbench/src/panes/AgUiDisplaySurface.tsx`, `apps/ag-ui-workbench/src/panes/AgentSessionPanel.tsx`, and `apps/ag-ui-workbench/src/styles.css`.
- Affected runtime code: `apps/ag-ui-workbench/src/runtime/actions.ts`, `apps/ag-ui-workbench/src/runtime/state.ts`, `apps/ag-ui-workbench/src/runtime/selectors.ts`, `apps/ag-ui-workbench/src/runtime/effects/tmuxEffects.ts`, and `apps/ag-ui-workbench/src/runtime/effects/activeThreadEffects.ts`.
- Affected tests: workbench Playwright tests and runtime reducer/effects tests for tmux selection, message diagnostics, and active-thread unsupported/flicker behavior.
- No external API or storage migration is expected.
