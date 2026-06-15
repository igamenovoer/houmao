## Context

The completed Plotly reset makes `houmao.graphic.template` the Layer 1 chart component: schema version `2`, Plotly-only renderer metadata, curated traces/layout/config, and no raw Vega-Lite escape hatch. The advanced graphing plan reserves Vega-Lite for Layer 2 so agents can express custom declarative graphics without expanding Layer 1 into a general plotting DSL.

The current implementation has useful seams for this change. Python authoring owns typed component models and schema discovery in `src/houmao/ag_ui/authoring.py`. Capability metadata is built in `src/houmao/ag_ui/capabilities.py`. The workbench renders completed Houmao tool calls through a component renderer registry in `apps/ag-ui-workbench/src/ag-ui/componentRenderers.tsx`, with the Plotly Layer 1 renderer isolated in `templateGraphics.tsx`.

Altair is already available in the Pixi Python environment and can emit Vega-Lite v6 JSON from `chart.to_dict()` without requiring the gateway or GUI to run Python. The workbench does not yet declare `vega`, `vega-lite`, or `vega-embed`, and `vl-convert-python` is not installed, so the first Layer 2 slice should render Vega-Lite in the browser and avoid mandatory Python-side compilation.

## Goals / Non-Goals

**Goals:**

- Add a Layer 2 typed component named `houmao.graphic.vegalite`.
- Allow agents to send either hand-authored Vega-Lite specs or JSON specs generated through optional Python Altair authoring.
- Keep Altair as an authoring convenience. Payloads carry declarative JSON, not Python source.
- Validate a strict Houmao envelope around the Vega-Lite spec before rendering standard AG-UI events.
- Accept common Altair-generated Vega-Lite v6 shape, including the Vega-Lite `$schema` URL.
- Reject remote `data.url`, unsafe inline HTML/script content, JavaScript URLs, iframes, scriptable SVG, and oversized inline payloads.
- Render the payload in the workbench with `vega-embed` and clean up mounted Vega views on rerender or unmount.
- Expose Layer 2 in capability metadata as `presentation.vegaDsl`, separate from Layer 1 `presentation.templateGraphics`.
- Update `houmao-interop-ag-ui` so agents choose the least powerful graphics layer that satisfies the task.

**Non-Goals:**

- Do not add direct raw Vega (`houmao.graphic.vega`) in the first release.
- Do not add `vl-convert-python` as a required dependency or require Python compile/preflight for ordinary validation.
- Do not execute Python, Altair, JavaScript, HTML, or arbitrary callbacks in the gateway.
- Do not support remote Vega data loading, remote image loading, or browser network fetches from Vega specs by default.
- Do not implement presentation datasource bindings for Vega-Lite specs in this change.
- Do not add D3 scripted graphics or any sandboxed JavaScript runtime.
- Do not weaken Layer 1: `houmao.graphic.template` remains Plotly-backed and continues rejecting Vega-Lite renderer ids and `extra.vega-lite`.

## Decisions

### Add `houmao.graphic.vegalite` as a sibling component

Layer 2 should enter the Houmao component registry as a separate component named `houmao.graphic.vegalite`. It should not reuse `houmao.graphic.template`, `renderer.preferred: "vega-lite"`, or `extra.vega-lite`.

This keeps the component namespace readable:

```text
Layer 1  houmao.graphic.template   curated Plotly-backed chart intent
Layer 2  houmao.graphic.vegalite   declarative Vega-Lite DSL spec
Layer 3  houmao.graphic.d3_script  planned scripted sandbox, still out of scope
```

Alternative considered: re-enable Vega-Lite as a Layer 1 renderer. That would undo the Plotly reset and bring renderer fallback semantics back into the template layer.

### Use a strict Houmao envelope around raw Vega-Lite JSON

The payload should look like this:

```json
{
  "schemaVersion": 1,
  "library": "vega-lite",
  "specVersion": "6",
  "title": "Queue Status",
  "description": "Optional summary",
  "spec": {
    "$schema": "https://vega.github.io/schema/vega-lite/v6.4.1.json",
    "data": {
      "values": [
        { "status": "ready", "count": 58 },
        { "status": "queued", "count": 23 }
      ]
    },
    "mark": "bar",
    "encoding": {
      "x": { "field": "status", "type": "nominal" },
      "y": { "field": "count", "type": "quantitative" }
    }
  },
  "display": {
    "height": 360,
    "caption": "Optional caption"
  }
}
```

The envelope gives Houmao stable fields for schema versioning, capability metadata, display hints, and future policy while preserving Vega-Lite's own grammar inside `spec`.

Alternative considered: accept raw Vega-Lite specs directly as the tool-call arguments. That would reduce nesting, but it would make schema versioning, title display, capability reporting, and future direct Vega support less explicit.

### Treat Altair as optional authoring, not runtime execution

Agents may use Python Altair to generate the `spec` object:

```python
import altair as alt

chart = alt.Chart(
    alt.Data(values=[
        {"status": "ready", "count": 58},
        {"status": "queued", "count": 23},
    ])
).mark_bar().encode(
    x="status:N",
    y="count:Q",
)
spec = chart.to_dict()
```

The agent sends `spec` in `houmao.graphic.vegalite`. The gateway and workbench receive JSON and do not run Altair, pandas, Python code, or notebook display hooks.

Alternative considered: add a helper command that accepts Python or Altair code and emits events. That would introduce code execution, dependency isolation, and file access concerns. It can be revisited later as an offline authoring helper, not as the first Layer 2 runtime contract.

