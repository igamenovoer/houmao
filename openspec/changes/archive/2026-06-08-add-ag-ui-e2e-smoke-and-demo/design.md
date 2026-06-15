## Context

Milestone 1 exposed the live per-agent AG-UI route surface and Milestone 2 made `/v1/ag-ui/runs` admit one task through `GatewayServiceRuntime.create_request()`, map canonical headless/TUI observations, and stream AG-UI SSE events including `houmao_render_graphic` tool calls. The remaining stage 1 gap is not another mapper feature. It is confidence that a real gateway route, durable request row, worker execution, canonical artifact lookup, SSE stream, and CopilotKit-style client reconstruction all agree on the same run contract.

The important invariant is that the AG-UI `runId` becomes the gateway prompt `turn_id`. For headless targets, `GatewayServiceRuntime.ag_ui_headless_artifact(run_id)` resolves canonical events from `<manifest-stem>.turn-artifacts/<runId>/canonical-events.jsonl`. An end-to-end smoke can assert this invariant directly.

The current adapter includes AG-UI declared tools in the prompt context, but it does not bind frontend tools into provider-native tool execution. A live model may describe a graphic in prose or Markdown rather than emit a structured `houmao_render_graphic` action. The first graphics E2E must therefore control the canonical event input while still exercising the live gateway and SSE path.

## Goals / Non-Goals

**Goals:**

- Prove `/v1/ag-ui/runs` through a real live gateway route, not only direct mapper or fake route calls.
- Prove deterministic graphics reconstruction from AG-UI SSE into one assistant message with a `houmao_render_graphic` tool call.
- Prove a real managed headless agent can submit and complete an AG-UI text run through the gateway queue.
- Add diagnostics that let an operator inspect AG-UI connect/run activity and stream failures without exposing private state.
- Provide a minimal documented demo path that can be run before starting the passive-server facade.
- Define a passive-server readiness check for preserving upstream AG-UI SSE semantics.

**Non-Goals:**

- Do not implement passive-server AG-UI proxy routes in this change.
- Do not add provider-native frontend tool execution or require live models to call `houmao_render_graphic`.
- Do not add Open Generative UI or sandboxed generated JavaScript support.
- Do not give CopilotKit or any GUI lifecycle authority over managed Houmao agents.
- Do not make browser tests mandatory for ordinary unit-test runs.

## Decisions

### Use a Layered E2E Strategy

The change should add three validation layers:

1. A deterministic AG-UI wire E2E that starts a real gateway app/runtime surface, posts `RunAgentInput` to `/v1/ag-ui/runs`, consumes the SSE response, and reconstructs assistant messages/tool calls.
2. A live managed-agent smoke that reuses existing headless gateway launch and cleanup patterns to prove queue admission, lifecycle events, and terminal completion against one real headless target.
3. A browser or client rendering smoke that uses the Bun-global Playwright toolchain and a minimal AG-UI/CopilotKit-style fixture to verify `houmao_render_graphic` rendering.

Rationale: each layer catches different failures. The deterministic layer catches protocol and artifact-contract bugs. The live-agent layer catches runtime integration and admission bugs. The browser layer catches client reconstruction and renderer assumptions.

Alternative considered: one large CopilotKit demo as the only E2E. That would mix gateway, model, JavaScript runtime, React rendering, and browser failures into one test and make regressions harder to localize.

### Control the First Graphics Oracle

The first generated-graphics smoke should use a deterministic canonical headless artifact that contains an explicit `action_request` or `action_result` named `houmao_render_graphic`. It may be produced by a fixture adapter, a small fixture command whose provider-shaped JSON is parsed by the existing headless canonicalizer, or a controlled runtime double that still writes the canonical artifact at the real run-id-derived path.

Rationale: the AG-UI adapter currently does not bind declared frontend tools into provider-native tool execution. Depending on a live model to choose the exact graphics tool call would make the smoke flaky and would test model behavior more than Houmao's AG-UI contract.

Alternative considered: prompt the live model to emit a graphic and parse Markdown or prose. That conflicts with the Milestone 2 decision that graphics must be explicit structured artifacts, not Markdown scraping.

### Reuse Existing Demo Launch and Cleanup Patterns

