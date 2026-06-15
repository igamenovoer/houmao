---
name: houmao-interop-ag-ui
description: "Use Houmao AG-UI interop helpers for typed visual output: discover implementation schemas, validate payloads, render standard AG-UI event batches, and publish them through a live Houmao gateway. Use when Codex needs to create, validate, render, or deliver Houmao AG-UI graphics, tables, metric grids, dashboards, or other typed GUI messages."
---

# Houmao Interop AG-UI

Use maintained Houmao tooling to send typed visual output to an AG-UI GUI.

Typed Houmao implementations are application-layer contracts carried inside standard AG-UI tool-call events. The gateway validates standard AG-UI event shape and routing only. `houmao-mgr ag-ui protocol` owns schema-agnostic AG-UI event validation and framing. `houmao-mgr ag-ui impl` owns Houmao implementation schemas, payload validation, and event generation.

## Help

When the user asks `$houmao-interop-ag-ui help`, `help for houmao-interop-ag-ui`, or what this skill can do, answer from this section and stop unless they also ask for a concrete AG-UI action. This is read-only help: do not run commands, mutate files, send mail, change gateway state, or alter managed-agent lifecycle state during help. If the user asks a concrete task such as "help me send a chart to the GUI", route to the matching workflow instead of stopping at generic help.

Purpose: create visual AG-UI messages without hand-writing raw event JSON.

Available functionality:

- List Houmao AG-UI implementation schemas.
- List graphics schemas by `templated-graphics`, `freeform-graphics`, and `new-component` layer.
- Show one implementation schema and example.
- Validate an implementation payload.
- Render a valid payload into standard AG-UI events.
- Render a schema-agnostic custom tool call for a frontend-specific component.
- Validate already-rendered standard AG-UI event batches.
- Publish a rendered batch to the live Houmao gateway for the current or selected agent.

Common starting prompts:

- `$houmao-interop-ag-ui help`
- `$houmao-interop-ag-ui list implementation schemas`
- `$houmao-interop-ag-ui render a bar chart`
- `$houmao-interop-ag-ui publish these events to my GUI`

Related skills and boundaries:

- Use `houmao-agent-gateway` for gateway lifecycle, attachment, status, reminders, and direct gateway controls.
- Use `houmao-agent-messaging` for prompts, interrupts, and live managed-agent communication.
- Use this skill only for AG-UI implementation/event authoring and AG-UI publish workflows.
- Do not use this skill to submit ordinary prompt work.

## Launcher

Choose one `houmao-mgr` launcher for the turn:

1. Run `command -v houmao-mgr` and use the command on `PATH` when present.
2. If that fails, use `uv tool run --from houmao houmao-mgr`.
3. For repo development only, use the project launcher such as `pixi run houmao-mgr`.
4. If the user names a launcher, use that launcher.

Reuse the same launcher for discovery, validation, rendering, and publishing in the same turn.

## Protocol and Implementation Split

- Standard AG-UI protocol: standard event arrays such as `TOOL_CALL_START`, `TOOL_CALL_ARGS`, and `TOOL_CALL_END`. Use `houmao-mgr ag-ui protocol ...` for schema-agnostic validation, framing, and generic tool-call rendering.
- Houmao AG-UI impl: Houmao-owned implementation contracts such as `houmao.graphic.template`, `houmao.graphic.vegalite`, `houmao.table`, `houmao.metric_grid`, and `houmao.dashboard`. Use `houmao-mgr ag-ui impl ...` for schema discovery, validation, rendering, and catalogs.
- Graphics categories: `templated-graphics` currently contains the Plotly-backed `houmao.graphic.template` schema; `freeform-graphics` currently contains the Vega-Lite `houmao.graphic.vegalite` schema; `new-component` covers table, metric grid, dashboard, and frontend-specific custom tool calls.
- Houmao gateway publishing: use `houmao-mgr agents ... gateway ag-ui publish`.
- Third-party endpoints: use `houmao-mgr` only to generate or validate events, then deliver the generated event batch with endpoint-specific instructions from that endpoint.

Do not ask the gateway to validate Houmao implementation semantics. Protocol validation only means the event shape is standard AG-UI; it does not prove a GUI can render a custom implementation payload. Do not assume that another AG-UI endpoint accepts Houmao gateway route fields, auth, content type, or stream semantics.

Agent identity is the durable address. A gateway host and port are live transport coordinates that can disappear or change when the agent or gateway restarts. The Houmao workbench stores the selected `agent_id` or unambiguous `agent_name`, resolves the current gateway through the passive server, and reconnects when a matching gateway appears. Do not tell a user that a copied gateway URL is the stable identity of an agent.

The Houmao gateway publishes GUI events as live-only fanout. It does not store missed published events for later replay. The workbench can keep graphics visible only when it was already watching the target and cached the events in the browser.

## Discover Schemas

List supported Houmao implementations:

```bash
houmao-mgr ag-ui impl list
```

Show a schema and example:

