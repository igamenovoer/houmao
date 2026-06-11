## Why

Houmao AG-UI currently supports fixed chart components and a compatibility graphics path, but agents cannot emit one standardized chart-intent payload that can be rendered by multiple backends. Adding Layer 1 template graphics gives agents a stable JSON contract while letting the GUI choose a renderer such as Recharts or Vega-Lite.

## What Changes

- Add a new Houmao AG-UI component/tool contract named `houmao.graphic.template` for standardized chart JSON.
- Support renderer selection metadata with initial renderer ids `recharts` and `vega-lite`.
- Add a renderer-scoped `extra` object for optional backend-specific refinements that cannot replace the standardized chart contract.
- Render `houmao.graphic.template` as standard AG-UI tool-call events through the existing `houmao-mgr internals ag-ui` authoring flow.
- Add Vega-Lite rendering to `apps/ag-ui-workbench` while keeping the gateway publish endpoint responsible only for standard AG-UI event validation and live fanout.
- Advertise Layer 1 template graphics support and renderer metadata in AG-UI capabilities.
- Update agent-facing guidance and reference docs so agents choose Layer 1 for ordinary charts and reserve raw Vega-Lite specs for a later Layer 2 capability.

## Capabilities

### New Capabilities
- `ag-ui-template-graphics`: Standardized Houmao Layer 1 chart JSON, offline authoring validation, AG-UI event rendering, capability metadata, and workbench rendering with Recharts and Vega-Lite backends.

### Modified Capabilities
- None.

## Impact

- Python AG-UI authoring models and registry under `src/houmao/ag_ui/`.
- `houmao-mgr internals ag-ui` schema, validation, and event-rendering commands.
- Gateway capability metadata under `GET /v1/ag-ui/capabilities`.
- Workbench renderer code under `apps/ag-ui-workbench/src/ag-ui/` and workbench package dependencies for Vega-Lite rendering.
- Debug workbench fixtures, tests, gateway reference docs, and `houmao-interop-ag-ui` skill guidance.
