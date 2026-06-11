## Context

The current AG-UI validation stack has three useful but separate layers. Backend integration tests cover `/v1/ag-ui/runs` and AG-UI SSE mapping. The deterministic browser smoke verifies that the workbench can render graphics from a controlled stream. The live managed-agent smoke submits a plain-text AG-UI run to a real gateway, but it bypasses the workbench UI and intentionally does not require a live model to produce graphics.

The missing coverage is the actual operator path: the workbench discovers a managed agent, connects to its gateway, marks or uses an active GUI thread, submits a prompt through the GUI, the real agent publishes a `houmao.graphic.template` message, and the workbench renders it. This change adds an opt-in smoke for that path. It is not suitable for default CI because it depends on local credentials, a managed agent runtime, passive-server discovery, model behavior, and browser automation.

## Goals / Non-Goals

**Goals:**

- Add a reproducible opt-in Playwright smoke that drives `apps/ag-ui-workbench` against an existing real Houmao test agent.
- Restart the selected agent before the test so stale agent state is not silently reused.
- Exercise the GUI prompt path, not a direct HTTP-only `/v1/ag-ui/runs` helper.
- Verify that the GUI receives and renders a nonce-labeled `houmao.graphic.template` chart, with Vega-Lite SVG output as preferred evidence.
- Capture enough diagnostics for live-agent, gateway, and renderer failures.
- Keep the test outside `pixi run test` and other default test paths.

**Non-Goals:**

- Do not make live model graphics deterministic enough for required CI.
- Do not start or own arbitrary user agents without an explicit test-agent selector.
- Do not add a new AG-UI protocol feature or change runtime event semantics.
- Do not test Layer 2 raw Vega/Vega-Lite DSL graphics or custom React components.
- Do not require stopping the existing test agent after the smoke unless an operator explicitly opts in.

## Decisions

### Gate the smoke behind explicit environment variables

The smoke requires `HMWB_REAL_AGENT_SMOKE=1`, a passive-server URL, and either a test agent name or id. The harness fails early with clear setup diagnostics when those values are missing.

Alternative considered: include this in the regular workbench Playwright suite. That would make ordinary frontend checks depend on live credentials and model timing, which would create false failures unrelated to renderer regressions.

### Let Playwright drive the GUI and shell out only for setup

Playwright opens the workbench, selects the agent through the existing picker, connects the pane, submits the prompt, and inspects the DOM. A Node or Bun setup fixture shells out to `pixi run houmao-mgr` only for agent relaunch and optional readiness checks.

Alternative considered: post directly to `/v1/ag-ui/runs` from the test process. That would test the gateway but would miss the workbench target selection, connection, active-thread, prompt composer, run submission, and renderer path that this change is meant to cover.

### Connect before prompting and include the pane thread id in the prompt

The test connects first so the gateway has a live stream destination for agent-published events. The prompt includes the current pane thread id as a fallback route, so the agent can publish to the active GUI thread or to an explicit thread if active-thread routing is unavailable.

Alternative considered: rely only on the active-thread default. That is simpler but makes failures ambiguous when the agent publishes correctly to the wrong or unsupported route.

### Use a nonce-labeled prompt and chart title

Each run generates a nonce. The prompt asks the agent to publish a chart titled `Real Agent Template Graphic Smoke <nonce>` and also requests `AG_UI_TEMPLATE_GRAPHIC_SMOKE_DONE <nonce>` as an optional text marker. The test passes on the rendered chart title and SVG renderer evidence because that is the GUI message under validation. It records whether the text marker appeared for diagnostics.

Alternative considered: require the text marker as well as the chart. That proved too strict for TUI-backed real agents that publish the GUI event correctly but do not map a final text reply into the AG-UI transcript before the smoke timeout.

### Treat agent-published graphics separately from headless generated-graphics metadata

The prompt asks for `renderer.preferred = "vega-lite"` with `recharts` as fallback. The primary DOM assertion looks for the workbench Vega-Lite template chart container and an SVG. Failure artifacts should include enough event and capability data to explain whether the agent emitted the wrong component, the gateway missed delivery, or the renderer failed.

The smoke requires live AG-UI run/connect support, published-event fanout metadata, and local `houmao-mgr internals ag-ui components schema houmao.graphic.template` support. It records `generatedGraphics` and template presentation metadata when the gateway advertises them, but it does not require `generatedGraphics=true` for TUI-backed agents. `generatedGraphics` describes headless canonical artifact mapping, while this smoke validates agent-published GUI events through `/v1/ag-ui/events`.

Alternative considered: require `generatedGraphics=true` and the template tool in AG-UI capabilities. That is correct for headless artifact-mapping coverage, but it excludes the existing TUI-backed test agent even though that agent can publish already-rendered AG-UI events to an active GUI stream.

## Risks / Trade-offs

- Live model does not follow the prompt → Keep the smoke opt-in, use a strict prompt, include the exact component name and authoring-helper path, and record transcript/event evidence.
- Agent publishes before the GUI is connected → Connect first, wait for connected or watched status, and verify active-thread or explicit thread details before prompting.
- Passive-server or gateway routes drift → Preflight discovery, run/connect capabilities, published-event metadata, template authoring schema discovery, and route resolution before model work begins.
- Browser selectors drift → Use existing `data-testid` hooks and add missing hooks only where necessary for stable smoke assertions.
- Vega-Lite rendering is visually different across browsers → Assert semantic title visibility and SVG presence, not pixel-perfect layout.
- Existing test agent state is user-owned → Relaunch only the selected test agent and avoid stopping it by default.

## Migration Plan

This is an additive smoke-test change. Add the harness and documentation, run the deterministic Python and browser tests, then run the real-agent smoke manually in an environment with a configured test agent and credentials. Rollback is deleting or disabling the opt-in smoke and docs; runtime AG-UI behavior is unchanged.

## Open Questions

- Which existing local test agent name should documentation use as the recommended example?
- Should the first implementation live under `apps/ag-ui-workbench` Playwright tests, `scripts/demo`, or both with one shell wrapper around the Playwright spec?
- Should the smoke fail when Recharts fallback renders successfully, or record fallback as a warning while still passing the operator path?