```bash
houmao-mgr ag-ui impl schema houmao.graphic.template
houmao-mgr ag-ui impl schema houmao.graphic.vegalite
```

List graphics implementation categories:

```bash
houmao-mgr ag-ui impl templated-graphics list
houmao-mgr ag-ui impl freeform-graphics list
```

List supported and excluded Plotly template trace types:

```bash
houmao-mgr ag-ui impl catalog houmao.graphic.template traces
```

Use the schema output before crafting a new payload. Do not invent fields.

## Validate and Render

Validate a payload:

```bash
houmao-mgr ag-ui impl validate houmao.graphic.template --input payload.json
```

Render a valid payload into standard AG-UI events:

```bash
houmao-mgr ag-ui impl render houmao.graphic.template --input payload.json > events.json
```

Validate a rendered event batch:

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

Render a frontend-specific tool call when the user has supplied the GUI-side implementation contract:

```bash
houmao-mgr ag-ui impl new-component render --tool-name myapp.graphic.timeline --args payload.json > events.json
```

## Layer 1 Template Graphics

Use `houmao.graphic.template` for ordinary charts. The legacy fixed chart components are retired; do not generate `houmao.chart.bar`, `houmao.chart.line`, or `houmao.chart.pie`.

Layer 1 template graphics use schema version `3`, `figureType: "plotly2d"`, and a Plotly-backed curated schema selected through `traces[].type`. Fill standardized fields such as `schemaVersion`, `figureType`, `title`, optional `subtitle`, `traces`, optional `layout`, optional `config`, optional `display`, optional `dataRefs`, and optional renderer-scoped `extra`. Supported trace types come from the template graphics schema and AG-UI capabilities; inspect those before authoring uncommon Plotly families. Prefer `houmao.graphic.template` for supported Plotly 2D charts such as heatmaps, box and violin plots, polar charts, financial charts, treemaps, tables, and Sankey diagrams.

Do not ask the user to choose a Layer 1 renderer. Omit `renderer` or set `"renderer": { "preferred": "plotly" }`. `renderer.fallback` is retired and validation rejects non-Plotly renderer ids.

Datasource bindings are reserved vocabulary until capabilities explicitly advertise materialization support. You may declare `dataRefs` and trace `source.bindings` entries only when the target capability says the vocabulary is supported. Binding keys are catalog field paths such as `data.x`, `data.y`, `data.open`, `data.high`, `data.low`, `data.close`, `data.node.label`, `data.link.value`, `data.header.values`, and `data.cells.values`. In the current workbench, materialization is unsupported, so datasource-bound traces show a diagnostic instead of a chart. Prefer inline `traces[].data` arrays when the user needs a visible chart now.

Use `traces[].data` for Plotly-aligned data fields and `traces[].style` for Plotly-aligned style fields accepted by the catalog. Use `extra.plotly` only for small allowlisted presentation refinements such as curated `layout`, `config`, `style`, and `display` fields. Do not put raw Plotly `data`, raw `traces`, full replacement specs, frames, transforms, templates, JavaScript, HTML, iframes, SVG, remote URLs, credential-bearing map settings, Vega-Lite, or Vega fields in Layer 1. Do not use true 3D Plotly scene traces such as `scatter3d`, `surface`, or `mesh3d`.

## Layer 2 Vega-Lite Graphics

Use `houmao.graphic.vegalite` only when the user needs Vega-Lite grammar or custom declarative structure that does not fit the Layer 1 Plotly 2D trace catalog, such as layering, custom encodings, transforms, selections, or linked views. For ordinary supported Plotly 2D charts with inline data, keep using `houmao.graphic.template`.

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

Validate and render Layer 2 payloads before publishing:

```bash
houmao-mgr ag-ui impl validate houmao.graphic.vegalite --input payload.json
houmao-mgr ag-ui impl render houmao.graphic.vegalite --input payload.json > events.json
```

Layer 2 safety limits:

- Use inline `data.values` unless a future capability explicitly advertises a safe reference mechanism.
- Do not use remote `data.url`, local file URLs, remote images, arbitrary HTTP(S) strings outside the allowed Vega-Lite v6 `$schema` marker, credentials, private local file contents, arbitrary HTML, script tags, iframes, JavaScript URLs, or scriptable SVG.
- Do not put a raw Vega-Lite spec inside `houmao.graphic.template.extra`; use `houmao.graphic.vegalite`.

## Publish to Houmao Gateway

Publish only to the Houmao gateway through the scoped gateway command family.

Current agent:

```bash
houmao-mgr agents self gateway ag-ui publish --input events.json
```

Selected agent:

```bash
houmao-mgr agents single --agent-id <agent-id> gateway ag-ui publish --input events.json
houmao-mgr agents single --agent-name <agent-name> gateway ag-ui publish --input events.json
```

For the Houmao AG-UI workbench, a tmux-controlled agent often lacks GUI-appended canvas or thread context. In that case, omit explicit routing and let the gateway resolve the destination. The gateway order is:

