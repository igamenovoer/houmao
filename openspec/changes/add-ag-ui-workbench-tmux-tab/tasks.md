## 1. Dependencies and Host Bridge

- [x] 1.1 Add workbench dependencies for Fuse.js, xterm, xterm fit addon, WebSocket server support, and node-pty.
- [x] 1.2 Add a Vite tmux bridge plugin with `GET /__houmao_tmux/status`, `GET /__houmao_tmux/sessions`, and `WS /__houmao_tmux/attach`.
- [x] 1.3 Implement tmux session listing with tmux availability detection and deterministic unavailable/error responses.
- [x] 1.4 Implement WebSocket attach startup for read-write and read-only tmux attachment modes.
- [x] 1.5 Enforce read-only input rejection in the host tmux bridge and clean up only the spawned browser-client attach process on close.

## 2. Workbench Data Model

- [x] 2.1 Remove new-use `operator` pane creation from the workbench pane model and storage sanitizer.
- [x] 2.2 Extend workbench pane storage with a `tmux` pane kind and sanitized tmux tab configuration.
- [x] 2.3 Add default tmux tab config with read-write mode and Houmao-only filtering enabled.
- [x] 2.4 Add a single optional operator-pane marker that can reference only an ordinary discovered Houmao agent pane.
- [x] 2.5 Clear invalid operator-pane markers when the marked pane closes, disappears, or is retargeted away from a discovered Houmao agent.
- [x] 2.6 Ensure storage persistence excludes terminal bytes and continues to sanitize Dockview floating/popout state.
- [x] 2.7 Expose tmux pane creation, tmux update, and operator-designation callbacks through the workbench context where needed.

## 3. Tmux Client and Picker UI

- [x] 3.1 Add browser tmux client helpers for bridge status, session listing, WebSocket attach, resize, input, and close.
- [x] 3.2 Add a `TmuxTabPanel` component with unattached, attaching, attached, error, and disconnected states.
- [x] 3.3 Add a tmux session picker that joins raw tmux sessions with passive-server discovered agents by `tmux_session_name`.
- [x] 3.4 Implement Fuse.js fuzzy search over session name and matched Houmao agent metadata.
- [x] 3.5 Add the Houmao-only checkbox filter and deterministic empty/error states for discovery outages.
- [x] 3.6 Render the attached terminal with xterm and fit addon, including resize propagation.
- [x] 3.7 Enforce read-only mode in the browser terminal by suppressing stdin and showing a clear read-only state.

## 4. Workbench Integration

- [x] 4.1 Register the tmux panel component with Dockview and add a toolbar control for opening a tmux tab.
- [x] 4.2 Remove automatic Operator tab creation on fresh load, empty workspace, and reload from legacy layouts.
- [x] 4.3 Add an operator-designation control on eligible Houmao agent panes and visible marker state for the selected pane.
- [x] 4.4 Ensure operator-marked agent panes use the same AG-UI request bodies and watcher behavior as ordinary agent panes.
- [x] 4.5 Ensure tmux panes move within the existing docked workspace without enabling floating or popout groups.
- [x] 4.6 Ensure closing or disconnecting a tmux tab does not send AG-UI detach or Houmao lifecycle-control requests.
- [x] 4.7 Preserve existing agent, Debug Agent, watched-target, and clear-canvas behavior.
- [x] 4.8 Update foreground agent-pane activation and viewed-thread changes to set the target gateway's last-bound-thread state.
- [x] 4.9 Ensure background watchers, hidden panes, event-cache listeners, and passive reconnects do not update last-bound-thread.
- [x] 4.10 Clear last-bound-thread on a best-effort basis when the active bound pane closes or retargets without an active replacement.
- [x] 4.11 Ensure workbench binding calls do not set or clear gateway-owned last-sent-thread state.

## 5. Gateway Binding and AG-UI Publish

