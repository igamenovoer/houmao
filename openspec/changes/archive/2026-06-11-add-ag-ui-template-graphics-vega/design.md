## Context

The current AG-UI presentation path has three separated responsibilities. `houmao.ag_ui.authoring` defines Houmao-owned component schemas, validates payloads offline, and renders standard AG-UI tool-call events. The per-agent gateway accepts already-standard AG-UI events, validates event shape and routing only, and fans them out to active GUI streams. The workbench reconstructs completed tool calls and renders known Houmao component names with local React renderers.

Layer 1 template graphics should follow that split. The new contract adds one standardized chart-intent payload named `houmao.graphic.template`. Python authoring validates this renderer-neutral payload and emits standard AG-UI events. The gateway remains application-payload agnostic. The workbench chooses a renderer backend and renders the standardized payload through Recharts or a generated Vega-Lite spec.

The repository already depends on `pydantic` and `jsonschema`. The workbench already depends on Recharts. This change adds browser-side Vega dependencies for rendering. Python Vega bindings are useful later, but they are not required for the first Layer 1 runtime because the browser must render interactive Vega-Lite views.

## Goals / Non-Goals

**Goals:**

- Add `houmao.graphic.template` as the first standardized Layer 1 graphics component.
- Validate a stable Houmao JSON schema offline through `houmao-mgr internals ag-ui`.
- Support initial chart types `bar`, `line`, `scatter`, `area`, and `pie`.
- Support renderer choice with `preferred` and `fallback` renderer ids.
- Support `recharts` and `vega-lite` as initial renderers.
- Allow renderer-scoped `extra` values only as optional refinements.
- Advertise template graphics renderer support in AG-UI capabilities.
- Update workbench fixtures and agent-facing guidance.

**Non-Goals:**

- Do not accept raw Vega-Lite specs in Layer 1. Raw Vega-Lite belongs to Layer 2.
- Do not execute generated JavaScript, HTML, SVG, or React code.
- Do not add custom user templates.
- Do not make the gateway compile, validate, or render Vega-Lite.
- Do not require Altair, VegaFusion, or `vl-convert-python` in the base Python runtime.
- Do not remove or break existing `houmao.chart.*`, table, metric, dashboard, or `houmao_render_graphic` paths.

## Decisions

### Use a new component name instead of replacing fixed chart components

`houmao.graphic.template` becomes the Layer 1 contract. Existing names such as `houmao.chart.bar` remain valid compatibility components.

Alternative considered: add `renderer` and `extra` fields to every existing chart schema. That would spread the Layer 1 model across several component names and keep old one-off data shapes. A new component lets the schema normalize data and encoding once.

### Keep the standardized schema grammar-of-graphics shaped

The payload uses `data.values` plus `encoding` channels. Encodings include `field`, `type`, optional `title`, and renderer-neutral hints such as aggregate, sort, color, tooltip, and series fields where needed.

Alternative considered: reuse the current `{label, value}` chart data shape. That shape works for simple bar and pie charts, but it does not generalize cleanly to scatter, multi-series line, area, tooltips, or Vega-Lite.

### Use renderer-scoped `extra` as a narrow refinement channel

`extra` is an object keyed by renderer id. The standardized fields must be sufficient to render the chart. Unsupported renderer keys and unsupported fields inside a known renderer block are ignored by renderers or shown as non-fatal diagnostics.

The `extra.vega-lite` block may carry safe presentation fragments such as `config`, mark style, axis style, legend style, and view sizing hints. It must not carry raw `data`, `datasets`, `transform`, `layer`, `facet`, `concat`, full `encoding`, raw `params`, JavaScript callbacks, URLs, or a complete spec replacement.

Alternative considered: let `extra.vega-lite` merge arbitrary Vega-Lite fragments into the generated spec. That would turn Layer 1 into an undocumented Layer 2 and would make fallback renderers unreliable.

### Render Vega-Lite in the workbench, not the gateway

The workbench adds `vega`, `vega-lite`, and `vega-embed`. It converts the standardized payload to a Vega-Lite spec and mounts it in a bounded React component. The gateway continues to validate only standard AG-UI event shape and routing.

Alternative considered: compile or preflight Vega-Lite in Python with `vl-convert-python`. That can be useful for later export or stricter validation, but it adds runtime weight and does not remove the need for browser rendering.

### Keep Python Vega bindings optional

Vega-Altair is the recommended Python authoring binding for future Layer 2 examples and user-side generation of raw Vega-Lite specs. `vl-convert-python` is the optional compile/export helper. Neither belongs in the base implementation of Layer 1.

Alternative considered: require Altair and author Layer 1 charts through Altair objects. That would make Python the chart-building runtime and would complicate agent use outside Python notebooks.

### Advertise presentation capabilities through Houmao custom metadata

`GET /v1/ag-ui/capabilities` adds `custom.houmao.presentation.templateGraphics` with supported renderer ids, default renderer, chart types, schema version, and `extra` policy. The standard AG-UI tool list may also include `houmao.graphic.template` where generated graphics are supported.

Alternative considered: rely only on CLI schema discovery. CLI discovery is still needed for agents, but GUI clients need runtime capability metadata before streams start.

## Risks / Trade-offs

- Browser bundle size grows with Vega dependencies → Keep Vega-Lite isolated to the template renderer and consider dynamic import if bundle size becomes a problem.
- Recharts and Vega-Lite differ visually for the same standardized payload → Treat exact visual parity as a non-goal and test semantic rendering, fallback behavior, and diagnostics.
- `extra` can drift into backend-native specs → Enforce an allowlist in Python validation and keep workbench adapter behavior conservative.
- Vega-Lite render lifecycle can leak views → Encapsulate rendering in a component that calls Vega view cleanup on unmount and rerender.
- Existing fixed chart components and new template graphics may overlap → Document fixed components as compatibility/simple components and teach agents to prefer `houmao.graphic.template` for new Layer 1 graphics.
