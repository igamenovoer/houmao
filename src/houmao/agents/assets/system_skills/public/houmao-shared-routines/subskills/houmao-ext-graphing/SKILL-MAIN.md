---
name: houmao-ext-graphing
description: "Use when Houmao Plotly.js templated graphics or Vega-Lite freeform graphics must be created, repaired, schema-validated, rendered as AG-UI events, or prepared for later gateway publishing."
skill_invocation_notation: >
  Top-level skill entrypoints use SKILL.md. Parent-scoped subskill entrypoints use
  SKILL-MAIN.md and are loaded explicitly through their parent; nested SKILL.md is
  accepted only as legacy input when SKILL-MAIN.md is absent.
  Skill and subskill entrypoints use bare object paths: `X` invokes skill X and
  `X->Y->Z` invokes subskill Z. Subcommands use parenthesized components:
  `X->cmd()` invokes a direct subcommand, `X->Y->cmd()` invokes a subcommand of
  subskill Y, and `X->parent()->child()` invokes child subcommand child exposed
  by parent subcommand parent. Intermediate subcommands act as object generators.
  Forms such as `X()` and `X->Y()` are invalid for skill or subskill entrypoints.
---

# Houmao Ext Graphing

## Workflow

1. **Handle explicit help first** without running schema, validation, rendering, or publishing commands.
2. **Validate the inherited actor frame** from `houmao-shared-routines` and preserve any later gateway target.
3. **Select one subcommand** from **Subcommands** and choose the least powerful graphing layer that satisfies the request.
4. **Resolve one launcher**, discover the authoritative schema or trace catalog, and author or repair the payload.
5. **Validate the payload**, render standard AG-UI events, and validate the event batch before handoff.
6. **Return the graphing result** or hand rendered events to `houmao-shared-routines->houmao-interop-ag-ui` for publishing.

If the user's task does not map cleanly to these steps, use the native planning tool to build a step-by-step plan from the graphing subcommands, layer rules, schemas, validation contract, and user request, then execute the plan.

## Subcommands

| Subcommand | Use For | Detail |
| --- | --- | --- |
| `templated-graphics` | Supported Plotly.js 2D charts through `houmao.graphic.template`. | **Templated Graphics** |
| `freeform-graphics` | Declarative Vega-Lite charts requiring custom encodings, transforms, selections, or layers. | **Freeform Graphics** |
| `help` | Read-only graphing layers, schema discovery, validation, rendering, and boundary guidance. | **Help** |

## Actor Frame Gate

This parent-scoped routine loads only through `houmao-shared-routines`. Require the immutable admin or verified-agent frame validated by that parent. Graph authoring behavior is the same for both actors, but any later gateway publication preserves the supplied actor and target through the `interop-ag-ui` route. Missing or mismatched frames fail closed.

Author built-in Houmao graphing payloads, validate them, and render them into standard AG-UI events.

This skill owns graphing payload construction. Use `houmao-shared-routines->houmao-interop-ag-ui` after rendering when the task is about AG-UI protocol framing, Houmao gateway publishing, endpoint boundaries, routing, or delivery-result interpretation.

## Help

When the user asks `$houmao-shared-routines ext-graphing help`, `help for houmao-ext-graphing`, `usage for houmao-ext-graphing`, or what this skill can do, answer from this section and stop unless they also ask for a concrete graphing action. This is read-only help: do not run commands, mutate files, send mail, change gateway state, or alter managed-agent lifecycle state during help. If the user asks a concrete task such as "help me draw a Plotly heatmap", route to the matching graphing workflow instead of stopping at generic help.

Purpose: author built-in Houmao graphing payloads without hand-writing raw AG-UI event JSON.

Available functionality:

- `help`: explain this skill's purpose and supported graphing operations.
- List built-in graphing schemas by layer.
- Inspect the Plotly.js-backed `houmao.graphic.template` schema.
- Inspect the Vega-Lite-backed `houmao.graphic.vegalite` schema.
- List supported and excluded Plotly.js template trace types.
- Choose the least powerful built-in graphing layer that satisfies the request.
- Validate graphing payload JSON.
- Render validated graphing payloads into standard AG-UI events.
- Validate rendered AG-UI event batches before handoff.

Common starting prompts:

- `$houmao-shared-routines ext-graphing help`
- `$houmao-shared-routines ext-graphing list graphing schemas`
- `$houmao-shared-routines ext-graphing create a Plotly heatmap`
- `$houmao-shared-routines ext-graphing create a Vega-Lite layered chart`
- `$houmao-shared-routines ext-graphing validate this chart payload`

