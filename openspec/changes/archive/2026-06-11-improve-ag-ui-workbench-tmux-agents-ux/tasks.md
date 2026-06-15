## 1. Runtime Tmux Inventory

- [x] 1.1 Add shared tmux inventory state and selectors for bridge status, sessions, matched discovered agents, loading state, error state, and last refresh time.
- [x] 1.2 Add tmux pane inventory interest registration and cleanup so the runtime knows when at least one tmux pane needs inventory.
- [x] 1.3 Update tmux refresh effects to write shared inventory state and project it into existing tmux pane view models.
- [x] 1.4 Add one shared tmux inventory poller that starts on first tmux pane interest, refreshes immediately, refreshes on browser focus, and stops after the last tmux pane interest is removed.
- [x] 1.5 Prevent stale or overlapping tmux inventory responses from reintroducing obsolete sessions.
- [x] 1.6 Update tmux attach exit, close, and error handling to mark the pane attachment disconnected, clean up socket and sink resources, and request inventory refresh without issuing tmux or Houmao lifecycle commands.

## 2. Tmux Pane Layout and Resize

- [x] 2.1 Refactor `TmuxTabPanel` markup and styles so fixed controls stay fixed and the terminal host fills the remaining Dockview panel height.
- [x] 2.2 Move the tmux pane remove action out of the flexible terminal footer area so the terminal owns the remaining vertical space.
- [x] 2.3 Ensure the session list and tmux controls remain independently usable without forcing the attached terminal to shrink below its available region.
- [x] 2.4 Add terminal-host resize observation with requestAnimationFrame or short debounce fitting.
- [x] 2.5 Dispatch tmux resize updates only when fitted xterm columns or rows change and an attachment is active.

## 3. Agents Picker and Toolbar

- [x] 3.1 Trigger discovered-agent refresh whenever the Agents picker opens from the toolbar or from a pane target form.
- [x] 3.2 Guard picker auto-refresh against stale responses after close, passive-server URL change, or a newer refresh request.
- [x] 3.3 Add a picker New action that creates a blank manual docked agent pane without requiring a discovered-agent selection.
- [x] 3.4 Ensure picker New does not retarget the requesting pane when the picker was opened from an existing pane.
- [x] 3.5 Remove the top-level `Agent Pane` toolbar control and route blank manual agent-pane creation through the Agents picker.
- [x] 3.6 Preserve picker filtering, manual refresh, watch/unwatch, discovered-row open, and discovered-row retarget behavior.

## 4. Deterministic Fixtures and Tests

- [x] 4.1 Add or extend deterministic tmux bridge fixture support so tests can remove or exit a listed tmux session without relying on host tmux.
- [x] 4.2 Add runtime tests for shared tmux inventory state, one poller across multiple tmux panes, poller teardown, focus/manual refresh triggers, stale-response handling, and attach-exit refresh.
- [x] 4.3 Add browser coverage for tmux terminal fill and resize behavior after viewport or Dockview size changes.
- [x] 4.4 Add browser coverage for dead tmux session removal after fixture session exit or external removal.
- [x] 4.5 Add browser coverage for Agents picker auto-refresh on open, the in-picker New action, and absence of the top-level `Agent Pane` control.

## 5. Validation

- [x] 5.1 Run the workbench typecheck or equivalent frontend static check.
- [x] 5.2 Run the updated workbench runtime tests.
- [x] 5.3 Run the updated workbench Playwright E2E tests with the deterministic fixtures.
- [x] 5.4 Run `openspec validate improve-ag-ui-workbench-tmux-agents-ux --strict --no-interactive`.
