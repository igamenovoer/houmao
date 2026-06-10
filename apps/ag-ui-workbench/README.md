# Houmao AG-UI Workbench

The AG-UI workbench is a standalone Bun/Vite application for testing Houmao AG-UI protocol behavior against already-running agents. It is intentionally outside the PyPI package and lives under `apps/ag-ui-workbench/`.

## Commands

Run from this directory:

```bash
bun install
bun run dev
bun run typecheck
bun run build
bun run e2e
```

The E2E script uses Playwright from the Bun toolchain through `bunx playwright`.

## Targets

Each pane accepts either a direct gateway base URL or a concrete AG-UI route URL. These examples normalize to the same route family:

```text
http://127.0.0.1:8765
http://127.0.0.1:8765/v1/ag-ui
http://127.0.0.1:8765/v1/ag-ui/runs
http://127.0.0.1:8765/v1/ag-ui/connect
```

Future passive-server agent URLs are also accepted when they already include the agent-scoped AG-UI path:

```text
http://127.0.0.1:8080/houmao/agents/<agent_ref>/ag-ui
http://127.0.0.1:8080/houmao/agents/<agent_ref>/ag-ui/runs
```

Browser requests go through the app-local development proxy at `/__houmao_ag_ui_proxy`. The proxy allows loopback HTTP or HTTPS targets by default and rejects other hosts unless `HOUMAO_AG_UI_WORKBENCH_ALLOWED_HOSTS` lists an exact hostname or host:port value.

## Agent Picker

The toolbar `Agents` control opens a passive-server-backed list of discovered Houmao agents. The passive-server URL defaults to `http://127.0.0.1:9891`, matching the documented `houmao-passive-server serve` default. Click refresh to fetch `GET /houmao/agents`; rows show the discovered agent identity, tool, backend, tmux session, gateway availability, and mailbox availability.

Double-clicking a row from the toolbar opens a new docked agent pane. Opening the picker from a pane's target form defaults to retargeting that pane instead. The picker also exposes Watch, Unwatch, and Open actions. Watch records interest in an agent/thread and starts a background AG-UI connect stream without requiring a visible pane. Open creates a pane for a watched target and renders events that this browser already received.

The picker resolves a selected row through `GET /houmao/agents/<agent_ref>/resolve`. The pane stores the durable agent address (`agentId`, `agentName`, and passive-server URL) and treats the displayed AG-UI URL as the latest resolved gateway coordinate.

If the agent is known but currently has no gateway, the pane can still be targeted. Press Connect to watch it; the watcher enters an offline or waiting state, resolves through the passive server with capped backoff, and attaches when a live gateway appears. If a connected discovered-agent stream ends, the watcher resolves the same agent address again instead of reusing a stale port. Manual AG-UI URL entry remains the direct fallback for low-level tests, third-party endpoints, remote passive servers, SSH-forwarded gateways, and any gateway coordinate that is valid from the passive server host but not directly reachable from the browser. Manual targets do not silently switch into agent-address reconnect mode.

Closing a pane removes only the presentation surface when the target is watched. The background listener keeps running until Unwatch or Disconnect is used. Events published while no watcher is connected are lost for this browser because the Houmao gateway does not retain published GUI events.

For non-loopback passive servers or gateways, set `HOUMAO_AG_UI_WORKBENCH_ALLOWED_HOSTS` to the exact hostname or host:port values before starting the Vite dev server.

Validation flows:

- GUI first: select a known offline agent, press Connect, then start the agent gateway; the pane should move from offline or waiting to connected.
- Agent first: select a live discovered agent; the pane resolves the current gateway URL and connects directly.
- Gateway restart: keep the discovered-agent pane targeted at the same agent; when the stream closes, the pane resolves the current gateway coordinates again and reconnects.
- Manual direct URL: enter the AG-UI URL by hand; the pane uses that exact URL and reports ordinary request errors if the endpoint goes away.

## Debug Agent

The toolbar `Debug Agent` control opens a local protocol playground. It does not create a managed Houmao agent, tmux session, passive-server registry record, gateway sidecar, mailbox, or credential binding. The pane has a white-box sender on the left and a normal AG-UI display on the right. The display connects through the same AG-UI client, SSE parser, reducer, diagnostics, and typed component renderers used by ordinary workbench panes.

The debug relay runs in the Vite host process on the same host and port as the workbench. Its route family is local development/test surface only:

```text
GET    /__houmao_debug_agents/status
GET    /__houmao_debug_agents/<debug_agent_id>/v1/ag-ui/capabilities
POST   /__houmao_debug_agents/<debug_agent_id>/v1/ag-ui/connect
POST   /__houmao_debug_agents/<debug_agent_id>/v1/ag-ui/runs
POST   /__houmao_debug_agents/<debug_agent_id>/v1/ag-ui/events
DELETE /__houmao_debug_agents/<debug_agent_id>/v1/ag-ui/connections/<connection_id>
POST   /__houmao_debug_agents/<debug_agent_id>/components/<component_name>
```

Open a Debug Agent pane first, then copy the visible endpoint or curl command from the sender. A raw AG-UI event batch can be posted from an external shell like this:

