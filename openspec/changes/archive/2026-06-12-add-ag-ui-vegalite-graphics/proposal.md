## Why

Layer 1 template graphics are now intentionally Plotly-backed and curated, leaving no supported path for custom declarative graphics that need Vega-Lite grammar, Altair output, interactive selections, layering, or linked views. Layer 2 should provide that higher-freedom declarative path without reopening Layer 1 renderer selection or allowing arbitrary JavaScript execution.

## What Changes

- Add a Layer 2 Vega-Lite typed component named `houmao.graphic.vegalite`.
- Allow agents to hand-author Vega-Lite JSON or optionally use Python Altair to generate a Vega-Lite spec with `chart.to_dict()` or `chart.to_json()`, then send the resulting JSON in the component payload.
- Keep Altair as an agent/tooling-side authoring convenience; the gateway and workbench SHALL receive declarative JSON and SHALL NOT execute Python or Altair code at render time.
- Add backend authoring validation for the Vega-Lite envelope, inline-data limits, forbidden remote data URLs, unsafe inline content, and Altair-generated Vega-Lite v6 `$schema` URLs.
- Add workbench rendering for `houmao.graphic.vegalite` using `vega`, `vega-lite`, and `vega-embed`, with visible compile/runtime diagnostics and renderer cleanup.
- Add capability metadata that exposes Layer 2 as `presentation.vegaDsl`, separate from Layer 1 `templateGraphics`, and keeps `templateGraphics.rawVegaLiteDsl` false.
- Add deterministic examples and Debug Agent fixtures for hand-authored and Altair-shaped Vega-Lite payloads.
- Defer direct raw Vega (`houmao.graphic.vega`), `vl-convert-python` preflight compilation, datasource-backed Vega specs, and D3 scripted graphics.
- Update docs and `houmao-interop-ag-ui` guidance so agents choose Layer 1 for ordinary Plotly-backed charts and Layer 2 Vega-Lite for custom declarative graphics.

## Capabilities

### New Capabilities
- `ag-ui-vegalite-graphics`: Layer 2 Vega-Lite graphics contract, validation, capabilities, browser rendering, Altair authoring guidance, and safety policy.

### Modified Capabilities
- `houmao-ag-ui-message-authoring`: Add `houmao.graphic.vegalite` to the Houmao typed component namespace and authoring/render validation workflow.
- `ag-ui-workbench-app`: Add a Vega-Lite renderer path in the typed component renderer registry and required frontend dependencies.
- `per-agent-ag-ui-attachment`: Extend capabilities and AG-UI tool metadata to report Layer 2 Vega-Lite support without changing gateway lifecycle or routing semantics.
- `ag-ui-workbench-debug-agent`: Add debug payloads and fixtures for valid and invalid Vega-Lite graphics.
- `houmao-interop-ag-ui-skill`: Teach agents the Layer 1 versus Layer 2 selection rule, optional Altair authoring path, validation workflow, and Layer 2 safety limits.

## Impact

- Python AG-UI authoring models, component schema registry, validation helpers, JSON Schema examples, capability metadata, and unit tests under `src/houmao/ag_ui/`.
- `houmao-mgr internals ag-ui components ...` and `events render ...` behavior through the existing generic component authoring commands.
- Workbench typed component rendering, Debug Agent examples, package dependencies, browser tests, and renderer cleanup under `apps/ag-ui-workbench/`.
- AG-UI reference docs, system-skill guidance, and real-agent smoke prompts for custom declarative graphics.
- Existing Layer 1 `houmao.graphic.template` payloads remain Plotly-backed and SHALL NOT accept Vega-Lite as `renderer.preferred`, `renderer.fallback`, or `extra.vega-lite`.
