## Why

The current AG-UI workbench can target a live per-agent gateway URL, but that URL is volatile: if the agent or gateway starts after the GUI, restarts, or moves to a new port, the GUI cannot reliably reconnect by the user's intended agent identity. Agents should be addressable by stable `agent_id` or unambiguous `agent_name`, while gateway coordinates remain derived live metadata.

## What Changes

- Treat `agent_id` and unambiguous `agent_name` as first-class durable AG-UI GUI targets.
- Add passive-server resolution behavior that can distinguish known/offline agents from unknown agents, and can expose current gateway coordinates whenever a named agent is live.
- Update the workbench so discovered-agent panes persist the agent address and actively resolve/reconnect to the current gateway instead of treating the initially resolved gateway URL as durable.
- Keep the gateway passive: it publishes live coordinates and serves AG-UI routes, but it does not search for, remember, or call back to GUIs.
- Add durable AG-UI event cursor semantics so GUI reconnect can request events after `lastSeenEventId` when gateway retention is available, and otherwise falls back to a fresh snapshot.
- Update AG-UI publish reporting and agent-facing guidance so `delivered_count = 0` can mean "stored for later replay" when `stored_count > 0`, rather than always meaning the GUI missed the event forever.
- Preserve direct manual AG-UI URL entry as an explicit low-level fallback for tests and third-party endpoints.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `agent-discovery-registry`: add durable known-agent resolution semantics distinct from live gateway presence.
- `passive-server-agent-discovery`: expose agent-address resolution suitable for GUI reconnect, including offline-known and current-gateway states.
- `per-agent-ag-ui-attachment`: add resumable AG-UI connect/event semantics using `lastSeenEventId`, durable event IDs, and bounded replay or snapshot fallback.
- `ag-ui-workbench-agent-picker`: make selected discovered-agent targets agent-addressed rather than one-time direct gateway URLs.
- `ag-ui-workbench-app`: add active resolve/reconnect behavior for agent-addressed panes while keeping manual direct targets supported.
- `houmao-agent-ag-ui-skill`: revise publish guidance for durable event storage and reconnect-aware delivery reporting.

## Impact

- Affected Python areas: shared registry models/storage/resolution, passive-server discovery and agent resolution routes, per-agent AG-UI routes, AG-UI event hub/persistence, gateway client/CLI publish response models, and related unit/integration tests.
- Affected frontend areas: `apps/ag-ui-workbench` target storage, discovery picker, AG-UI client connection lifecycle, reconnect state display, and Playwright coverage.
- Affected docs/skills: Houmao AG-UI system skill guidance and any workbench documentation that currently describes discovered targets as direct gateway URLs.
- Compatibility: manual direct AG-UI URLs remain supported, but discovered-agent targets should migrate toward stable agent address metadata and may refresh their gateway URL automatically.
