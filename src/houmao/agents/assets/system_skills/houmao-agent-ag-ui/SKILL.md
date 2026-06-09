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

- Houmao component protocol: `houmao.chart.bar`, `houmao.chart.line`, `houmao.chart.pie`, `houmao.table`, `houmao.metric_grid`, and `houmao.dashboard`.
- Standard AG-UI protocol: the rendered output is an event array such as `TOOL_CALL_START`, `TOOL_CALL_ARGS`, and `TOOL_CALL_END`.
- Houmao gateway publishing: use `houmao-mgr agents ... gateway ag-ui publish`.
- Third-party endpoints: use `houmao-mgr` only to generate or validate events, then deliver the generated event batch with endpoint-specific instructions from that endpoint.

Do not ask the gateway to validate Houmao component semantics. Do not assume that another AG-UI endpoint accepts Houmao gateway route fields, auth, content type, or stream semantics.

## Discover Schemas

List supported components:

```bash
houmao-mgr internals ag-ui components list
```

Show a schema and example:

```bash
houmao-mgr internals ag-ui components schema houmao.chart.bar
```

Use the schema output before crafting a new payload. Do not invent fields.

## Validate and Render

Validate a payload:

```bash
houmao-mgr internals ag-ui components validate houmao.chart.bar --input payload.json
```

Render a valid payload into standard AG-UI events:

```bash
houmao-mgr internals ag-ui events render houmao.chart.bar --input payload.json > events.json
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

## Publish to Houmao Gateway

Publish only to the Houmao gateway through the scoped gateway command family.

Current agent:

```bash
houmao-mgr agents self gateway ag-ui publish --input events.json --thread-id <thread-id>
```

Selected agent:

```bash
houmao-mgr agents single --agent-id <agent-id> gateway ag-ui publish --input events.json --thread-id <thread-id>
houmao-mgr agents single --agent-name <agent-name> gateway ag-ui publish --input events.json --thread-id <thread-id>
```

Use `--run-id` when targeting one run stream, `--connection-id` when targeting one GUI connection, or both `--thread-id` and `--run-id` when the user supplied both. Do not guess routing ids. If no routing id is known, ask for it or inspect the current GUI connection state through maintained gateway surfaces.

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
houmao-mgr agents self gateway ag-ui publish --input events.json --thread-id <thread-id>
```

## Safety

- Do not include credentials, tokens, cookies, private key material, or unredacted auth files in payloads.
- Do not include private local file contents unless the user explicitly asks to display that exact content.
- Do not use raw unsanitized HTML, scriptable SVG, JavaScript URLs, iframe content, or event-handler attributes.
- Prefer typed fields such as labels, numeric values, rows, metrics, and dashboard children.
- If validation fails, fix the payload and rerun validation before rendering or publishing.

## Guardrails

- Do not hand-write AG-UI tool-call event arrays when `events render` can generate them.
- Do not publish raw component payloads directly to the gateway; render them into events first.
- Do not call generic gateway prompt commands to display graphics. AG-UI publish is separate from prompt admission.
- Do not invent third-party endpoint URLs, headers, auth, route ids, or stream formats.
