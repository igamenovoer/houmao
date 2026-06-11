## 1. Pane Presentation State

- [x] 1.1 Add `TemplateGraphicBackendOverride` and pane presentation config types with `auto`, `vega-lite`, and `recharts` values.
- [x] 1.2 Add default and sanitize helpers in workbench storage so missing or invalid presentation config loads as `auto`.
- [x] 1.3 Persist pane presentation config in `PaneRecord` without changing persisted stream-content boundaries.
- [x] 1.4 Expose `updatePanePresentation` through `WorkbenchContext` and wire it from `App` storage updates.

## 2. Template Renderer Override UI and Rendering

- [x] 2.1 Add a compact template renderer dropdown to normal agent panes with stable test ids and per-pane state updates.
- [x] 2.2 Pass the pane renderer preference from `AgentSessionPanel` to `AgUiDisplaySurface`.
- [x] 2.3 Extend `ToolCallRenderer` and nested component rendering context to carry the template renderer override.
- [x] 2.4 Update `renderTemplateGraphic` renderer selection so `auto` preserves payload preference and forced renderers evaluate only the selected backend.
- [x] 2.5 Add deterministic fallback wording for unsupported forced renderer attempts while preserving raw payload diagnostics.

## 3. Agent Picker Auto-Connect

- [x] 3.1 Add an App-level helper that registers a target as watched, dispatches immediate `pane/targetChanged`, and requests active-thread set when the selected target is eligible.
- [x] 3.2 Change agent-pane creation to return the created pane id and accept an auto-connect option for discovered-agent picker selections.
- [x] 3.3 Change pane retargeting to accept an auto-connect option after clearing obsolete pane state.
- [x] 3.4 Update `AgentPicker` callback types and discovered-agent selection handlers to request auto-connect for new-pane and retarget actions.
- [x] 3.5 Keep the picker New blank-pane action manual and verify it does not register a watched target or active-thread mutation.

## 4. Tmux Terminal Repaint

- [x] 4.1 Add a local xterm visible-row refresh scheduler to `TmuxTabPanel` and clean it up on detach or pane close.
- [x] 4.2 Register xterm `onScroll` and `onWriteParsed` handlers that schedule terminal refresh without storing terminal bytes.
- [x] 4.3 Refresh visible rows after every successful fit, including same-size fits that do not dispatch runtime resize.
- [x] 4.4 Add Dockview dimension and visibility hooks that schedule terminal fit alongside the existing `ResizeObserver`.
- [x] 4.5 Evaluate deterministic stale-scroll reproduction; host-level wheel interception was not needed after refresh scheduling passed fixture coverage.

## 5. Browser Coverage

- [x] 5.1 Add or update deterministic AG-UI fixture coverage for `auto`, forced `vega-lite`, forced `recharts`, and forced-renderer diagnostic behavior.
- [x] 5.2 Add storage coverage proving renderer preference persists and invalid stored values sanitize to `auto`.
- [x] 5.3 Add picker coverage proving discovered-agent new-pane and retarget actions auto-connect without clicking Connect.
- [x] 5.4 Add picker coverage proving blank manual pane creation remains non-connecting.
- [x] 5.5 Add tmux fixture coverage that attaches a tmux tab, creates scrollback, mouse-scrolls the xterm viewport, and verifies repaint without resizing the browser window.

## 6. Verification

- [x] 6.1 Run `bun run typecheck` in `apps/ag-ui-workbench`.
- [x] 6.2 Run targeted workbench Playwright coverage with `bun run e2e` or the narrowed equivalent.
- [x] 6.3 No shared AG-UI authoring or gateway Python code was touched; Python/unit checks were not applicable.
- [x] 6.4 Run `pixi run openspec status --change improve-ag-ui-workbench-pane-behavior` and confirm the change is apply-ready.