```bash
curl -sS -X POST 'http://127.0.0.1:5177/__houmao_debug_agents/debug-agent-1/v1/ag-ui/events' \
  -H 'content-type: application/json' \
  --data '{"threadId":"debug-agent-1-thread","events":[{"type":"TOOL_CALL_START","toolCallId":"bar-1","toolCallName":"houmao.chart.bar","parentMessageId":"debug-message"},{"type":"TOOL_CALL_ARGS","toolCallId":"bar-1","delta":"{\"schemaVersion\":1,\"title\":\"Curl Bar Chart\",\"data\":[{\"label\":\"A\",\"value\":8},{\"label\":\"B\",\"value\":13}]}"},{"type":"TOOL_CALL_END","toolCallId":"bar-1"}]}'
```

The typed component convenience route validates application-layer payloads and wraps them into standard `TOOL_CALL_START`, `TOOL_CALL_ARGS`, and `TOOL_CALL_END` events before publishing:

```bash
curl -sS -X POST 'http://127.0.0.1:5177/__houmao_debug_agents/debug-agent-1/components/houmao.chart.bar' \
  -H 'content-type: application/json' \
  --data '{"threadId":"debug-agent-1-thread","payload":{"schemaVersion":1,"title":"Curl Component Bar","data":[{"label":"North","value":42},{"label":"South","value":28}]}}'
```

Replay is enabled by default for lab-only debug use. If a valid batch is posted before the display connects, the relay stores it in a bounded per-thread buffer and later replays it to the matching display connection. Publish responses identify this as `replay: "debug_thread_buffer"` and report `storedCount`. This intentionally differs from the live gateway. To reproduce gateway-like live-only behavior, turn off the pane replay checkbox or include `"replay": false`; the response reports `replay: "none"`, `storedCount: 0`, and a later display connection will not receive the earlier batch.

Troubleshooting checks:

- `deliveredCount = 0`: no active display stream matched the posted `threadId`, `runId`, or `connectionId`, or the display was disconnected when a live-only batch was posted.
- Display connected but nothing rendered: confirm the event batch contains a complete tool-call sequence and that `TOOL_CALL_ARGS.delta` is a JSON string for a supported Houmao component.
- Validation error: inspect `code`, `detail`, and `path` in the publish response; invalid batches are rejected before delivery.
- Wrong host URL: external callers must reach the workbench host and port. The debug relay is served by Vite; it is not available if the workbench dev server is stopped.
- Unknown component: use one of `houmao.chart.bar`, `houmao.chart.line`, `houmao.chart.pie`, `houmao.table`, `houmao.metric_grid`, or `houmao.dashboard`.

## Lifecycle Boundary

The GUI does not start, stop, restart, shut down, or interrupt Houmao agents. Connect on an agent pane marks the target watched and attaches a background AG-UI stream. Run submits one AG-UI `RunAgentInput`. Disconnect or Unwatch detaches the watched stream. Closing a watched pane does not detach the stream. If a connection ID is known, the workbench calls AG-UI detach; otherwise it only aborts its browser stream.

The workbench persists Dockview layout, passive-server URL, pane labels, target URLs, thread IDs, Debug Agent IDs, Debug Agent replay setting, watched-target metadata, and selected discovered-agent identity metadata in localStorage. It stores received AG-UI stream events for watched targets in an IndexedDB client cache with bounded per-target retention. It does not persist discovered-agent list responses, gateway-status payloads, prompt text, AG-UI request bodies, forwarded props, typed component request bodies, curl-posted event batches, credentials, authorization headers, mailbox content, memory content, or raw terminal content.

## Typed Components

Houmao typed components are application-layer payloads carried over standard AG-UI tool-call events. Agents should generate those events with `houmao-mgr internals ag-ui events render` rather than hand-writing raw AG-UI JSON.

The renderer registry recognizes these Houmao component names:

- `houmao.chart.bar`
- `houmao.chart.line`
- `houmao.chart.pie`
- `houmao.table`
- `houmao.metric_grid`
- `houmao.dashboard`

Charts render through Recharts. Tables, metric grids, and dashboards render as React components with typed payload validation. The compatibility `houmao_render_graphic` path remains available for sanitized SVG graphics. Unknown Houmao component names and invalid payloads render explicit fallback records, and the raw tool-call arguments remain visible in diagnostics. Typed component renderers do not inject raw HTML or raw SVG.

## Live Kimi Code Headless Check

For live/manual validation of this change, use a Kimi Code headless Houmao agent through an already-running per-agent gateway. When fixture credentials are present, prefer `tests/fixtures/auth-bundles/kimi/personal-a-default/`.

Start or discover the Kimi headless agent with the existing Houmao workflow, then point an operator or agent pane at the gateway URL, for example `http://127.0.0.1:<gateway_port>/v1/ag-ui`. The workbench should attach through AG-UI connect or submit one run through AG-UI runs without managing the Kimi headless process lifecycle.

The deterministic Playwright fake-server smoke remains the required automated test path. The Kimi Code headless run is opt-in evidence for local real-agent validation.

## Known Limits

The first workbench version is a protocol harness, not an operator scheduler. It does not execute frontend tools, send multimodal input, manage credentials, export event logs, or use CopilotKit as its runtime path. Houmao typed components and generated graphics render through complete AG-UI tool-call sequences, with unsupported or invalid payloads shown as explicit fallback records.
