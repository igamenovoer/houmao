## 1. Workbench Model and Shared Display

- [x] 1.1 Extend workbench pane/storage models to support a `debug-agent` pane kind with debug-agent ID, target URL, thread ID, replay setting, and safe persistence.
- [x] 1.2 Extract the reusable AG-UI display behavior from `AgentSessionPanel` so a debug pane can use the same client, SSE parsing, reducer, transcript, diagnostics, and typed component renderer path without duplicating logic.
- [x] 1.3 Preserve existing operator and agent pane behavior after the shared display extraction.
- [x] 1.4 Add sanitization so unknown or stale debug-pane records do not restore stream payloads, raw events, transcripts, rendered graphics, credentials, or request bodies from local storage.

## 2. Debug Relay Host Routes

- [x] 2.1 Add a Vite dev-server middleware for `/__houmao_debug_agents` alongside the existing workbench AG-UI proxy.
- [x] 2.2 Implement `GET /__houmao_debug_agents/status` with route and feature metadata for the Debug Agent UI and docs.
- [x] 2.3 Implement per-debug-agent `GET /v1/ag-ui/capabilities`, `POST /v1/ag-ui/connect`, `POST /v1/ag-ui/runs`, and `DELETE /v1/ag-ui/connections/{connection_id}` routes.
- [x] 2.4 Implement in-memory subscription management scoped by debug-agent ID, thread ID, run ID, and connection ID.
- [x] 2.5 Implement `POST /v1/ag-ui/events` for already-standard AG-UI event batches with event count limits, payload size limits, sequence validation, delivery counts, and deterministic validation errors.
- [x] 2.6 Implement bounded per-thread replay buffers and a live-only option that returns `replay: "none"` and does not deliver earlier batches to future connections.
- [x] 2.7 Ensure relay detach and browser abort cleanup release only debug connection bookkeeping and do not touch Houmao managed-agent lifecycle state.

## 3. Component Convenience Publishing

- [x] 3.1 Define the typed component send contract for `POST /__houmao_debug_agents/{agent_id}/components/{component_name}`.
- [x] 3.2 Implement wrapping of valid typed component payloads into standard `TOOL_CALL_START`, `TOOL_CALL_ARGS`, and `TOOL_CALL_END` events before publishing.
- [x] 3.3 Surface deterministic validation failures for invalid typed component payloads without publishing a successful component sequence.
- [x] 3.4 Provide example payload templates for at least `houmao.chart.bar`, `houmao.table`, and `houmao.dashboard`.

## 4. Debug Agent Pane UI

- [x] 4.1 Add a toolbar control to open a docked Debug Agent pane without creating a managed agent, gateway, tmux session, passive-server record, mailbox, or credential binding.
- [x] 4.2 Implement the composite Debug Agent pane layout with a white-box sender side and an AG-UI display side.
- [x] 4.3 Auto-configure the display side to the debug relay target URL and debug thread ID for that pane.
- [x] 4.4 Add sender controls for raw AG-UI event batches, typed component payloads, validate, send to display, copy curl, clear display, and replay/live-only selection.
- [x] 4.5 Show the most recent publish response including accepted count, delivered count, stored count when applicable, replay mode, thread ID, run ID, and connection ID.
- [x] 4.6 Ensure the right-side display shows transcript messages, typed graphics, diagnostics, raw events, and state snapshots through the normal AG-UI display path.
- [x] 4.7 Make endpoint and curl examples visible enough for operators to copy but do not persist posted payload contents by default.

## 5. Documentation

- [x] 5.1 Update `apps/ag-ui-workbench/README.md` to describe Debug Agent purpose, host-side relay process, route family, local-only boundary, replay behavior, and non-managed-agent lifecycle limits.
- [x] 5.2 Document curl examples for posting raw AG-UI event batches and typed component payloads to the debug relay.
- [x] 5.3 Document how Debug Agent replay differs from live gateway `replay: "none"` semantics and how to switch to live-only mode.
- [x] 5.4 Add troubleshooting notes for `deliveredCount = 0`, display not connected, wrong thread ID, invalid event sequences, and disallowed or unavailable workbench host URLs.

## 6. Tests and Evidence

- [x] 6.1 Add unit or focused integration coverage for debug relay route validation, subscription matching, live delivery counts, replay buffer delivery, live-only no-replay behavior, and detach cleanup.
- [x] 6.2 Add Playwright coverage that opens a Debug Agent pane, connects the display, posts a `houmao.chart.bar` event batch through the externally reachable events route, and verifies `deliveredCount > 0`.
- [x] 6.3 Extend Playwright coverage to verify visible graphical rendering through an SVG chart and rendered bar elements.
- [x] 6.4 Add Playwright coverage for curl-before-connect replay and live-only no-replay behavior.
- [x] 6.5 Verify that local storage does not contain posted event batches, raw stream events, typed component payloads, transcripts, rendered graphics, credentials, or authorization headers after debug sends.
- [x] 6.6 Capture or expose screenshot evidence for the rendered debug chart in the deterministic browser proof path.

## 7. Verification

- [x] 7.1 Run the workbench TypeScript typecheck.
- [x] 7.2 Run the workbench production build.
- [x] 7.3 Run the deterministic workbench Playwright E2E suite.
- [x] 7.4 Run focused Python tests if shared AG-UI validation helpers or CLI documentation are touched.
- [x] 7.5 Run `openspec validate add-ag-ui-debug-agent-pane --strict`.
