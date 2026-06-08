## 1. Discovery Contracts and Storage

- [ ] 1.1 Add workbench TypeScript types for passive-server discovery responses, gateway-status target resolution, discovered target metadata, and picker invocation context.
- [ ] 1.2 Extend `WorkbenchStorage` and `TargetConfig` sanitization so the app can persist passive-server base URL and optional manual or discovered source metadata without breaking existing saved manual panes.
- [ ] 1.3 Add storage test hooks or assertions so E2E can verify selected discovered-agent metadata persists while discovered-agent list responses and stream data do not persist.

## 2. Discovery Client and Proxy

- [ ] 2.1 Implement a discovery client that normalizes the passive-server base URL, fetches `GET /houmao/agents` through the workbench proxy, and returns typed picker rows with deterministic error messages.
- [ ] 2.2 Implement selected-agent resolution through `GET /houmao/agents/{agent_ref}/gateway`, including missing-gateway handling, wildcard host normalization, and direct `/v1/ag-ui` target URL construction.
- [ ] 2.3 Update `scripts/agUiProxyPlugin.ts` only as needed so passive-server JSON requests use the same protocol and host allowlist policy as AG-UI requests and preserve upstream status and response bodies.

## 3. Picker UI

- [ ] 3.1 Add an `AgentPicker` drawer or modal with passive-server URL control, refresh button, loading state, error state, search/filter input, gateway availability badges, and discovered-agent rows.
- [ ] 3.2 Add a toolbar `Agents` control that opens the picker in new-pane mode, defaults double-click to creating a docked pane, and supports choosing an existing pane as a retarget destination.
- [ ] 3.3 Add a choose-agent icon button to each `TargetForm` so the picker can open in pane-retarget mode for operator and agent panes.
- [ ] 3.4 Keep the manual label, AG-UI URL, and thread ID fields visible and make direct manual URL edits switch source metadata to manual.
- [ ] 3.5 Update workbench CSS so the picker, filters, badges, pane selector, row actions, and target-form controls fit cleanly on desktop and narrow browser widths.

## 4. Pane Creation and Retarget Lifecycle

- [ ] 4.1 Add workbench actions for creating a new agent pane from a resolved discovered target and for retargeting an existing pane while preserving Dockview placement.
- [ ] 4.2 Refactor `AgentSessionPanel` so picker-driven retargeting aborts any active stream, performs AG-UI detach when a connection ID is known, clears capabilities and reduced event state, and then applies the new target metadata.
- [ ] 4.3 Ensure retargeting and new-pane creation never call Houmao lifecycle, interrupt, launch, restart, shutdown, registry cleanup, or prompt-control endpoints.
- [ ] 4.4 Ensure new discovered-agent panes have independent thread IDs, event state, connection IDs, and saved target metadata.

## 5. Deterministic Browser Tests

- [ ] 5.1 Extend the fake test server so it serves passive-server discovery, gateway-status success, no-gateway failure, and fake AG-UI targets from one deterministic fixture.
- [ ] 5.2 Add Playwright coverage for listing agents, filtering rows, retargeting an existing pane from a pane-opened picker, and verifying old pane stream evidence is cleared.
- [ ] 5.3 Add Playwright coverage for opening a new docked pane from the toolbar picker and verifying event isolation between discovered-agent panes.
- [ ] 5.4 Add Playwright coverage for manual URL fallback, manual source metadata after editing a discovered target, and disallowed non-loopback passive-server policy errors.
- [ ] 5.5 Add Playwright coverage for an unresolved gateway row that shows an error and does not retarget or create a pane with an invalid AG-UI URL.

## 6. Documentation and Roadmap

- [ ] 6.1 Update `apps/ag-ui-workbench/README.md` with the passive-server agent picker workflow, manual gateway fallback, remote or forwarded gateway guidance, and allowlist configuration.
- [ ] 6.2 Update `context/plans/ag-ui-integration/roadmap.md` to record the completed workbench app baseline and this proposed agent-picker milestone.
- [ ] 6.3 Confirm the docs continue to state that the GUI lives under `apps/ag-ui-workbench/` and is not included in the PyPI package.

## 7. Verification

- [ ] 7.1 Run `bun install` in `apps/ag-ui-workbench` if dependencies are missing or lockfile updates are required.
- [ ] 7.2 Run `bun run typecheck` in `apps/ag-ui-workbench`.
- [ ] 7.3 Run `bun run build` in `apps/ag-ui-workbench`.
- [ ] 7.4 Run `bun run e2e` in `apps/ag-ui-workbench` using Bun-global Playwright.
- [ ] 7.5 Run `openspec validate add-ag-ui-workbench-agent-picker --strict`.
