## Why

The AG-UI workbench currently expects testers to know each Houmao agent gateway address before they can attach a pane. This slows manual and E2E validation because available agents are already discoverable through the passive server, but the GUI does not expose that list or provide a pane-targeting workflow.

## What Changes

- Add passive-server discovery configuration to the AG-UI workbench so a tester can point the GUI at a Houmao passive server and refresh the current agent list.
- Add an agent picker that lists discovered Houmao agents, shows gateway availability, and supports search or filtering.
- Allow a tester to double-click a discovered agent to retarget an existing pane when the picker was opened from that pane.
- Allow a tester to double-click a discovered agent, or use an explicit row action, to open a new docked pane when the picker was opened from the global toolbar.
- Resolve selected agents through the existing passive-server gateway status endpoint and derive the direct per-agent AG-UI target URL for `/v1/ag-ui`.
- Keep explicit gateway address entry as a first-class path for non-local passive servers, manually forwarded gateways, and cases where discovery cannot resolve a browser-reachable AG-UI URL.
- Extend the workbench local proxy as needed so browser tests can fetch passive-server discovery and gateway status through the same target-policy boundary as AG-UI calls.
- Add deterministic Playwright coverage with a fake passive server and fake AG-UI targets for listing, retargeting, new-pane creation, manual URL fallback, and unavailable gateway states.
- Update the AG-UI integration roadmap and workbench documentation to describe the agent picker workflow.

## Capabilities

### New Capabilities

- `ag-ui-workbench-agent-picker`: Defines passive-server-backed Houmao agent discovery in the AG-UI workbench, including list display, target resolution, existing-pane retargeting, new-pane creation, manual gateway fallback, persistence boundaries, and E2E coverage.

### Modified Capabilities

- None.

## Impact

- Changes are scoped to `apps/ag-ui-workbench/`, its README and E2E tests, and `context/plans/ag-ui-integration/roadmap.md`.
- The workbench depends on existing passive-server endpoints: `GET /houmao/agents` and `GET /houmao/agents/{agent_ref}/gateway`.
- The change does not add passive-server AG-UI proxy routes and does not change Houmao agent lifecycle ownership.
- The GUI remains outside the PyPI package and no Python package include rules should change.
- The local proxy policy remains restrictive: loopback targets work by default, while non-loopback passive servers or gateways require explicit allowlist configuration.
