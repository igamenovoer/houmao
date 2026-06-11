## Why

The AG-UI workbench is accumulating long-lived asynchronous workflows: AG-UI streams, watched-target reconnects, tmux WebSockets, active-thread state, gateway polling, event cache updates, and cross-pane coordination. React component-local `useEffect` and refs are becoming the wrong place to own that behavior.

The current gateway fallback also uses `last-bound-thread` as an implicit default destination. That makes the default graphing target depend on incidental GUI activity. The default destination should instead be an explicit `active-thread` chosen by the user or by a foreground pane connect action.

## What Changes

- Add RxJS to the AG-UI workbench and make it the primary browser runtime event facility for long-lived workflows.
- Introduce a workbench runtime layer with actions, effects, shared observable state, selectors, and React adapter hooks.
- Move active-thread polling and mutation into the RxJS runtime, with one shared poller per gateway and a 1 second default poll interval.
- **BREAKING** Replace gateway `last-bound-thread` terminology and routes with `active-thread`.
- Change gateway publish fallback priority to explicit request or event destination, then `active-thread`, then default sink.
- Keep `last-sent-thread` as gateway-owned bookkeeping only; it is updated after concrete non-sink sends but is no longer used for destination fallback.
- Add an explicit active-thread control on each eligible Houmao agent pane, shown gray when inactive and green when it matches the gateway active thread.
- Automatically mark an eligible Houmao agent pane active when the user connects that pane to the gateway.
- Preserve inactive pane behavior: inactive panes can still receive and render AG-UI events addressed to their exact thread; they are only excluded from omitted-route default selection.
- Update `houmao-mgr` AG-UI publish reporting and agent skill guidance so agents understand active-thread fallback, default-sink warnings, and zero-delivery results.
- Migrate watched-target, AG-UI stream, tmux attach, and persistence side effects toward the RxJS runtime without persisting raw terminal or AG-UI stream bytes beyond existing cache boundaries.

## Capabilities

### New Capabilities

- `ag-ui-workbench-rxjs-runtime`: Defines the AG-UI workbench browser runtime event layer, RxJS action/effect/state patterns, shared polling, cancellation, and React integration boundaries.

### Modified Capabilities

- `ag-ui-workbench-app`: Replaces implicit last-bound thread behavior with explicit active-thread pane controls and connect-time activation while preserving inactive pane rendering.
- `agent-gateway`: Replaces last-bound-thread state/routes with active-thread state/routes and changes omitted-route publish fallback to explicit destination, active-thread, then default sink.
- `houmao-ag-ui-message-authoring`: Updates Houmao gateway publish semantics so omitted routing relies on active-thread fallback and no longer uses last-sent-thread for routing.
- `houmao-agent-ag-ui-skill`: Updates agent guidance for tmux/TUI-controlled AG-UI publishing, active-thread fallback, last-sent bookkeeping, and default-sink/no-delivery reporting.

## Impact

- `apps/ag-ui-workbench`: Adds `rxjs`, introduces a runtime event layer, updates pane active-thread controls, moves cross-pane workflows out of component-local effects, and revises Playwright coverage.
- `src/houmao/ag_ui`: Renames destination state concepts, adds active-thread routes, changes publish fallback ordering, and keeps last-sent as diagnostics/bookkeeping only.
- `src/houmao/srv_ctrl/commands/agents/gateway.py`: Keeps route-optional publish support while updating output expectations and wording around active-thread/default-sink results.
- `src/houmao/agents/assets/system_skills/houmao-agent-ag-ui/SKILL.md`: Updates instructions for agents publishing graphics from tmux/TUI contexts.
- Tests: Add workbench RxJS runtime tests, Playwright active-thread polling and inactive-pane rendering coverage, gateway routing tests, CLI output tests, and skill text checks where appropriate.
