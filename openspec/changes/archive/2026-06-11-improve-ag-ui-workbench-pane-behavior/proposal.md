## Why

Manual AG-UI workbench testing currently has three avoidable friction points: tmux terminal panes can leave stale edge pixels after mouse scrolling, template graphics cannot be forced through a specific renderer from the GUI, and selecting a discovered agent still requires a separate Connect click before the pane is useful. These are presentation and workflow problems in the workbench, and they now block reliable manual validation of real-agent AG-UI graphics flows.

## What Changes

- Make docked tmux tabs repaint the full visible xterm area after local scroll, output parse, and layout/refit events so stale terminal edges do not require resizing the browser window to recover.
- Add a pane-level template graphic backend dropdown to agent panes with `auto`, `vega-lite`, and `recharts` options.
- In `auto`, keep the current message-driven `renderer.preferred` and `renderer.fallback` behavior.
- In forced `vega-lite` or `recharts` mode, render `houmao.graphic.template` tool calls with the selected backend when supported and show deterministic diagnostics when that backend cannot render the payload.
- Persist the pane presentation preference as safe local UI metadata, without persisting AG-UI stream content or mutating received tool-call payloads.
- Auto-connect discovered-agent panes opened from the agent picker, including new-pane and retarget flows, by reusing the same watched-target and active-thread behavior as the existing Connect action.
- Keep blank manual panes manual: creating a blank pane from the picker does not auto-connect.
- Add deterministic browser coverage for tmux scroll repaint, template renderer override selection, and picker auto-connect.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `ag-ui-workbench-app`: Adds pane-level template renderer override UI and persistence, strengthens tmux tab repaint/refit behavior, and expands browser coverage for these workbench presentation behaviors.
- `ag-ui-workbench-agent-picker`: Changes discovered-agent selection so new-pane and retarget actions auto-connect the resulting pane to the selected target while preserving manual blank-pane behavior.
- `ag-ui-copilotkit-graphics`: Clarifies workbench renderer selection semantics for `houmao.graphic.template` when a GUI-side override is present.

## Impact

- Affected frontend code: `apps/ag-ui-workbench/src/panes/AgentSessionPanel.tsx`, `apps/ag-ui-workbench/src/panes/AgentPicker.tsx`, `apps/ag-ui-workbench/src/panes/TmuxTabPanel.tsx`, `apps/ag-ui-workbench/src/panes/AgUiDisplaySurface.tsx`, `apps/ag-ui-workbench/src/ag-ui/componentRenderers.tsx`, `apps/ag-ui-workbench/src/ag-ui/templateGraphics.tsx`, `apps/ag-ui-workbench/src/App.tsx`, `apps/ag-ui-workbench/src/storage.ts`, and related CSS/tests.
- Affected runtime code: likely limited to existing workbench runtime actions/effects for active-thread and watched-target connection reuse; no AG-UI gateway protocol change is expected.
- Affected specs: workbench app behavior, agent picker behavior, and template graphic renderer selection behavior.
- Dependencies: no new runtime package dependency is expected; the workbench already has Recharts and Vega-Lite rendering dependencies.
- Persistence boundary: only safe pane presentation metadata is added to localStorage; streamed AG-UI events, terminal bytes, prompt text, credentials, and request bodies remain outside localStorage.
