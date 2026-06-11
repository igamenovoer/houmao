# Gateway AG-UI Routes

This page is for operators and GUI authors who want to connect an AG-UI or CopilotKit-style client directly to one live per-agent gateway. These routes belong to the live gateway sidecar for one existing Houmao agent. They do not start, stop, restart, shut down, or own the managed agent.

## Direct Gateway Routes

<!-- BEGIN ag-ui-route-inventory -->
- `GET /v1/ag-ui/capabilities`
- `POST /v1/ag-ui/connect`
- `POST /v1/ag-ui/events`
- `POST /v1/ag-ui/runs`
- `DELETE /v1/ag-ui/connections/{connection_id}`
<!-- END ag-ui-route-inventory -->

`POST /v1/ag-ui/runs` is the task-run endpoint. It accepts AG-UI `RunAgentInput` JSON and returns `text/event-stream` AG-UI frames. `POST /v1/ag-ui/connect` attaches a GUI stream to the existing agent state without submitting work. `POST /v1/ag-ui/events` accepts already-standard AG-UI event batches and fans them out to matching active connect or run streams without creating a Houmao prompt request. `DELETE /v1/ag-ui/connections/{connection_id}` removes only AG-UI connection bookkeeping.

## Minimal Run Request

```bash
curl -N \
  -H 'Content-Type: application/json' \
  -X POST "$GATEWAY_URL/v1/ag-ui/runs" \
  -d '{
    "threadId": "operator-thread",
    "runId": "operator-run-1",
    "state": {},
    "messages": [
      {"id": "message-1", "role": "user", "content": "Summarize the current task."}
    ],
    "tools": [],
    "context": [],
    "forwardedProps": {}
  }'
```

Every admitted run emits `RUN_STARTED` first and then exactly one terminal event, either `RUN_FINISHED` or `RUN_ERROR`. Pre-admission validation, busy-target, and unavailable-target failures remain HTTP errors and do not emit `RUN_STARTED`.

For headless targets, the AG-UI `runId` becomes the gateway prompt `turn_id`. The AG-UI stream loads canonical headless events from `<manifest-stem>.turn-artifacts/<runId>/canonical-events.jsonl`, so deterministic demos can seed that file to test text and graphics mapping without depending on live model tool choice.

## Agent-Published Events

Agents can publish already-rendered AG-UI events to active GUI streams through the live gateway:

```bash
curl \
  -H 'Content-Type: application/json' \
  -X POST "$GATEWAY_URL/v1/ag-ui/events" \
  -d '{
    "threadId": "operator-thread",
    "runId": "operator-run-1",
    "events": [
      {
        "type": "TOOL_CALL_START",
        "toolCallId": "tool-1",
        "toolCallName": "houmao.chart.bar",
        "parentMessageId": "message-1"
      },
      {
        "type": "TOOL_CALL_ARGS",
        "toolCallId": "tool-1",
        "delta": "{\"schemaVersion\":1,\"title\":\"Build Results\",\"data\":[{\"label\":\"Passed\",\"value\":42}]}"
      },
      { "type": "TOOL_CALL_END", "toolCallId": "tool-1" }
    ]
  }'
```

Route metadata must include at least one of `threadId`, `runId`, or `connectionId`. Publishing with `connectionId` targets one GUI connection. Publishing with `threadId`, `runId`, or both fans out to active streams whose route metadata matches. Published GUI events are live-only: the gateway does not store accepted batches for later replay.

The publish response reports:

- `acceptedCount`: events accepted after standard AG-UI validation.
- `storedCount`: always `0` for Houmao gateway GUI-event publish.
- `deliveredCount`: immediate live stream deliveries.
- `replay`: `none`.

`deliveredCount: 0` means no matching live GUI stream received the events. A later GUI connection will not recover that missed batch from the gateway. A GUI that needs durable display history must keep a listener connected for the interested target and cache events client-side.

The publish batch is bounded to 100 events and 256 KiB of encoded JSON. The gateway validates standard AG-UI event shapes, batch limits, route conflicts, and locally checkable tool-call ordering. It does not inspect Houmao component schemas or payload semantics. Generate Houmao typed component events with `houmao-mgr internals ag-ui events render`, and publish them with `houmao-mgr agents self gateway ag-ui publish` or `houmao-mgr agents single ... gateway ag-ui publish`.

## Capability Discovery

```bash
curl "$GATEWAY_URL/v1/ag-ui/capabilities"
```

Capabilities are conservative. The gateway currently reports HTTP SSE streaming, text input, state snapshots, and generated graphics when the backend can expose structured headless artifacts. When generated graphics are enabled, capabilities also include `custom.houmao.presentation.templateGraphics` metadata with the Layer 1 tool name, schema version, supported chart types, renderer ids, default renderer, and `extra` policy. The gateway does not report state deltas, frontend tool execution, Open Generative UI support, or resumable replay for published GUI events.

Capabilities report `transport.resumable: false` and Houmao `replaySupport: "current_snapshot_only"` for published GUI events. `POST /v1/ag-ui/connect` emits a fresh `STATE_SNAPSHOT` and then future live fanout events. Clients should not send browser cache cursors as `lastSeenEventId` expecting the gateway to recover missed published events.

## HttpAgent Setup

The direct AG-UI client points at the per-agent gateway run URL:

```ts
import { HttpAgent } from "@ag-ui/client";

export const houmaoAgent = new HttpAgent({
  url: `${gatewayUrl}/v1/ag-ui/runs`,
});
```