Related skills and boundaries:

- Use `houmao-shared-routines->houmao-interop-ag-ui` for AG-UI protocol validation/framing beyond graphing, generic custom tool-call rendering, Houmao gateway publishing, endpoint selection, routing ids, and publish-result interpretation.
- Use `houmao-shared-routines->houmao-agent-gateway` for gateway lifecycle, attachment, status, reminders, and direct gateway controls.
- Use this skill only for built-in graphing payload authoring, validation, rendering, and graphing-specific repair.
- DO NOT use this skill to submit ordinary prompt work.

## Launcher

Choose one `houmao-mgr` launcher for the turn:

1. Run `command -v houmao-mgr` and use the command on `PATH` when present.
2. If that fails, use `uv tool run --from houmao houmao-mgr`.
3. For repo development only, use the project launcher such as `pixi run houmao-mgr`.
4. If the user names a launcher, use that launcher.

Reuse the same launcher for schema discovery, validation, rendering, and event validation in the same turn.

## Layer Choice

Choose the least powerful built-in graphing layer that satisfies the request:

1. Use `templated-graphics` for ordinary supported Plotly.js 2D charts and chart-like visualizations.
2. Use `freeform-graphics` for custom declarative Vega-Lite charts that need layering, custom encodings, transforms, selections, linked views, or chart shapes outside the Plotly.js trace catalog.
3. Do not use a custom frontend `new-component` for built-in Plotly.js or Vega-Lite graphics. Custom frontend tool-call contracts belong to `houmao-shared-routines->houmao-interop-ag-ui` when the user supplies the GUI-side implementation contract.

Current built-ins:

- `templated-graphics`: `houmao.graphic.template`, Layer 1, Plotly.js-backed, schema version `3`, `figureType: "plotly2d"`.
- `freeform-graphics`: `houmao.graphic.vegalite`, Layer 2, Vega-Lite-backed, schema version `1`, rendered by `vega-embed`.

The legacy fixed chart components are retired. Do not generate `houmao.chart.bar`, `houmao.chart.line`, or `houmao.chart.pie`.

## Discover Schemas

List graphing schemas by layer:

```bash
houmao-mgr ag-ui impl templated-graphics list
houmao-mgr ag-ui impl freeform-graphics list
```

Show schema details and examples:

```bash
houmao-mgr ag-ui impl schema houmao.graphic.template
houmao-mgr ag-ui impl schema houmao.graphic.vegalite
```

List supported and excluded Plotly.js template trace types:

```bash
houmao-mgr ag-ui impl catalog houmao.graphic.template traces
```

Do not infer schema names from Plotly trace names. `bar`, `heatmap`, `sankey`, and other Plotly trace types are catalog entries under `houmao.graphic.template`; they are not standalone Houmao implementation schema names.

## Validate and Render

Validate a graphing payload:

```bash
houmao-mgr ag-ui impl validate houmao.graphic.template --input payload.json
houmao-mgr ag-ui impl validate houmao.graphic.vegalite --input payload.json
```

Render a valid payload into standard AG-UI events:

```bash
houmao-mgr ag-ui impl render houmao.graphic.template --input payload.json > events.json
houmao-mgr ag-ui impl render houmao.graphic.vegalite --input payload.json > events.json
```

Validate the rendered event batch:

```bash
houmao-mgr ag-ui protocol events validate --input events.json
```

Supported render formats:

```bash
houmao-mgr ag-ui impl render houmao.graphic.template --input payload.json --format json
houmao-mgr ag-ui impl render houmao.graphic.template --input payload.json --format jsonl
houmao-mgr ag-ui impl render houmao.graphic.template --input payload.json --format sse
houmao-mgr ag-ui protocol events frame --input events.json --format sse
```

Do not publish raw graphing payloads directly to the gateway. Render them into standard AG-UI events first. After rendering and validating events, use `houmao-shared-routines->houmao-interop-ag-ui` or maintained gateway guidance for Houmao gateway publishing.

## Templated Graphics

Use `houmao.graphic.template` for supported Plotly.js 2D charts with a curated Houmao envelope.

Required shape:

- `schemaVersion`: `3`
- `figureType`: `"plotly2d"`
- `traces[].type`: one supported Plotly.js 2D trace type from the catalog
- `traces[].data`: inline Plotly-aligned data fields
- `traces[].style`: optional Plotly-aligned style fields accepted by the catalog
- optional `layout`, `config`, `display`, `dataRefs`, and renderer-scoped `extra`

