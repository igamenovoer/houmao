---
name: houmao-agent-ag-ui
description: Use Houmao AG-UI authoring helpers to discover component schemas, validate payloads, render standard AG-UI events, and publish them to the Houmao gateway.
license: MIT
---

# Houmao Agent AG-UI

Use this skill when a Houmao agent needs to send typed visual output to an AG-UI GUI through maintained Houmao tooling.

Typed Houmao components are an application-layer protocol carried inside standard AG-UI tool-call events. The gateway validates standard AG-UI event shape and routing only. `houmao-mgr` owns Houmao component schemas, payload validation, and event generation.

## Help

When the user asks `$houmao-agent-ag-ui help`, `help for houmao-agent-ag-ui`, or what this skill can do, answer from this section and stop unless they also ask for a concrete AG-UI action. This is read-only help: do not run commands, mutate files, send mail, change gateway state, or alter managed-agent lifecycle state during help. If the user asks a concrete task such as "help me send a chart to the GUI", route to the matching workflow instead of stopping at generic help.

Purpose: create visual AG-UI messages without hand-writing raw event JSON.

Available functionality:

- List Houmao AG-UI component schemas.
- Show one component schema and example.
- Validate a component payload.
- Render a valid payload into standard AG-UI events.
- Validate already-rendered standard AG-UI event batches.
- Publish a rendered batch to the live Houmao gateway for the current or selected agent.

Common starting prompts:

- `$houmao-agent-ag-ui help`
- `$houmao-agent-ag-ui list components`
- `$houmao-agent-ag-ui render a bar chart`
- `$houmao-agent-ag-ui publish these events to my GUI`

Related skills and boundaries:

- Use `houmao-agent-gateway` for gateway lifecycle, attachment, status, reminders, and direct gateway controls.
- Use `houmao-agent-messaging` for prompts, interrupts, and live managed-agent communication.
- Use this skill only for AG-UI component/event authoring and AG-UI publish workflows.
- Do not use this skill to submit ordinary prompt work.

## Launcher

Choose one `houmao-mgr` launcher for the turn:

1. Run `command -v houmao-mgr` and use the command on `PATH` when present.
2. If that fails, use `uv tool run --from houmao houmao-mgr`.
3. For repo development only, use the project launcher such as `pixi run houmao-mgr`.
4. If the user names a launcher, use that launcher.

Reuse the same launcher for discovery, validation, rendering, and publishing in the same turn.

## Protocol Split

- Houmao component protocol: `houmao.graphic.template`, `houmao.chart.bar`, `houmao.chart.line`, `houmao.chart.pie`, `houmao.table`, `houmao.metric_grid`, and `houmao.dashboard`.
- Standard AG-UI protocol: the rendered output is an event array such as `TOOL_CALL_START`, `TOOL_CALL_ARGS`, and `TOOL_CALL_END`.
- Houmao gateway publishing: use `houmao-mgr agents ... gateway ag-ui publish`.
- Third-party endpoints: use `houmao-mgr` only to generate or validate events, then deliver the generated event batch with endpoint-specific instructions from that endpoint.

Do not ask the gateway to validate Houmao component semantics. Do not assume that another AG-UI endpoint accepts Houmao gateway route fields, auth, content type, or stream semantics.

Agent identity is the durable address. A gateway host and port are live transport coordinates that can disappear or change when the agent or gateway restarts. The Houmao workbench stores the selected `agent_id` or unambiguous `agent_name`, resolves the current gateway through the passive server, and reconnects when a matching gateway appears. Do not tell a user that a copied gateway URL is the stable identity of an agent.

The Houmao gateway publishes GUI events as live-only fanout. It does not store missed published events for later replay. The workbench can keep graphics visible only when it was already watching the target and cached the events in the browser.

## Discover Schemas

List supported components:

```bash
houmao-mgr internals ag-ui components list
```

Show a schema and example:

```bash
houmao-mgr internals ag-ui components schema houmao.chart.bar
houmao-mgr internals ag-ui components schema houmao.graphic.template
```

Use the schema output before crafting a new payload. Do not invent fields.

## Validate and Render

Validate a payload:

```bash
houmao-mgr internals ag-ui components validate houmao.chart.bar --input payload.json
houmao-mgr internals ag-ui components validate houmao.graphic.template --input payload.json
```

Render a valid payload into standard AG-UI events:

```bash
houmao-mgr internals ag-ui events render houmao.chart.bar --input payload.json > events.json
houmao-mgr internals ag-ui events render houmao.graphic.template --input payload.json > events.json
```

Validate a rendered event batch:

