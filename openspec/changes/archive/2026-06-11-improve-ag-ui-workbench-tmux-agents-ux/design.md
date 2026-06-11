## Context

`apps/ag-ui-workbench` already has runtime-owned tmux effects, a Dockview-based layout, an xterm-based tmux panel, and an Agents picker backed by passive-server discovery. Today each tmux pane requests refresh on mount, keeps terminal DOM and fit objects locally, and delegates attach WebSocket lifecycle to the runtime. The browser bridge lists real tmux sessions through the Vite plugin and exposes a WebSocket attach path that reports output, resize, errors, and exit.

The current gaps are UX and lifecycle freshness rather than a new integration boundary. The tmux panel layout can leave unused vertical space and depends on the current component sizing behavior. A tmux session that exits from inside the attached terminal or is killed outside the browser can remain in the list until the user refreshes. The Agents picker can open with stale or empty content because the user must manually refresh, and the toolbar duplicates the same workflow through `Agents` and `Agent Pane`.

## Goals / Non-Goals

**Goals:**

- Make tmux terminal panes fill available Dockview height and refit when the browser or panel size changes.
- Keep tmux session inventory fresh while tmux panes are open, including immediate refresh after attach exit or socket close.
- Remove dead tmux sessions from visible lists without sending tmux kill commands or Houmao lifecycle commands.
- Refresh Agents discovery automatically on picker open.
- Move blank manual agent-pane creation into the Agents picker and remove the separate top-level `Agent Pane` toolbar control.
- Cover the behavior with deterministic runtime and browser tests.

**Non-Goals:**

- Replace the tmux bridge implementation with a new tmux server.
- Persist terminal scrollback or raw terminal data.
- Change Houmao managed-agent lifecycle semantics.
- Add new package dependencies unless implementation discovers a strong need.
- Preserve the removed top-level `Agent Pane` button as a compatibility alias.

## Decisions

### Keep terminal rendering local and make layout deterministic

The tmux React pane will continue to own `Terminal`, `FitAddon`, DOM refs, and browser layout measurement. CSS will make the tmux panel a strict height-contained layout: fixed header and picker controls, a remaining-space body, an independently scrollable session list, and a terminal host with `min-height: 0`, `height: 100%`, and no footer that steals terminal space. The current bottom Remove action should move into the fixed header/action area or become an icon action so the terminal host remains the only flexible vertical region.

The component will call `fit()` from a `ResizeObserver` attached to the terminal host and from lifecycle points where xterm becomes visible or the selected session changes. After each successful fit, the pane dispatches the runtime resize action with the current xterm columns and rows when an attachment is active. A small requestAnimationFrame or micro-debounce is acceptable to avoid repeated resize messages during Dockview drag.

Alternative considered: store terminal size in runtime state and drive fitting from the runtime. This would mix DOM-only state with runtime reducers and conflict with the existing requirement that terminal objects and DOM refs remain outside reduced runtime state.

### Promote tmux inventory to shared runtime state

The runtime should expose one shared tmux inventory view containing bridge status, sessions, matched discovered agents, loading/error state, and last refresh time. Per-pane tmux state should keep pane-specific concerns such as selected session, read-only mode, attach status, and active attachment id. Selectors can project the shared inventory into each pane view so existing panes keep rendering status, sessions, agents, loading, and errors through runtime-derived data.

Runtime effects will maintain an inventory interest count or equivalent set of tmux pane ids. When the first tmux pane opens, effects refresh immediately and start a poller. When the last tmux pane closes, effects stop the poller. The default polling cadence should be modest, around five seconds, because the UI only needs to remove stale sessions promptly enough for operator feedback. Manual refresh, pane open, browser focus, attach exit, socket close, and socket error all trigger immediate refresh.

Overlapping refreshes should be coalesced or made last-writer-wins. The implementation can use an in-flight request token, abort controller support where available, or an RxJS switch/exhaust pattern consistent with the existing runtime effects. The selected approach must prevent stale responses from reintroducing deleted sessions after a newer refresh.

Alternative considered: keep refresh state per tmux pane. That duplicates timers and requests, makes externally killed sessions disappear at different times in different panes, and works against the runtime lifecycle contract that long-lived tmux refreshes are runtime owned.

### Treat attach exit as a browser attachment event, not a lifecycle command

The tmux attach WebSocket already reports `exit` and closes when the spawned attach process ends. Runtime effects should interpret that as the browser client attachment ending. They should close and remove the WebSocket handle, mark the pane attachment disconnected or errored as appropriate, unregister or ignore obsolete sink writes, and trigger inventory refresh. They must not send any tmux kill-session command or Houmao lifecycle command.

If the exiting attachment ended because the session itself died, the next inventory refresh removes the session. If the attach process ended while the tmux session still exists, the refreshed list keeps it visible and the user can attach again.

### Auto-refresh Agents picker on open

The picker should trigger discovery refresh whenever its open request changes from closed to open. The refresh should reuse the existing passive-server discovery client path and state shape so manual refresh, loading indicators, and error messages stay consistent. The component should guard against stale responses by tracking a request id, aborting when supported, or ignoring responses after the request is no longer current.

The picker should not refresh when no passive-server base URL is configured beyond the current deterministic empty or error behavior. Existing row actions, filtering, watch/unwatch, and retarget behavior remain unchanged.

### Make Agents the single agent creation entry point

The top toolbar should keep `Agents` as the discovery and agent-pane entry point and remove the separate `Agent Pane` button. Inside the picker, a `New` action creates a blank manual agent pane by calling the same application helper currently used by the toolbar button. When the picker is opened from a pane for retargeting, `New` creates a separate blank pane and leaves the requesting pane unchanged. Selecting or double-clicking a discovered row continues to perform the picker’s current action: create a discovered pane from toolbar mode or retarget the requesting pane from pane mode.

This keeps the top-level navigation smaller while preserving the manual target flow.

### Test through runtime fakes and browser fixtures

Runtime tests should cover inventory interest lifecycle, one shared poller for multiple panes, attach-exit-triggered refresh, external-session-removal projection, and teardown cleanup. Browser tests should cover the visible behaviors that users asked for: terminal resize after viewport or panel changes, dead fixture session removal, picker auto-refresh on open, absence of the top-level `Agent Pane` control, and blank manual pane creation from the picker New action.

The deterministic tmux fixture may need a fixture-only mutation hook or in-memory bridge state so tests can remove a listed session and observe the UI update without depending on host tmux. Fixture-only behavior must remain behind the existing workbench test/dev bridge boundary.

## Risks / Trade-offs

- Polling can add unnecessary bridge requests if left running after panes close. Mitigation: use explicit tmux pane interest tracking and assert poller teardown in runtime tests.
- Browser resize can emit many terminal resize messages during Dockview drag. Mitigation: debounce with requestAnimationFrame or a short timer and only dispatch when columns or rows change.
- A stale discovery or tmux inventory response can reintroduce old data. Mitigation: use request sequence tokens or cancelation and accept only the latest response.
- Moving blank pane creation into the picker can make the manual flow less visible. Mitigation: place the New action in the picker header near refresh and keep the label concise.

## Migration Plan

This is a development workbench change with no persisted data migration. Existing saved workbench layouts can continue to restore agent, Debug Agent, and tmux panes. The removed toolbar button changes only the visible command surface; the blank manual agent-pane creation helper remains available through the picker.

Rollback is limited to reverting the workbench code and tests for this change.

## Open Questions

None at proposal time.