The live managed-agent smoke should reuse the repo's existing headless gateway demo/manual conventions, including isolated output roots, fixture auth bundles, gateway attach, and explicit cleanup. It should add an AG-UI probe to those flows rather than creating a separate managed-agent lifecycle stack.

Rationale: lifecycle bugs are already expensive in managed-agent demos. Reusing the maintained launch/cleanup posture reduces new moving parts and keeps failure artifacts in familiar locations.

Alternative considered: build a standalone ad hoc launcher only for AG-UI. That would duplicate fragile lifecycle logic and drift from operator workflows.

### Treat Browser Checks as Optional Smoke Evidence

Browser rendering checks should use the Bun-global Playwright installation documented in `AGENTS.md`. They should run through an explicit command or manual/demo script, not as part of default `pixi run test`.

Rationale: browser checks are valuable for CopilotKit-style rendering but slower and more environment-sensitive than unit tests. Making them explicit keeps the default test suite stable.

Alternative considered: require Playwright in the default Python test run. That would make ordinary backend checks depend on a Node/browser toolchain.

### Add Diagnostics Without Exposing Private State

AG-UI diagnostics should record lifecycle-shaped facts: route, connection id or run id, request id, transport family, event name, status code, terminal outcome, active connection count, active run count, duration, and error category. They must not include prompt text, mailbox content, memory, raw terminal history, credentials, or unmanaged forwarded props.

Rationale: stage 1 needs enough observability to debug stream failures and passive-server proxying, but AG-UI remains a presentation adapter over sensitive managed-agent state.

Alternative considered: emit raw request and state payloads into diagnostics. That would simplify debugging but violates the AG-UI data-boundary established in the roadmap.

### Define Passive-Server Readiness as a Contract Test

This change should add a readiness fixture or test that consumes a fake upstream per-agent AG-UI stream and asserts a proposed passive-server proxy can preserve content type, status behavior, and SSE event bytes. It should not implement the stage 2 route.

Rationale: stage 2 needs a concrete target before implementation, but proxy code belongs in a separate change so stage 1 can close cleanly.

Alternative considered: start passive-server proxying immediately. That expands scope before the per-agent endpoint has live E2E evidence.

## Risks / Trade-offs

- [Risk] A deterministic fixture may pass while real agents fail to produce graphics → Mitigation: split the live-agent smoke into text/lifecycle coverage and document that provider-native graphics generation remains future work until tool binding exists.
- [Risk] Browser smoke tests become flaky in headless environments → Mitigation: keep them opt-in, use the Bun-global Playwright toolchain, and make the deterministic AG-UI client reconstruction test the required gate.
- [Risk] Active run counters can leak or stay non-zero after client disconnects → Mitigation: tie counters to stream setup/finally blocks and add tests for success, error, and abort paths.
- [Risk] Stream errors after `RUN_STARTED` can terminate HTTP responses without an AG-UI terminal event → Mitigation: catch mapping/encoding failures at the stream boundary, log the error category, and emit `RUN_ERROR` when the stream has already started and the client is still connected.
- [Risk] Docs drift from route behavior → Mitigation: add route/docs drift tests for documented curl examples and capability payload assumptions.

## Migration Plan

1. Add diagnostics and counters around existing AG-UI connect/run streams without changing route names or request shapes.
2. Add deterministic AG-UI E2E helpers and tests for `/v1/ag-ui/runs`, including `houmao_render_graphic` reconstruction.
3. Add or extend a manual/demo script that launches one live headless gateway target and runs an AG-UI text smoke.
4. Add a minimal browser/client fixture and optional Playwright smoke command.
5. Update gateway docs and the AG-UI roadmap with the smoke workflow, limits, and passive-server readiness result.

Rollback is removing the new tests, demo fixtures, docs, and diagnostics additions. The AG-UI public route contract should remain compatible throughout this change.

## Open Questions

- Should the deterministic graphics fixture use a direct canonical artifact writer or a provider-shaped fixture command that exercises the existing headless parser?
- Should the browser smoke use `@ag-ui/client` directly as the first supported fixture, or should it immediately mount a minimal CopilotKit runtime and renderer?
- Which existing demo pack should own the live AG-UI text smoke: the single-agent gateway wakeup demo, a small new AG-UI demo pack, or a manual script under `tests/manual/`?
