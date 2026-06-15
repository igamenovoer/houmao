## Why

Layer 1 template graphics currently support only five Plotly-backed chart intents, which forces agents to choose Layer 2 Vega-Lite for ordinary Plotly chart families such as heatmaps, box plots, financial traces, polar charts, Sankey diagrams, tables, and treemaps. The advanced graphing plan wants Layer 1 to remain Plotly-only and templated, but the current `chartType` enum is too small to represent Plotly.js 2D coverage.

## What Changes

- **BREAKING**: Replace the schema version 2 `chartType`-first template contract with a schema version 3 Plotly 2D template contract whose supported surface is defined by a Houmao-owned trace catalog.
- Support every Plotly.js trace family that is not a true 3D scene trace, subject to Houmao validation, safety policy, bundle capability, and offline rendering constraints.
- Reject Plotly true 3D trace families such as `scatter3d`, `surface`, `mesh3d`, `cone`, `streamtube`, `volume`, and `isosurface`.
- Keep Layer 1 as a curated Houmao template schema, not raw unrestricted Plotly figure JSON.
- Replace the current cartesian-only Plotly browser bundle with a Plotly bundle capable of rendering the allowed 2D trace catalog.
- Introduce catalog-backed validation artifacts shared by Python authoring, TypeScript workbench validation, capability metadata, examples, and tests.
- Generalize datasource bindings from fixed `source.x` and `source.y` style fields to catalog-backed field-path bindings such as `source.bindings.open`, `source.bindings.node.label`, and `source.bindings.link.value`.
- Update capabilities and agent guidance so agents discover supported Plotly 2D trace types rather than relying on a five-item chart type list.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `ag-ui-template-graphics`: Replace the limited schema version 2 chart-type contract with schema version 3 Plotly 2D trace-catalog support, including validation, capabilities, datasource bindings, and workbench rendering requirements.
- `houmao-interop-ag-ui-skill`: Update agent guidance so ordinary Plotly 2D charts use `houmao.graphic.template` and only custom declarative Vega-Lite grammar stays on `houmao.graphic.vegalite`.

## Impact

- Python AG-UI authoring models and validation in `src/houmao/ag_ui/authoring.py`.
- Capability metadata in `src/houmao/ag_ui/capabilities.py`.
- Workbench template graphics validation and Plotly rendering in `apps/ag-ui-workbench/src/ag-ui/templateGraphics.tsx` and related debug-agent validation fixtures.
- Workbench package dependencies, replacing the cartesian-only Plotly bundle with a broader Plotly 2D bundle strategy.
- Documentation and examples under `docs/reference/gateway/ag-ui.md`.
- The maintained `houmao-interop-ag-ui` system skill content.
- Unit, integration, and Playwright coverage for schema validation, capability metadata, catalog generation, and visible rendering across representative Plotly 2D trace families.
