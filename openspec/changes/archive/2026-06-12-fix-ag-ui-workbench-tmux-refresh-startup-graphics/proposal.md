## Why

Manual validation found two reliability gaps before the cross-runtime tmux backend work can be implemented safely. A real tmux attachment can leave stale edge regions in the browser terminal until the outer window is resized, and a true new-agent startup graphics test is blocked by a retired `houmao-agent-ag-ui` system-skill reference even though existing-agent first-connect graphics now render.

## What Changes

- Strengthen tmux pane resize and repaint behavior so real tmux attachments repaint the full visible xterm area without requiring browser resize.
- Ensure first-connect AG-UI graphics validation covers a newly launched Houmao agent, not only an existing or relaunched agent.
- Fix workbench real-agent smoke assertions so Plotly's multiple SVG layers count as one visible chart instead of failing strict locator checks.
- Prevent stale retired managed system-skill references in unrelated project presets or profiles from blocking a launch that does not select those records.
- Keep the bug-fix work independent of the pending cross-runtime tmux PTY backend change.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `ag-ui-workbench-app`: Require real tmux repaint validation and first-connect graphics validation that covers fresh agent launch.
- `ag-ui-workbench-local-server`: Clarify tmux attachment resize delivery and browser-visible paint behavior expected from the server-backed tmux bridge.
- `agent-launch-profiles`: Require removed system-skill references to be reported against the selected launch source instead of globally blocking unrelated launches.
- `houmao-mgr-agents-launch`: Require project agent launch to validate only the selected launch source and its dependencies before birth.

## Impact

- Affected frontend code: `apps/ag-ui-workbench/src/panes/TmuxTabPanel.tsx`, workbench runtime tmux effects, and Playwright workbench tests.
- Affected local server code: `apps/ag-ui-workbench/src/server/**` tmux bridge routes and WebSocket resize handling.
- Affected launch code: project agent launch profile/preset resolution and managed system-skill validation.
- Affected fixtures: the project-local test preset that still references retired `houmao-agent-ag-ui`.
- No AG-UI protocol change, no browser persistence of terminal bytes, and no managed-agent lifecycle control from tmux pane attach/detach.
