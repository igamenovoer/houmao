## Context

AG-UI core defines event envelopes and message/tool/state/custom event types. It carries tool names and JSON payloads, but it does not standardize application component names such as `barChart`, `render_bar_chart`, or `houmao.chart.bar`. The local AG-UI SDK models under `extern/orphan/ag-ui/sdks/python/ag_ui/core/` confirm that tool-call events are standard while component naming is open-ended. The local CopilotKit examples under `extern/orphan/copilotkit/showcase/` use `useComponent` and `useRenderTool` registrations to map app-defined names to React renderers.

Houmao currently maps structured headless graphics artifacts to one AG-UI tool call named `houmao_render_graphic`, and the workbench renders only SVG payloads from that tool call. TUI agents cannot participate in that path unless a structured Houmao event appears in their observed output. The intended model is broader: any Houmao agent, including TUI agents, can use code or shell commands to ask `houmao-mgr` to validate a typed GUI message and emit standard AG-UI events. `houmao-mgr` can publish those events to a Houmao gateway, while agents that target third-party AG-UI-compatible endpoints use the generated events and perform delivery themselves according to the target endpoint's constraints.

## Goals / Non-Goals

**Goals:**

- Let agents discover Houmao GUI component schemas without reading frontend source.
- Let agents validate component payloads and generate standard AG-UI events through `houmao-mgr`.
- Let `houmao-mgr` publish generated events only through Houmao gateway-specific surfaces.
- Keep the per-agent gateway aware of AG-UI event syntax and stream routing only; it must not own Houmao component schemas.
- Let the workbench render a useful first set of typed graphics components, including chart, table, metric-grid, and dashboard-style layouts.
- Package an agent-facing skill that teaches the workflow and the safety boundary.

**Non-Goals:**

- Standardize Houmao component names as part of AG-UI itself.
- Require a gateway for all AG-UI authoring; `houmao-mgr` must be usable as an offline event generator.
- Make `houmao-mgr` an arbitrary third-party AG-UI HTTP client.
- Add frontend tool execution or CopilotKit runtime dependency to the workbench.
- Treat raw HTML or arbitrary SVG as trusted component input.
- Preserve the narrow `houmao_render_graphic` path as the only graphics contract.

## Decisions

### `houmao-mgr` Owns the Application Protocol

Create a shared authoring package, tentatively `houmao.ag_ui.authoring`, with Pydantic models for Houmao component messages and event-generation helpers. The initial component names should be namespaced and versioned by schema, for example `houmao.chart.bar` with `schemaVersion: 1` in the payload. Initial components should cover:

- `houmao.chart.bar`
- `houmao.chart.line`
- `houmao.chart.pie`
- `houmao.table`
- `houmao.metric_grid`
- `houmao.dashboard`

`houmao-mgr internals ag-ui ...` should expose schema discovery, validation, and rendering:

- `houmao-mgr internals ag-ui components list`
- `houmao-mgr internals ag-ui components schema <component>`
- `houmao-mgr internals ag-ui components validate <component> --input <path-or->`
- `houmao-mgr internals ag-ui events render <component> --input <path-or-> --format json|jsonl|sse`
- `houmao-mgr internals ag-ui events validate --input <path-or->`

This keeps typed component knowledge in a tool agents can invoke directly. A separate Houmao gateway publish helper should live under the maintained scoped gateway command family:

```bash
houmao-mgr agents self gateway ag-ui publish --input <events-json>
houmao-mgr agents single --agent-id <id> gateway ag-ui publish --input <events-json>
houmao-mgr agents single --agent-name <name> gateway ag-ui publish --input <events-json>
```

The publish helper should accept routing options only for Houmao gateway semantics, such as `--thread-id`, `--run-id`, or `--connection-id` when the gateway ingestion contract needs them. It should post only to the resolved Houmao gateway AG-UI ingestion route after validating the event sequence.

The publish helper must not expose arbitrary endpoint controls such as:

```bash
houmao-mgr ... ag-ui publish --endpoint <url>
houmao-mgr ... ag-ui publish --method <method>
houmao-mgr ... ag-ui publish --content-type <type>
```

For third-party AG-UI-compatible endpoints, `houmao-mgr` stops at generated and validated events; the agent sends them using whatever request shape, authentication, headers, stream framing, or admission policy that endpoint requires.

Alternative considered: put schema discovery and component validation in the gateway. That would make the gateway a Houmao application protocol server, which conflicts with the desired separation and makes non-gateway AG-UI event generation harder.

### Render Typed Components as Standard Tool-Call Events

The canonical event output for a component should be an AG-UI tool-call sequence whose `toolCallName` is the component name, for example `houmao.chart.bar`. The CLI should generate `TOOL_CALL_START`, one or more `TOOL_CALL_ARGS`, and `TOOL_CALL_END`, with optional assistant text message framing and optional `TOOL_CALL_RESULT` summary. The arguments should be the validated component payload JSON using AG-UI camelCase field names where applicable.

