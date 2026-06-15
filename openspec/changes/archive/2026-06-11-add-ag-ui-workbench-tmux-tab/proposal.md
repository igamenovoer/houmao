## Why

The AG-UI workbench can inspect AG-UI streams, but it cannot directly observe or operate the tmux sessions that back Houmao TUI agents. The dedicated Operator tab is only a stub because operators can either control a session through tmux or designate an ordinary Houmao agent pane as the operator surface.

When a user controls an agent through a tmux tab, the agent does not receive the GUI-appended prompt context that an ordinary workbench prompt submission can include. The agent still needs a reliable way to discover the GUI thread that should receive authored AG-UI graphics.

## What Changes

- Add a new docked `tmux` pane kind to the AG-UI workbench.
- Provide a tmux session picker that lists local tmux sessions and supports quick fuzzy search by session and Houmao agent metadata.
- Allow the picker to filter the list to Houmao registry-backed agent sessions.
- Attach tmux panes in read-write mode by default, with an explicit read-only option.
- Remove the dedicated default `operator` tab as a first-class pane kind.
- Allow one connected Houmao agent pane to be flagged as the operator pane for user orientation, without granting special protocol behavior.
- Add gateway-local AG-UI destination state for the last foreground GUI-bound thread and the last concrete thread that received a gateway AG-UI publish.
- Have the workbench set that binding when an agent pane becomes the actively viewed GUI target or changes its viewed thread, while background watchers and reconnects do not steal the binding.
- Allow the Houmao gateway publish helper to omit explicit routing. The gateway resolves the destination as message-specified thread, then last-sent thread, then last-bound thread, then a Houmao-defined default sink.
- Return a warning when the gateway uses the default sink because no destination was available; the sink name is not agent-visible and the current sink behavior is gateway logging.
- Update the `houmao-agent-ag-ui` skill so agents know when they can omit routing and how to interpret default-sink warnings or zero delivery.
- Keep tmux attachment separate from AG-UI gateway semantics: closing a tmux tab closes only the browser attachment, not the tmux session or managed agent lifecycle.
- Persist only tmux tab configuration and selected session metadata, not terminal output.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `ag-ui-workbench-app`: Adds docked tmux tabs, tmux session discovery, Fuse-powered search, Houmao-agent filtering, read-write/read-only attachment, terminal persistence boundaries, removal of the dedicated Operator tab, and operator designation on ordinary Houmao agent panes.
- `agent-gateway`: Adds volatile last-bound and last-sent AG-UI thread state, binding routes, publish fallback behavior, and a default sink warning for omitted routing.
- `houmao-ag-ui-message-authoring`: Allows Houmao gateway publishing to omit explicit routing and rely on gateway destination fallback, while preserving third-party endpoint boundaries.
- `houmao-agent-ag-ui-skill`: Teaches agents how to publish from a tmux/TUI context with omitted routing and how to handle default-sink warnings.

## Impact

- `apps/ag-ui-workbench`: React pane model, storage schema, operator-pane removal, operator-designation UI, tmux picker UI, xterm rendering, and Vite development-server plugin surface.
- `src/houmao/ag_ui`: Gateway AG-UI destination state, routes, event publish fallback, and default-sink logging.
- `src/houmao/srv_ctrl/commands/agents/gateway.py`: AG-UI publish helper routing options, fallback reporting, and default-sink warning output.
- `src/houmao/agents/assets/system_skills/houmao-agent-ag-ui/SKILL.md`: Publishing guidance for tmux-controlled agents, gateway destination fallback, and default-sink warnings.
- Dependencies: add browser terminal/search and host tmux bridge packages such as Fuse.js, xterm, xterm fit addon, WebSocket server, and node-pty.
- Local runtime: requires `tmux` on the host running the workbench dev server; unavailable tmux should degrade to an empty/error session list rather than crashing the app.
- Tests: add deterministic browser tests for no-default-operator behavior, operator designation, last-bound-thread updates, session listing, filtering, read-only/read-write attachment behavior, close semantics, and persistence boundaries; add gateway/CLI tests for destination fallback, last-sent refresh, and default-sink warnings.