CopilotKit can register an AG-UI `HttpAgent` at its runtime boundary and point the agent URL at the same endpoint. The renderer for Houmao graphics should register `houmao_render_graphic` for compatibility graphics and `houmao.graphic.template` for standardized Layer 1 charts. A minimal renderer example lives at [`docs/reference/gateway/examples/houmao-graphic-renderer.tsx`](examples/houmao-graphic-renderer.tsx).

## Graphics Contract

Houmao streams generated graphics as an assistant-parented AG-UI tool-call sequence named `houmao_render_graphic`. The validated argument payload is:

- `title`
- `description`
- `format`: `svg`, `html_fragment`, `image_url`, `image_data_uri`, or `chart_json`
- `content`
- `contentUrl`
- `altText`
- `metadata`

The AG-UI mapper recognizes graphics only from explicit structured canonical `action_request` or `action_result` events named `houmao_render_graphic`. It does not scrape Markdown image links, prose, or unstructured HTML from assistant text into generated graphics.

## Typed Component Contract

Houmao typed components are application-layer payloads carried inside standard AG-UI tool-call events. The current names are `houmao.graphic.template`, `houmao.chart.bar`, `houmao.chart.line`, `houmao.chart.pie`, `houmao.table`, `houmao.metric_grid`, and `houmao.dashboard`.

Use `houmao-mgr internals ag-ui components list` and `houmao-mgr internals ag-ui components schema <component>` to discover schemas. Use `houmao-mgr internals ag-ui components validate <component> --input payload.json` before rendering. The GUI version owns renderer compatibility for these Houmao component payloads and should show an unknown-component fallback when it receives a component name or schema version it does not understand.

### Layer 1 Template Graphics

`houmao.graphic.template` is the standardized Layer 1 chart object. The agent fills a renderer-neutral JSON payload with `schemaVersion`, `chartType`, `renderer`, `title`, optional `subtitle`, inline `data.values`, `encoding`, optional `interactions`, optional `style`, and optional renderer-scoped `extra`. The initial chart types are `bar`, `line`, `scatter`, `area`, and `pie`.

The `renderer` field is a preference, not a raw backend contract. The GUI tries `renderer.preferred`, then `renderer.fallback`, then its own defaults. The current workbench supports `vega-lite` and `recharts`, and the current default is `vega-lite`. A backend can ignore `extra` blocks it does not understand.

`extra` is only for small backend-specific knobs that do not replace the standardized chart object. For `extra.vega-lite`, Layer 1 allows top-level `axis`, `config`, `height`, `legend`, `mark`, `view`, and `width`. It rejects raw Vega-Lite spec replacement keys such as `data`, `datasets`, `encoding`, `transform`, `layer`, `facet`, `concat`, `params`, `repeat`, and `spec`. This means Layer 1 can use Vega-Lite as a renderer backend, but it is not the raw Vega-Lite DSL. Raw Vega-Lite or Vega specs belong to the planned Layer 2 DSL graphics capability.

Minimal template graphic payload:

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

Agents should generate template graphic events through the authoring helpers:

```bash
houmao-mgr internals ag-ui components validate houmao.graphic.template --input payload.json
houmao-mgr internals ag-ui events render houmao.graphic.template --input payload.json > events.json
```

## Smoke Commands

The deterministic backend E2E runs through pytest:

```bash
pixi run pytest tests/integration/ag_ui/test_gateway_e2e.py -q
```

The live managed-agent text smoke is owned by the existing single-agent headless gateway demo pack. Start a demo-owned headless gateway, run the AG-UI smoke against its live gateway URL, then stop the demo-owned resources:

```bash
scripts/demo/single-agent-gateway-wakeup-headless/run_demo.sh start --tool codex
scripts/demo/single-agent-gateway-wakeup-headless/run_demo.sh ag-ui-smoke
scripts/demo/single-agent-gateway-wakeup-headless/run_demo.sh stop
```

Use `--abort-after-run-start` on `ag-ui-smoke` to verify GUI stream detach behavior. The smoke writes event, request-state, and cleanup evidence under the demo `outputs/evidence/` directory.

The opt-in browser fixture uses the Bun-global Playwright toolchain:

```bash
scripts/demo/ag-ui-browser-smoke/run_smoke.sh
```

This browser smoke uses a deterministic AG-UI graphics stream and verifies visible renderer evidence. It stays outside `pixi run test`.

## Known Limits

- TUI targets stream lower-fidelity status and final text, not headless canonical event detail.
- Frontend tool execution is not implemented; declared AG-UI tools are prompt context, not provider-native tool bindings.
- State deltas remain future work; published GUI events are not replayed by the gateway.
- Multimodal input support is conservative and may reject unsupported content before admission.
- The first graphics smoke is deterministic and fixture-backed because live models are not required to choose `houmao_render_graphic`.
- Closing a GUI stream detaches the AG-UI subscription by default and does not interrupt the underlying Houmao task.

## Passive-Server Readiness

The passive server exposes agent discovery and address resolution for GUI target selection. Use `GET /houmao/agents/{agent_ref}/resolve` to distinguish unknown, ambiguous, known/offline, live-without-gateway, and live-with-gateway states. The GUI should treat `agent_id` or an unambiguous `agent_name` as the durable target and treat gateway host/port as volatile live coordinates.

Stable passive-server AG-UI proxy routes remain future work. The readiness test in `tests/integration/ag_ui/test_passive_server_readiness.py` defines the stream-preservation contract for that future facade: preserve upstream status behavior, `text/event-stream` content type, and AG-UI SSE bytes.