```bash
houmao-mgr internals ag-ui events validate --input events.json
```

Supported render formats:

```bash
houmao-mgr internals ag-ui events render houmao.chart.bar --input payload.json --format json
houmao-mgr internals ag-ui events render houmao.chart.bar --input payload.json --format jsonl
houmao-mgr internals ag-ui events render houmao.chart.bar --input payload.json --format sse
```

## Layer 1 Template Graphics

Prefer `houmao.graphic.template` for ordinary charts when you need renderer choice, Vega-Lite rendering, or a forward-compatible standardized chart object. Use the older `houmao.chart.bar`, `houmao.chart.line`, and `houmao.chart.pie` payloads only for simple compatibility charts.

Layer 1 template graphics are not raw Vega-Lite specs. Fill the standardized fields: `schemaVersion`, `chartType`, `renderer`, `title`, optional `subtitle`, inline `data.values`, `encoding`, optional `interactions`, optional `style`, and optional renderer-scoped `extra`. Supported chart types are `bar`, `line`, `scatter`, `area`, and `pie`.

The `renderer` field expresses preference. Use `"preferred": "vega-lite"` when Vega-Lite output is desired and include `"fallback": ["recharts"]` so a GUI with only Recharts can still display the chart.

Use `extra` only for small backend-specific knobs. For `extra.vega-lite`, allowed top-level keys are `axis`, `config`, `height`, `legend`, `mark`, `view`, and `width`. Do not put raw Vega-Lite keys such as `data`, `datasets`, `encoding`, `transform`, `layer`, `facet`, `concat`, `params`, `repeat`, or `spec` in Layer 1. If the user needs a custom Vega-Lite/Vega spec, that belongs to the planned Layer 2 DSL graphics capability, not this component.

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

This command intentionally has no `--endpoint` option. For third-party endpoints, generate the event batch with `internals ag-ui events render`, validate it, then use that endpoint's documented delivery method.

## Examples

Bar chart payload:

```json
{
  "schemaVersion": 1,
  "title": "Build Results",
  "xLabel": "Status",
  "yLabel": "Count",
  "data": [
    { "label": "Passed", "value": 42 },
    { "label": "Failed", "value": 2 }
  ]
}
```

Template graphic payload:

```json
{
  "schemaVersion": 1,
  "chartType": "bar",
  "renderer": {
    "preferred": "vega-lite",
    "fallback": ["recharts"]
  },
  "title": "Build Results",
  "data": {
    "values": [
      { "status": "passed", "count": 42 },
      { "status": "failed", "count": 2 }
    ]
  },
  "encoding": {
    "x": { "field": "status", "type": "nominal", "title": "Status" },
    "y": { "field": "count", "type": "quantitative", "title": "Count" },
    "tooltip": true
  },
  "interactions": { "tooltip": true, "legend": true },
  "extra": {
    "vega-lite": {
      "config": { "axis": { "labelFontSize": 12 } }
    }
  }
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
houmao-mgr internals ag-ui components validate houmao.table --input payload.json
houmao-mgr internals ag-ui events render houmao.table --input payload.json > events.json
houmao-mgr agents self gateway ag-ui publish --input events.json
```

After publishing, report the response accurately. If `delivered_count > 0`, say the gateway delivered the batch to live stream subscribers. If the response includes `default_sink_due_to_no_destination`, say that no GUI destination was available and the gateway used the internal sink. If `delivered_count` is zero without that warning, say only that the gateway accepted the batch and no live GUI stream received it.

## Safety

- Do not include credentials, tokens, cookies, private key material, or unredacted auth files in payloads.
- Do not include private local file contents unless the user explicitly asks to display that exact content.
- Do not use raw unsanitized HTML, scriptable SVG, JavaScript URLs, iframe content, or event-handler attributes.
- Prefer typed fields such as labels, numeric values, rows, metrics, and dashboard children.
- Prefer `houmao.graphic.template` for ordinary charts that can be described as standardized chart type, data, and encoding.
- If validation fails, fix the payload and rerun validation before rendering or publishing.

## Guardrails

- Do not hand-write AG-UI tool-call event arrays when `events render` can generate them.
- Do not publish raw component payloads directly to the gateway; render them into events first.
- Do not embed full Vega-Lite or Vega DSL specs inside `houmao.graphic.template`; use only the standardized Layer 1 schema and allowed `extra` fields.
- Do not call generic gateway prompt commands to display graphics. AG-UI publish is separate from prompt admission.
- Do not invent third-party endpoint URLs, headers, auth, route ids, or stream formats.
