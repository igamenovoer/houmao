## Why

Houmao agents should be able to produce GUI updates without depending on headless-only artifact mapping or a Houmao-specific gateway extension that understands every rendered component. AG-UI already provides the standard event stream shape, while CopilotKit-style typed components are an application-layer protocol, so Houmao needs a clear split between standard AG-UI events and Houmao-owned component schemas.

## What Changes

- Add `houmao-mgr` AG-UI authoring commands that expose Houmao GUI component schemas, validate typed component messages, and render those messages into standard AG-UI event sequences.
- Define a Houmao application-layer GUI message schema namespace for reusable typed components such as bar charts, line charts, tables, metric grids, and dashboards.
- Add a gateway ingestion route for already-standard AG-UI events so an agent can publish GUI messages through the local gateway without making the gateway understand Houmao component schemas.
- Teach Houmao agents how to send AG-UI messages through a packaged system skill that uses `houmao-mgr` for schema discovery, validation, rendering, and optional Houmao-gateway publishing.
- Expand the AG-UI workbench renderer registry so it can render Houmao typed component messages carried over standard AG-UI tool/custom events, similar to CopilotKit demo dashboards.
- Keep the agent gateway as a standard AG-UI protocol boundary: it validates AG-UI event envelopes, stream routing, ordering, size limits, and safe replay metadata, but it does not validate Houmao component semantics.

## Capabilities

### New Capabilities

- `houmao-ag-ui-message-authoring`: Covers `houmao-mgr` commands, shared schemas, validation, rendering, and Houmao-gateway publish helper behavior for converting Houmao typed GUI messages into standard AG-UI events.
- `houmao-agent-ag-ui-skill`: Covers the packaged Houmao system skill that teaches agents how to discover schemas, validate messages, render AG-UI events, publish those events through Houmao gateways, and hand generated events to agents for third-party endpoint delivery when needed.

### Modified Capabilities

- `per-agent-ag-ui-attachment`: The live per-agent gateway gains a standard AG-UI event ingestion surface and validates only standard AG-UI event shapes and routing constraints.
- `ag-ui-workbench-app`: The workbench gains a renderer registry for Houmao typed component names carried inside standard AG-UI events, rather than depending only on `houmao_render_graphic` SVG tool calls.

## Impact

- Affected CLI code: `src/houmao/srv_ctrl/commands/internals.py`, a new AG-UI authoring command module, and likely `src/houmao/srv_ctrl/commands/agents/gateway.py` for Houmao-gateway publish helpers.
- Affected shared models: new or extended AG-UI/Houmao GUI schema models under `src/houmao/ag_ui/` or a nearby shared package.
- Affected gateway code: per-agent gateway AG-UI routes, event validation, event bus/replay bookkeeping, and client helpers.
- Affected frontend code: `apps/ag-ui-workbench/src/ag-ui/` reducer/rendering code and deterministic Playwright fixtures for component rendering.
- Affected system-skill assets: a new packaged Houmao AG-UI skill and catalog/installation metadata so managed agents can learn the workflow.
- Tests should cover CLI schema discovery/validation/rendering, gateway AG-UI event ingestion, workbench renderer behavior, and a documented agent workflow that can publish through a gateway while remaining AG-UI-conforming.
