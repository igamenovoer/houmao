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

Route metadata must include at least one of `threadId`, `runId`, or `connectionId`. Publishing with `connectionId` targets one GUI connection. Publishing with `threadId`, `runId`, or both fans out to active streams whose route metadata matches. The gateway does not replay accepted batches to future streams; the response reports `"replay": "none"` and a `deliveredCount`.

The publish batch is bounded to 100 events and 256 KiB of encoded JSON. The gateway validates standard AG-UI event shapes, batch limits, route conflicts, and locally checkable tool-call ordering. It does not inspect Houmao component schemas or payload semantics. Generate Houmao typed component events with `houmao-mgr internals ag-ui events render`, and publish them with `houmao-mgr agents self gateway ag-ui publish` or `houmao-mgr agents single ... gateway ag-ui publish`.

## Capability Discovery

```bash
curl "$GATEWAY_URL/v1/ag-ui/capabilities"
```

Capabilities are conservative. The gateway currently reports HTTP SSE streaming, text input, state snapshots, and generated graphics when the backend can expose structured headless artifacts. It does not report state deltas, frontend tool execution, or Open Generative UI support.

## HttpAgent Setup

The direct AG-UI client points at the per-agent gateway run URL:

```ts
import { HttpAgent } from "@ag-ui/client";

export const houmaoAgent = new HttpAgent({
  url: `${gatewayUrl}/v1/ag-ui/runs`,
});
```

CopilotKit can register an AG-UI `HttpAgent` at its runtime boundary and point the agent URL at the same endpoint. The renderer for Houmao graphics should register the `houmao_render_graphic` tool name. A minimal renderer example lives at [`docs/reference/gateway/examples/houmao-graphic-renderer.tsx`](examples/houmao-graphic-renderer.tsx).

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

Houmao typed components are application-layer payloads carried inside standard AG-UI tool-call events. The initial names are `houmao.chart.bar`, `houmao.chart.line`, `houmao.chart.pie`, `houmao.table`, `houmao.metric_grid`, and `houmao.dashboard`.

Use `houmao-mgr internals ag-ui components list` and `houmao-mgr internals ag-ui components schema <component>` to discover schemas. Use `houmao-mgr internals ag-ui components validate <component> --input payload.json` before rendering. The GUI version owns renderer compatibility for these Houmao component payloads and should show an unknown-component fallback when it receives a component name or schema version it does not understand.

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
- State deltas and connect replay beyond the current state snapshot remain future work.
- Multimodal input support is conservative and may reject unsupported content before admission.
- The first graphics smoke is deterministic and fixture-backed because live models are not required to choose `houmao_render_graphic`.
- Closing a GUI stream detaches the AG-UI subscription by default and does not interrupt the underlying Houmao task.

## Passive-Server Readiness

Stage 2 will add stable passive-server AG-UI routes. Until then, GUI clients should use the live gateway URL above. The readiness test in `tests/integration/ag_ui/test_passive_server_readiness.py` defines the stream-preservation contract for the future facade: preserve upstream status behavior, `text/event-stream` content type, and AG-UI SSE bytes.