Do not ask the user to choose a Layer 1 renderer. Omit `renderer` or set `"renderer": { "preferred": "plotly" }`. `renderer.fallback` is retired and validation rejects non-Plotly renderer ids.

Prefer inline `traces[].data` arrays when the user needs a visible chart now. Datasource bindings are reserved vocabulary until capabilities explicitly advertise materialization support. You may declare `dataRefs` and trace `source.bindings` only when the target capability says the vocabulary is supported. Binding keys are catalog field paths such as `data.x`, `data.y`, `data.open`, `data.high`, `data.low`, `data.close`, `data.node.label`, `data.link.value`, `data.header.values`, and `data.cells.values`. In the current workbench, datasource-bound traces show a diagnostic instead of a chart.

Use `extra.plotly` only for small allowlisted presentation refinements such as curated `layout`, `config`, `style`, and `display` fields. Do not put raw Plotly `data`, raw `traces`, full replacement specs, frames, transforms, templates, JavaScript, HTML, iframes, SVG, remote URLs, credential-bearing map settings, Vega-Lite, or Vega fields in Layer 1. Do not use true 3D Plotly scene traces such as `scatter3d`, `surface`, or `mesh3d`.

Example:

```json
{
  "schemaVersion": 3,
  "figureType": "plotly2d",
  "renderer": {
    "preferred": "plotly"
  },
  "title": "Build Results",
  "traces": [
    {
      "type": "bar",
      "name": "Jobs",
      "data": {
        "x": ["passed", "failed"],
        "y": [42, 2]
      },
      "style": {
        "marker": { "color": ["#1f7a4d", "#c2410c"] },
        "hovertemplate": "%{x}: %{y}<extra></extra>"
      }
    }
  ],
  "layout": {
    "xaxis": { "title": "Status" },
    "yaxis": { "title": "Count" },
    "bargap": 0.28
  },
  "extra": {
    "plotly": {
      "layout": { "margin": { "l": 48, "r": 16, "t": 48, "b": 44 } }
    }
  }
}
```

## Freeform Graphics

Use `houmao.graphic.vegalite` only when the user needs Vega-Lite grammar or custom declarative structure that does not fit the Layer 1 Plotly.js trace catalog.

Layer 2 payloads use schema version `1` and a strict Houmao envelope:

```json
{
  "schemaVersion": 1,
  "library": "vega-lite",
  "specVersion": "6",
  "title": "Queue Status",
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
  "display": { "height": 360, "caption": "Current queue status." }
}
```

You may hand-author the Vega-Lite JSON `spec`. You may also use Python Altair only as an authoring helper:

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

Send the resulting JSON object under `spec`. Do not send Python source code, Altair objects, pandas objects, notebook state, local file paths, or code that expects the gateway or workbench to execute Python. The gateway and workbench receive declarative JSON only.

## Repair Guidance

- If schema lookup fails, run the layer list command and use the exact implementation name it reports.
- If a Plotly trace type is rejected, inspect `houmao-mgr ag-ui impl catalog houmao.graphic.template traces` and choose a supported 2D trace.
- If `chartType` appears in a payload, rewrite it as schema version `3`, `figureType: "plotly2d"`, and `traces[].type`.
- If a Vega-Lite spec is present inside `houmao.graphic.template.extra`, move it to a `houmao.graphic.vegalite` payload.
- If validation fails, fix the payload and rerun validation before rendering or publishing.

## Guardrails

- DO NOT include credentials, tokens, cookies, private key material, or unredacted auth files in graphing payloads.
- DO NOT include private local file contents unless the user explicitly asks to display that exact content.
- DO NOT use raw unsanitized HTML, scriptable SVG, JavaScript URLs, iframe content, or event-handler attributes.
- DO NOT use raw replacement Plotly `data`, raw `traces`, frames, transforms, templates, JavaScript, HTML, iframes, SVG, remote URLs, credential-bearing map settings, Vega-Lite fields, Vega fields, or true 3D scene traces in templated graphics.
- DO NOT use a non-inline Vega-Lite data source unless a future capability explicitly advertises a safe reference mechanism.
- DO NOT use remote `data.url`, local file URLs, remote images, arbitrary HTTP(S) strings outside the allowed Vega-Lite v6 `$schema` marker, credentials, private local file contents, arbitrary HTML, script tags, iframes, JavaScript URLs, or scriptable SVG in freeform graphics.
