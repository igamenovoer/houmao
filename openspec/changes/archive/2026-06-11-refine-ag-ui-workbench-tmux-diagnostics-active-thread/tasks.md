## 1. Tmux Picker and Inventory

- [x] 1.1 Update tmux runtime effects so shared inventory refreshes on explicit requests, combobox open, and attach exit/error without maintaining a recurring poller solely because tmux panes are open
- [x] 1.2 Preserve stale-request protection for tmux inventory by aborting, coalescing, or ignoring obsolete refresh responses
- [x] 1.3 Replace the tmux pane's persistent left session list with a top searchable combobox/dropdown that uses the existing Fuse session matching and Houmao-only filter
- [x] 1.4 Attach to a selected tmux dropdown row using the current read-only/read-write mode and close the dropdown after selection
- [x] 1.5 Update tmux pane CSS so the terminal consumes available height and full pane width after fixed controls are laid out
- [x] 1.6 Update workbench tests for dropdown-open refresh, search/filter behavior, attach selection, full-width terminal layout, and dead-session removal on next picker open or manual refresh

## 2. Per-message Agent Diagnostics

- [x] 2.1 Refactor `AgUiDisplaySurface` to support normal on-demand diagnostics and Debug Agent global diagnostics modes
- [x] 2.2 Add an info icon control to each normal agent transcript message with stable test IDs and accessible button labels
- [x] 2.3 Implement a side diagnostics inspector scoped to the selected message, including related transcript, raw message events, tool calls, raw tool-call events, activity/custom records where deterministically linked, and current state snapshot evidence
- [x] 2.4 Wire normal `AgentSessionPanel` panes to on-demand message diagnostics while keeping `DebugAgentPanel` raw/global diagnostics behavior available
- [x] 2.5 Update CSS so transcript content, info controls, and the side inspector fit without overlapping on desktop and mobile-width panes
- [x] 2.6 Update Playwright tests that previously asserted `raw-*` or `state-*` in normal agent panes to open the message info inspector before checking diagnostics evidence

## 3. Active-thread Unsupported State

- [x] 3.1 Extend active-thread runtime state and actions to represent unsupported gateways separately from inactive, polling, ready, and transient error states
- [x] 3.2 Classify deterministic unsupported-route active-thread failures, such as `404` or `405`, as unsupported while preserving retryable behavior for ordinary network/server failures
- [x] 3.3 Update the active-thread poll effect to avoid overlapping requests for the same gateway and to avoid aborting an in-flight poll solely because the next interval tick arrives
- [x] 3.4 Stop active-thread polling and suppress active-thread set/clear mutations for gateways known to be unsupported until the target or gateway key changes
- [x] 3.5 Update active-thread selectors and `AgentSessionPanel` UI so unsupported gateways do not render as `Inactive thread` with an error
- [x] 3.6 Add runtime tests for unsupported active-thread detection, poller shutdown, target-change reset, and slow-poll non-flicker behavior
- [x] 3.7 Add or update workbench E2E coverage for a live discovered gateway with capabilities but no `/active-thread` route

## 4. Validation

- [x] 4.1 Run `bun run typecheck` in `apps/ag-ui-workbench`
- [x] 4.2 Run `bunx playwright test --config=playwright.config.ts tests/runtime.spec.ts` in `apps/ag-ui-workbench`
- [x] 4.3 Run `CI=1 bun run e2e` in `apps/ag-ui-workbench`
- [x] 4.4 Run `openspec validate refine-ag-ui-workbench-tmux-diagnostics-active-thread --strict --no-interactive`