1. Destination specified in the publish request or rendered event batch.
2. Gateway `active-thread`, set by the workbench active-thread control or by an eligible pane connect action.
3. Houmao default sink.

The default sink is gateway-defined and is not an agent-visible thread name. Do not invent or target a sink thread id.

Gateway `last-sent-thread` is bookkeeping only. It records the last concrete non-sink publish destination, but the gateway does not use it as fallback routing when a later publish omits routing.

Use `--thread-id <thread-id>` by itself when the user or environment gives a known destination thread. A pane-level connect stream and an active run stream both receive thread-only publishes for the same thread. Adding `--run-id` narrows delivery to a stream with that exact run id, so a guessed, newly generated, stale, or copied-but-wrong run id will usually produce `delivered_count: 0` and the GUI will render nothing.

Use `--run-id` only when targeting one known active run stream. Use `--connection-id` only when targeting one known active GUI connection. Do not guess routing ids. If no routing id is known, ask for it or inspect the current GUI connection state through maintained gateway surfaces.

Check the publish response:

- `accepted_count` is the number of standard AG-UI events accepted by the gateway after validation.
- `stored_count` is normally `0` for Houmao gateway GUI-event publish because the gateway does not retain missed events for replay.
- `delivered_count` is the number of live stream deliveries made immediately.
- `warnings` may include `default_sink_due_to_no_destination` when the gateway accepted the batch but had no message-specified or active-thread destination.

`delivered_count > 0` means matching live GUI/run streams received the events immediately. `delivered_count: 0` with `stored_count: 0` means no matching live stream received the events and the Houmao gateway did not retain them for later replay. Do not describe a publish as visible in the GUI unless `delivered_count > 0` or the user confirms that the GUI received it through another path.

If the response warns `default_sink_due_to_no_destination`, report that the gateway accepted the events but sent them to the internal default sink because no GUI destination was available. Do not claim that the GUI displayed the message.

If the user expected a chart to appear but `delivered_count` is zero, ask the user to open or watch the intended workbench target, mark the pane active when relying on omitted routing, and publish the event batch again after a listener is connected.

This command intentionally has no `--endpoint` option. For third-party endpoints, generate the event batch with `ag-ui impl render` or `ag-ui protocol tool-call render`, validate it, then use that endpoint's documented delivery method.

## Examples

Template graphic payload:

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

Datasource-bound template graphic payload:

```json
{
  "schemaVersion": 3,
  "figureType": "plotly2d",
  "title": "Build Results",
  "dataRefs": [
    {
      "id": "buildRows",
      "columns": [
        { "name": "status", "type": "string" },
        { "name": "count", "type": "number" }
      ]
    }
  ],
  "traces": [
    {
      "type": "bar",
      "source": {
        "dataRef": "buildRows",
        "bindings": {
          "data.x": { "column": "status" },
          "data.y": { "column": "count" }
        }
      }
    }
  ]
}
```

Table payload:

```json
{
  "schemaVersion": 1,
  "title": "Top Issues",
  "columns": [
    { "key": "id", "label": "ID" },
    { "key": "count", "label": "Count", "kind": "number", "align": "right" }
  ],
  "rows": [
    { "id": "A", "count": 4 },
    { "id": "B", "count": 2 }
  ]
}
```

Render and publish:

```bash
houmao-mgr ag-ui impl validate houmao.table --input payload.json
houmao-mgr ag-ui impl render houmao.table --input payload.json > events.json
houmao-mgr agents self gateway ag-ui publish --input events.json
```

After publishing, report the response accurately. If `delivered_count > 0`, say the gateway delivered the batch to live stream subscribers. If the response includes `default_sink_due_to_no_destination`, say that no GUI destination was available and the gateway used the internal sink. If `delivered_count` is zero without that warning, say only that the gateway accepted the batch and no live GUI stream received it.

## Safety

- Do not include credentials, tokens, cookies, private key material, or unredacted auth files in payloads.
- Do not include private local file contents unless the user explicitly asks to display that exact content.
- Do not use raw unsanitized HTML, scriptable SVG, JavaScript URLs, iframe content, or event-handler attributes.
- Prefer typed fields such as labels, numeric values, rows, metrics, and dashboard children.
- Prefer `houmao.graphic.template` for ordinary charts that can be described as a supported Plotly 2D trace type with inline traces.
- If validation fails, fix the payload and rerun validation before rendering or publishing.

## Guardrails

- Do not hand-write AG-UI tool-call event arrays when `ag-ui impl render` or `ag-ui protocol tool-call render` can generate them.
- Do not publish raw implementation payloads directly to the gateway; render them into events first.
- Do not embed raw Plotly, Vega-Lite, Vega, HTML, or JavaScript specs inside `houmao.graphic.template`; use only the standardized Layer 1 schema and allowed `extra.plotly` fields.
- Do not call generic gateway prompt commands to display graphics. AG-UI publish is separate from prompt admission.
- Do not invent third-party endpoint URLs, headers, auth, route ids, or stream formats.
