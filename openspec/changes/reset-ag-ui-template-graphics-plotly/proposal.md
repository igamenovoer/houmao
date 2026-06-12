## Why

The current Layer 1 template graphics experiment advertises and implements multiple browser renderers, which makes agent guidance, validation, fallback behavior, and future graphing layers harder to reason about. The advanced AG-UI graphing plan now standardizes Layer 1 around Plotly.js, with Vega-Lite reserved for a later Layer 2 DSL path.

## What Changes

- **BREAKING**: Reset `houmao.graphic.template` to a Plotly-first Layer 1 schema instead of the current `data.values` plus `encoding` schema.
- **BREAKING**: Replace Layer 1 renderer ids `recharts` and `vega-lite` with a single supported renderer id: `plotly`.
- **BREAKING**: Remove Layer 1 renderer fallback semantics from the public contract; `renderer.preferred` defaults to `plotly` and any non-Plotly renderer is invalid or diagnostic-only compatibility input.
- **BREAKING**: Retire Recharts completely from the AG-UI workbench, including template rendering, renderer override controls, tests, and frontend dependencies.
- **BREAKING**: Remove the legacy fixed chart component APIs `houmao.chart.bar`, `houmao.chart.line`, and `houmao.chart.pie` from schema discovery, authoring guidance, workbench registered renderers, debug fixtures, docs, and tests instead of preserving those APIs on Plotly.
- Add a curated Plotly-aligned payload shape with trace-like series, layout-like display fields, config-like interaction fields, optional datasource references, and optional `extra.plotly` refinements.
- Add static inline chart support under `houmao.graphic.template` for the five initial 2D chart types: `bar`, `line`, `scatter`, `pie`, and `histogram`.
- Defer broader Plotly 2D chart coverage, including area, bubble, donut, heatmap, box, violin, financial, map, polar, ternary, flow, hierarchy, image, table-style, and parallel-coordinate chart families.
- Add datasource binding vocabulary to the schema and capabilities as a contract-only shape for a future runtime, without implementing datasource materialization in this round.
- Update capabilities, docs, system skill guidance, debug/fake agent fixtures, and smoke prompts to advertise Plotly as the only Layer 1 template renderer and to use `houmao.graphic.template` rather than `houmao.chart.*`.
- Keep raw Vega-Lite, raw Vega, D3, arbitrary JavaScript, HTML, iframes, and remote data loading out of Layer 1.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `ag-ui-template-graphics`: Reset the Layer 1 template graphic schema, renderer contract, extra policy, capability metadata, workbench rendering behavior, and agent guidance around Plotly.js.
- `ag-ui-workbench-app`: Remove Recharts-backed rendering, fixed `houmao.chart.*` registered renderers, and template renderer override UI from the workbench, and require Plotly-backed rendering for template graphics.
- `ag-ui-copilotkit-graphics`: Remove the obsolete workbench template renderer override behavior that depended on multi-renderer fallback and Recharts.
- `houmao-ag-ui-message-authoring`: Remove legacy fixed chart components from the discoverable Houmao component namespace and authoring examples.
- `houmao-interop-ag-ui-skill`: Update GUI authoring guidance so chart examples use the Plotly-backed `houmao.graphic.template`, not `houmao.chart.*`.
- `ag-ui-workbench-debug-agent`: Replace debug chart fixtures and typed component sender examples that use `houmao.chart.*`.
- `ag-ui-workbench-client-event-cache`: Keep cache semantics component-agnostic while replacing fixed-chart examples with Plotly-backed template graphics.
- `per-agent-ag-ui-attachment`: Keep gateway ingestion opaque to component semantics while replacing fixed-chart examples with current Houmao component names.

## Impact

- Python AG-UI authoring models, validation, JSON Schema export, component examples, and capability metadata in `src/houmao/ag_ui/`.
- Workbench template rendering, registered typed component rendering, renderer selection UI, storage sanitization, debug agent payloads, fake server fixtures, browser tests, and dependencies under `apps/ag-ui-workbench/`.
- Plotly.js source/schema reference at `extern/orphan/plotly.js`, especially the trace modules for the five initial chart types.
- Workbench diagnostics for datasource-bound template payloads that cannot be materialized yet.
- AG-UI reference docs and `houmao-interop-ag-ui` system skill guidance.
- Existing experimental template payloads using `renderer.preferred: "vega-lite"`, `renderer.fallback: ["recharts"]`, `data.values`, `encoding`, or `extra.vega-lite` must be rewritten for the Plotly-aligned schema.
- Existing legacy fixed chart payloads using `houmao.chart.bar`, `houmao.chart.line`, or `houmao.chart.pie` must be rewritten to `houmao.graphic.template`.
- Any workbench code that imports from `recharts` or depends on Recharts-specific DOM/test selectors must be migrated to Plotly or removed in this change.