- [x] 5.1 Add gateway-local last-bound-thread and last-sent-thread state with deterministic empty/bound/sent response models.
- [x] 5.2 Add Houmao extension routes to read destination fallback state and to set and clear last-bound-thread, including blank-thread validation.
- [x] 5.3 Refresh last-sent-thread when gateway publishing resolves to a concrete non-sink thread destination.
- [x] 5.4 Update gateway AG-UI publish routing to use message-specified destination, last-sent-thread, last-bound-thread, then default sink.
- [x] 5.5 Implement the default sink as a Houmao-defined no-GUI-fan-out destination that logs safe routing metadata and returns a warning due to no destination.
- [x] 5.6 Ensure default-sink publishing does not expose a sink thread name to agents and does not refresh last-sent-thread.
- [x] 5.7 Preserve live-only publish semantics when last-sent-thread or last-bound-thread fallback is used, including zero delivery when no GUI stream is listening.
- [x] 5.8 Update `houmao-mgr` AG-UI publish command handling so route flags are optional for Houmao gateways and explicit routes still override fallback.
- [x] 5.9 Update publish helper output to report default-sink warnings and avoid claiming GUI visibility for default-sink or zero-delivery results.
- [x] 5.10 Update `houmao-agent-ag-ui` skill guidance for tmux-controlled agents, gateway destination fallback, default-sink warnings, and zero-delivery results.

## 6. Documentation

- [x] 6.1 Update the workbench README with the removal of the dedicated Operator tab and the two operator workflows: tmux direct control or agent-pane operator designation.
- [x] 6.2 Update the workbench README with tmux tab usage, prerequisites, read-only mode, and the tmux lifecycle boundary.
- [x] 6.3 Document that tmux terminal output/input is in-memory only and is not stored in localStorage or IndexedDB.
- [x] 6.4 Document destination fallback behavior for tmux-controlled agents, including that last-bound-thread is GUI-maintained, last-sent-thread is gateway-maintained, both are volatile, and the default sink is not agent-addressable.

## 7. Tests and Verification

- [x] 7.1 Add deterministic tmux bridge fixtures or test hooks for session listing and attachment behavior.
- [x] 7.2 Add Playwright coverage proving a fresh workbench and empty workspace do not create a dedicated Operator tab.
- [x] 7.3 Add Playwright coverage proving one discovered Houmao agent pane can be marked as operator and that the marker clears when the pane becomes ineligible.
- [x] 7.4 Add Playwright coverage proving operator-marked panes send the same minimal AG-UI request bodies as ordinary agent panes.
- [x] 7.5 Add Playwright coverage for opening a tmux tab, listing sessions, Fuse search, and Houmao-only filtering.
- [x] 7.6 Add Playwright coverage for read-write input forwarding and read-only input suppression or rejection.
- [x] 7.7 Add Playwright coverage proving tmux tab close keeps the fixture session alive and does not emit lifecycle-control requests.
- [x] 7.8 Add persistence coverage proving terminal output/input is absent from localStorage and the AG-UI event cache.
- [x] 7.9 Add gateway unit tests for destination fallback state reads, last-bound-thread set/clear, blank-thread validation, and last-sent-thread ownership.
- [x] 7.10 Add gateway publish tests for message-specified precedence, last-sent fallback, bound-thread fallback, last-sent refresh, default-sink fallback, and live-only zero delivery.
- [x] 7.11 Add CLI tests for route-optional Houmao gateway publishing, explicit-route precedence, default-sink warning output, and zero-delivery output.
- [x] 7.12 Add Playwright coverage proving foreground agent panes bind last-bound-thread and background watchers do not steal it.
- [x] 7.13 Run `bun run typecheck` and the workbench Playwright suite from `apps/ag-ui-workbench`.
- [x] 7.14 Run relevant gateway and CLI Python tests with `pixi run`.
- [x] 7.15 Run `openspec validate add-ag-ui-workbench-tmux-tab --strict --no-interactive`.