This mirrors CopilotKit’s `useComponent` and `useRenderTool` pattern without copying CopilotKit’s component names or requiring CopilotKit in the workbench. It also keeps third-party AG-UI clients able to treat unknown Houmao components as ordinary tool calls.

Alternative considered: emit `CUSTOM` events for every component. `CUSTOM` is useful for out-of-band UI state, but tool-call events are a better fit for chat-adjacent generative UI because existing AG-UI/CopilotKit clients already model renderable tool calls.

### Gateway Validates AG-UI, Not Houmao Components

Add a gateway event ingestion route such as `POST /v1/ag-ui/events`. The request body should carry routing metadata plus a list of event objects. The gateway should validate that each event is a known AG-UI core event shape, enforce bounded size and event count limits, reject inconsistent run/thread identifiers when present, assign or preserve safe event IDs for replay bookkeeping, and broadcast accepted events to matching connect/run streams.

The gateway must treat `toolCallName: "houmao.chart.bar"` as an opaque string. It should reject malformed `TOOL_CALL_START` or invalid ordering when it can verify ordering, but it should not inspect the component’s `props`, chart series, dashboard layout, or visual semantics.

Alternative considered: reuse `POST /v1/ag-ui/runs` for event publishing. That route admits prompt work and owns run lifecycle. Event publishing is a separate stream-ingestion concern and should not create a Houmao prompt or mutate agent lifecycle.

### Workbench Renders Known Houmao Components Defensively

Refactor the workbench graphic rendering path into a renderer registry keyed by tool/custom component name. The reducer should keep complete tool-call records as it does now, but the rendering layer should parse known component names through local TypeScript validators before rendering. Unknown names should remain visible as raw tool calls.

The workbench should add a chart renderer using a maintained charting library such as Recharts, following the CopilotKit local examples. It should also render tables, metric grids, and dashboard containers with stable responsive dimensions. Inline SVG/HTML should remain unsupported unless a dedicated sanitizer and renderer is introduced in a later change.

Alternative considered: keep only `houmao_render_graphic`. That cannot represent dashboard-style typed components cleanly and keeps TUI agents dependent on a headless artifact mapper.

### Skill Teaches the Agent Workflow

Add a packaged system skill named `houmao-agent-ag-ui`. The skill should explain that AG-UI is the wire protocol, while Houmao component schemas are application-layer conventions managed through `houmao-mgr`. The workflow should be:

1. Resolve `houmao-mgr` using the established launcher precedence.
2. Discover the component schema.
3. Create a payload that matches the schema.
4. Validate the payload.
5. Render standard AG-UI events.
6. Publish through a Houmao gateway when targeting Houmao, or use the generated events as the handoff artifact for third-party endpoints.

The skill should warn agents not to handcraft unvalidated raw HTML/SVG and not to assume CopilotKit demo component names are AG-UI standards.

## Risks / Trade-offs

- Gateway does not validate component semantics → The GUI must defensively validate known component payloads and degrade unknown or invalid components to raw tool-call display.
- Tool-call event sequences need ordering rules → `houmao-mgr` should generate complete sequences by default, and the gateway should reject obvious malformed sequences such as args before start within one publish batch.
- Third-party AG-UI receivers may impose endpoint-specific constraints → `houmao-mgr` only generates and validates events for that lane; the agent handles delivery using the receiver's own API contract.
- Dashboard rendering can grow quickly → Start with a small typed component set and avoid raw HTML/iframe support in this change.
- CLI surface under `internals` may become user-facing by habit → Keep command help explicit that these are agent-authoring utilities, then promote later only if the workflow stabilizes.

## Migration Plan

1. Add the authoring models and CLI commands without changing existing AG-UI run/connect behavior.
2. Add the gateway event ingestion route and tests behind the existing AG-UI route registration.
3. Add workbench renderers while keeping `houmao_render_graphic` visible through the same registry.
4. Add the packaged skill and catalog metadata.
5. Update deterministic fixtures to publish a chart/table/dashboard event batch through the new route.

Rollback is straightforward before release: remove the new CLI group, route, renderer registry entries, and skill asset. Existing `/v1/ag-ui/capabilities`, `/connect`, `/runs`, and `houmao_render_graphic` behavior can remain unchanged during rollback.

## Open Questions

- Should the gateway ingestion route accept a raw JSON array of events, or require a wrapper with `threadId`, `runId`, and replay options?
- Should `houmao-mgr internals ag-ui events render` generate assistant message framing by default, or require an explicit `--with-message` flag?
- Should `houmao.dashboard` compose only other Houmao components, or also allow simple Markdown/text blocks in the initial version?
