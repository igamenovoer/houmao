## 1. Shared AG-UI Authoring Models

- [x] 1.1 Add a `houmao.ag_ui.authoring` module with Pydantic models for the initial Houmao component set: `houmao.chart.bar`, `houmao.chart.line`, `houmao.chart.pie`, `houmao.table`, `houmao.metric_grid`, and `houmao.dashboard`.
- [x] 1.2 Add component registry helpers that list components, return JSON Schema-compatible metadata, return valid examples, and validate payloads by component name.
- [x] 1.3 Add event-generation helpers that turn one validated component payload into a standard AG-UI tool-call event sequence with deterministic message and tool-call IDs.
- [x] 1.4 Add standard AG-UI event-sequence validation helpers for known event shapes, bounded batch size, and locally checkable tool-call ordering.
- [x] 1.5 Add unit tests for component schema discovery, valid examples, invalid payload diagnostics, unsafe content rejection, event rendering, and event-sequence validation.

## 2. `houmao-mgr` Authoring CLI

- [x] 2.1 Add `houmao-mgr internals ag-ui components list` and `components schema <component>` commands with JSON/plain output support.
- [x] 2.2 Add `houmao-mgr internals ag-ui components validate <component> --input <path-or->` with field-path diagnostics and safe secret-like value redaction.
- [x] 2.3 Add `houmao-mgr internals ag-ui events render <component> --input <path-or-> --format json|jsonl|sse` using the shared event-generation helpers.
- [x] 2.4 Add `houmao-mgr internals ag-ui events validate --input <path-or->` for already-rendered AG-UI event batches.
- [x] 2.5 Add a Houmao-gateway-specific AG-UI publish helper under the maintained gateway command family that validates events before posting to the Houmao gateway ingestion route and does not accept arbitrary third-party endpoint options.
- [x] 2.6 Add CLI unit tests covering stdin/path input, success output, invalid JSON, invalid component names, invalid payloads, invalid event batches, Houmao-gateway publish preflight rejection, and third-party endpoint rejection or non-support messaging.

## 3. Gateway AG-UI Event Ingestion

- [x] 3.1 Add request/response models for a bounded AG-UI event publish batch under the existing AG-UI gateway model boundary.
- [x] 3.2 Add `POST /v1/ag-ui/events` or the final chosen ingestion route to the per-agent gateway AG-UI route registration.
- [x] 3.3 Validate submitted events against AG-UI core event shapes, batch limits, routing metadata, and locally checkable ordering without inspecting Houmao component schemas.
- [x] 3.4 Add in-memory stream fanout from accepted event batches to matching active connect/run streams while keeping published events separate from Houmao prompt admission.
- [x] 3.5 Add bounded replay bookkeeping or explicit no-replay behavior matching the finalized route contract.
- [x] 3.6 Add safe diagnostics for accepted, rejected, delivered, oversized, and no-subscriber publish outcomes without logging full payloads.
- [x] 3.7 Add gateway unit and route tests for valid publish, malformed event rejection, opaque `houmao.chart.bar` payload acceptance, no prompt creation, stream delivery, no-subscriber behavior, and diagnostics redaction.

## 4. Workbench Renderer Registry

- [x] 4.1 Refactor the workbench tool/custom event reducer output so complete AG-UI tool calls can be passed to a renderer registry by name.
- [x] 4.2 Add TypeScript payload validators for the initial Houmao component set and invalid-component fallback state.
- [x] 4.3 Add chart rendering for bar, line, and pie components using a maintained charting dependency such as Recharts.
- [x] 4.4 Add table, metric-grid, and dashboard renderers with stable responsive layout and no raw HTML/SVG injection.
- [x] 4.5 Move the existing `houmao_render_graphic` SVG rendering path into the registry or a compatibility adapter.
- [x] 4.6 Add deterministic fixture events for known components, invalid components, and unknown components.
- [x] 4.7 Add workbench typecheck/build and Playwright coverage for visible chart/dashboard output, invalid fallback output, unknown component raw-event visibility, and continued stream processing.

## 5. Packaged Agent Skill

- [x] 5.1 Add `src/houmao/agents/assets/system_skills/houmao-agent-ag-ui/SKILL.md` with protocol split guidance, launcher resolution, schema discovery, validation, rendering, and publishing workflow.
- [x] 5.2 Add chart and table examples that call the new `houmao-mgr internals ag-ui` commands and avoid unvalidated raw AG-UI JSON.
- [x] 5.3 Add endpoint-selection guidance that supports Houmao gateway publishing while telling agents to use generated events and endpoint-specific delivery for third-party endpoints without guessing host, port, thread id, or run id.
- [x] 5.4 Add safety guidance prohibiting raw unsanitized HTML, scriptable SVG, JavaScript URLs, credential material, and private local file contents in GUI payloads.
- [x] 5.5 Register the skill in the maintained system-skill catalog and add tests that verify catalog visibility and packaged file installation.

## 6. Documentation and Verification

- [x] 6.1 Update AG-UI workbench README or docs to describe Houmao typed components as application-layer renderers carried over standard AG-UI events.
- [x] 6.2 Update gateway or AG-UI reference docs with the standard-event ingestion route, payload limits, routing behavior, and the fact that gateway validation is AG-UI-only.
- [x] 6.3 Run `openspec validate agent-authored-ag-ui-messages --strict`.
- [x] 6.4 Run focused Python unit tests for AG-UI authoring, CLI, gateway route, and system-skill catalog behavior.
- [x] 6.5 Run workbench typecheck/build and deterministic Playwright coverage for component rendering.
- [x] 6.6 Run `pixi run lint`, `pixi run typecheck`, and relevant `pixi run test` subsets before marking the implementation complete.