### Validate shape and safety in Python, compile in the browser

Python validation should verify the Houmao envelope, require `library: "vega-lite"` and `specVersion: "6"`, require `spec` to be a JSON object, enforce byte and inline-row limits, and reject high-risk content. It should not require `vl-convert-python` or compile the Vega-Lite spec by default.

The workbench should use `vega-embed` to parse and render the spec. Compile or runtime failures become visible invalid-component diagnostics rather than gateway errors.

Alternative considered: require `vl-convert-python` preflight during `houmao-mgr internals ag-ui components validate`. This would catch some errors earlier but adds a native dependency and diverges from the current environment where `vl-convert-python` is absent.

### Allow Vega-Lite schema URLs while rejecting remote data

Altair emits a `$schema` URL such as `https://vega.github.io/schema/vega-lite/v6.4.1.json`. Validation should allow that known schema URL pattern. It should still reject remote data and asset loading such as `data.url`, nested `url` fields used for external loads, or arbitrary HTTP(S) strings outside explicitly allowed schema metadata.

This means Layer 2 cannot reuse the Layer 1 "reject every remote URL string" traversal unchanged. It needs a Vega-Lite-aware traversal that distinguishes schema identity from data loading.

Alternative considered: strip `$schema` from Altair specs before validation. That makes examples less faithful to real Altair output and creates extra repair work for agents.

### Add browser-side Vega dependencies and renderer cleanup

The workbench should add `vega`, `vega-lite`, and `vega-embed` as frontend dependencies. The renderer should mount into a bounded component frame, call `vegaEmbed(container, spec, options)`, disable renderer actions by default, apply workbench sizing/theme defaults where possible, and call `view.finalize()` or the returned cleanup path on rerender/unmount.

Browser validation remains required because published AG-UI events can bypass Python authoring validation. Browser validation can be lighter than Python validation, but it must reject obvious unsafe shapes and show a fallback instead of crashing the pane.

Alternative considered: render through a server-side workbench Fastify route. That would complicate local server state and is unnecessary for client-side Vega-Lite rendering.

### Advertise Layer 2 separately in capabilities

Capabilities should add a sibling block under `custom.houmao.presentation`:

```json
{
  "vegaDsl": {
    "supported": true,
    "toolNames": ["houmao.graphic.vegalite"],
    "libraries": [
      { "name": "vega-lite", "majorVersions": ["6"], "pythonAuthoring": ["altair"] },
      { "name": "vega", "supported": false, "planned": true }
    ],
    "renderer": "vega-embed",
    "remoteData": "disabled",
    "inlineData": true,
    "preflight": {
      "pythonCompile": false,
      "browserCompile": true
    }
  }
}
```

Layer 1 capability metadata should continue to report `templateGraphics.rawVegaLiteDsl: false`. That value means raw Vega-Lite is not part of Layer 1, not that Houmao lacks a separate Layer 2 component.

Alternative considered: replace the Layer 1 `rawVegaLiteDsl` boolean with a broader graphics-layers object. That may be useful later, but the smaller change can add `vegaDsl` without destabilizing existing capability consumers.

## Risks / Trade-offs

- Vega-Lite specs may be large or expensive to render -> enforce payload byte, inline row, and nested object limits; add browser error fallback.
- Security validation may accidentally reject valid Altair output -> allow known Vega-Lite `$schema` URLs and inline `data.values`; add tests with real Altair-generated JSON.
- Security validation may miss a remote-loading path -> start with a conservative traversal for `url` fields and HTTP(S) strings except allowed schema metadata; keep remote loading disabled in `vega-embed` loader options.
- Browser bundle size grows -> add only the Vega packages needed for Layer 2 and keep Plotly Layer 1 unchanged.
- Python validation cannot catch every Vega-Lite compile error without `vl-convert-python` -> surface compile errors through visible workbench diagnostics and keep `preflight.pythonCompile: false` in capabilities.
- Agent guidance may overuse Layer 2 for ordinary charts -> update the skill to prefer Layer 1 first and use Vega-Lite only for custom declarative graphics.

## Migration Plan

1. Add Python constants, Pydantic models, schema examples, and prevalidation for `houmao.graphic.vegalite`.
2. Register `houmao.graphic.vegalite` in the component registry and allow dashboard children to include it.
3. Extend capabilities and AG-UI tool metadata to advertise Layer 2 `vegaDsl` support when generated graphics are available.
4. Add unit tests for schema discovery, valid hand-authored payloads, valid Altair-shaped payloads, rejected remote data URLs, rejected unsafe inline content, rendered AG-UI events, and capability metadata.
5. Add workbench dependencies and a `vegaDslGraphics` renderer mounted through the existing component renderer registry.
6. Add browser tests for successful render, malformed spec fallback, remote data rejection, cleanup after rerender/clear, and Debug Agent fixture publishing.
7. Update docs, examples, real-agent smoke guidance, and the `houmao-interop-ag-ui` system skill.

Rollback is source-control rollback while this feature remains experimental. If partial rollback is required, remove `houmao.graphic.vegalite` from component discovery and capabilities first so agents stop emitting Layer 2 payloads, then remove the workbench renderer and dependencies.

## Open Questions

- What initial payload limits should be enforced for maximum encoded payload bytes and maximum inline `data.values` rows?
- Should the browser renderer use SVG or canvas as the default Vega renderer?
- Should direct raw Vega become a second component in the next Layer 2 change or wait until datasource support exists?
