# per-agent-ag-ui-e2e-smoke Specification

## Purpose
TBD - created by archiving change add-ag-ui-e2e-smoke-and-demo. Update Purpose after archive.
## Requirements
### Requirement: AG-UI run smoke exercises the live per-agent gateway contract
Houmao SHALL provide a deterministic end-to-end smoke path that posts AG-UI `RunAgentInput` JSON to the live per-agent gateway `POST /v1/ag-ui/runs` route and consumes the response as AG-UI SSE.

The smoke path SHALL exercise the real gateway route registration, request admission, durable request-state observation, canonical headless artifact lookup, AG-UI event mapping, and SSE framing. It SHALL NOT call the mapper directly as the only validation path.

The smoke path SHALL assert that the AG-UI `runId` is preserved as the gateway prompt `turn_id` and as the headless artifact lookup key used for `<manifest-stem>.turn-artifacts/<runId>/canonical-events.jsonl`.

#### Scenario: Deterministic run smoke observes the full AG-UI lifecycle
- **WHEN** the smoke posts a valid AG-UI run input to `/v1/ag-ui/runs` on a live per-agent gateway test surface
- **THEN** the response status is successful and the content type is `text/event-stream`
- **AND THEN** the SSE stream contains `RUN_STARTED` before mapped output events
- **AND THEN** the SSE stream contains exactly one terminal event, `RUN_FINISHED` or `RUN_ERROR`
- **AND THEN** the accepted gateway request payload uses the AG-UI `runId` as its prompt `turn_id`

#### Scenario: Run-id-derived artifact path is used for headless output
- **WHEN** a deterministic headless AG-UI smoke uses `runId` value `agui-smoke-run-1`
- **THEN** the canonical artifact lookup resolves the turn artifact directory for `agui-smoke-run-1`
- **AND THEN** mapped AG-UI output comes from the canonical event artifact associated with that run id
- **AND THEN** output from another run id is not included in the stream

### Requirement: Graphics smoke reconstructs CopilotKit-compatible tool calls deterministically
Houmao SHALL provide a deterministic graphics smoke that proves an explicit canonical `houmao_render_graphic` artifact streams as a CopilotKit-compatible assistant-parented tool call sequence.

The first graphics smoke SHALL control the canonical event input. It SHALL NOT depend on a live model choosing to call `houmao_render_graphic`, because AG-UI declared tools are not yet provider-native frontend tool bindings.

The graphics smoke SHALL reconstruct at least one assistant message with one `toolCalls` entry whose name is `houmao_render_graphic` and whose parsed arguments match the typed Houmao graphics artifact payload.

#### Scenario: Controlled graphics artifact reconstructs one rendered tool call
- **WHEN** the deterministic smoke supplies a canonical headless event named `houmao_render_graphic` with a valid SVG, HTML fragment, image URL, image data URI, or chart JSON payload
- **THEN** the AG-UI stream emits `TOOL_CALL_START`, `TOOL_CALL_ARGS`, and `TOOL_CALL_END` for `houmao_render_graphic`
- **AND THEN** the tool call has a parent assistant message id
- **AND THEN** a CopilotKit-style message collector reconstructs one assistant message containing that tool call in its `toolCalls` list
- **AND THEN** the parsed tool arguments preserve the artifact `title`, `format`, content locator, `altText`, and metadata fields allowed by the graphics schema

#### Scenario: Graphics smoke does not rely on Markdown scraping
- **WHEN** the deterministic smoke includes assistant prose or Markdown adjacent to the graphic artifact
- **THEN** the smoke validates only the structured `houmao_render_graphic` tool-call arguments as the graphic payload
- **AND THEN** the smoke does not treat Markdown image links, prose, or unstructured HTML snippets as generated graphics unless they are inside a validated graphics artifact

### Requirement: Live managed-agent smoke covers AG-UI text lifecycle
Houmao SHALL provide a manual or integration smoke path that launches or reuses one real managed headless agent with a live per-agent gateway and submits a plain-text AG-UI run through `/v1/ag-ui/runs`.

The live smoke SHALL verify queue admission, stream lifecycle ordering, mapped assistant text or compatible terminal output, request completion, and cleanup through maintained Houmao managed-agent launch and gateway patterns.

The live smoke SHALL NOT require real generated graphics until Houmao has provider-native tool binding or another deterministic managed-agent artifact mechanism for graphics.

#### Scenario: Real headless gateway completes an AG-UI text run
- **WHEN** a maintained live headless gateway smoke starts one real managed headless target and posts a plain-text AG-UI run
- **THEN** the run is admitted through the gateway request queue
- **AND THEN** the stream emits `RUN_STARTED`
- **AND THEN** the stream emits mapped text or compatible terminal output from the completed turn
- **AND THEN** the stream emits `RUN_FINISHED` after the gateway request reaches a completed terminal state
- **AND THEN** the smoke cleanup stops or detaches only the demo-owned resources

#### Scenario: Live smoke keeps GUI lifecycle separate from agent lifecycle
- **WHEN** the AG-UI client closes the run stream during a live managed-agent smoke
- **THEN** Houmao detaches the stream subscription
- **AND THEN** Houmao does not stop, restart, shut down, or interrupt the managed agent unless an explicit abort policy is enabled

### Requirement: Browser or client smoke validates graphics rendering fixture
Houmao SHALL provide an explicit browser or client smoke fixture that can consume the deterministic AG-UI graphics stream and verify that `houmao_render_graphic` can be rendered by an AG-UI or CopilotKit-style client.

Browser automation SHALL use the Bun-global Playwright toolchain. Browser checks SHALL be opt-in and SHALL NOT be required by the default Python unit-test command.

#### Scenario: Playwright smoke observes a rendered graphic
- **WHEN** an operator runs the explicit AG-UI graphics browser smoke in an environment with Bun-global Playwright available
- **THEN** the smoke starts or targets a deterministic AG-UI graphics stream
- **AND THEN** the browser client receives the `houmao_render_graphic` tool call
- **AND THEN** the page renders visible graphic evidence such as the artifact title, alt text, SVG element, image element, or chart JSON content
- **AND THEN** the smoke records enough output to diagnose a missing stream, missing tool call, or failed render

#### Scenario: Browser smoke is skipped clearly when unavailable
- **WHEN** Bun-global Playwright or its browser bundle is unavailable
- **THEN** the browser smoke fails or skips with a clear prerequisite diagnostic
- **AND THEN** the default backend AG-UI test suite remains runnable without Playwright

### Requirement: AG-UI demo documentation covers direct gateway setup and limits
Houmao SHALL document how to run the per-agent AG-UI smoke or demo against the live gateway before the passive-server facade exists.

The documentation SHALL show the direct `/v1/ag-ui/runs` endpoint, the capability discovery endpoint, and a minimal AG-UI or CopilotKit `HttpAgent` setup that registers the `houmao_render_graphic` renderer. It SHALL also state the known limits: lower-fidelity TUI streams, no frontend tool execution, no state deltas, conservative multimodal support, deterministic graphics smoke, and GUI-detach lifecycle semantics.

#### Scenario: Operator can find the direct per-agent AG-UI workflow
- **WHEN** an operator reads the AG-UI gateway documentation or demo README
- **THEN** the documentation identifies the live gateway `GET /v1/ag-ui/capabilities` and `POST /v1/ag-ui/runs` routes
- **AND THEN** it shows how to point an AG-UI or CopilotKit `HttpAgent` at the run endpoint
- **AND THEN** it explains that the GUI attaches to an existing Houmao agent and does not manage that agent's lifecycle

#### Scenario: Documented examples match registered routes
- **WHEN** the documentation includes curl examples or demo route constants for per-agent AG-UI routes
- **THEN** a route or docs drift test can verify those examples still match the FastAPI route inventory
- **AND THEN** stale passive-server-style routes are not presented as required for the stage 1 demo

### Requirement: Passive-server readiness smoke defines stream proxy expectations
Houmao SHALL include a passive-server readiness test or fixture that defines the stream-preservation contract required for future stage 2 AG-UI proxying.

The readiness check SHALL use a fake upstream per-agent AG-UI stream and assert that a proposed passive-server proxy can preserve status behavior, `text/event-stream` content type, and event bytes. It SHALL NOT require the stage 2 passive-server proxy routes to be implemented in this change.

#### Scenario: Readiness fixture preserves upstream stream semantics
- **WHEN** a fake upstream per-agent gateway returns an AG-UI SSE stream
- **THEN** the readiness fixture can assert that a future passive-server proxy preserves the upstream content type and event byte framing
- **AND THEN** the readiness fixture records how upstream HTTP errors and post-admission `RUN_ERROR` events should pass through the facade
- **AND THEN** the fixture remains marked as readiness or spike coverage until stage 2 implements the proxy routes

### Requirement: Real workbench smoke exercises a live agent GUI graphics loop
Houmao SHALL provide an explicit opt-in smoke that drives the AG-UI workbench GUI against one existing real managed Houmao test agent.

The smoke SHALL restart the selected test agent before exercising the GUI path.

The smoke SHALL use passive-server discovery or resolution to select the target agent in the workbench.

The smoke SHALL connect the workbench pane to the selected agent gateway before submitting a prompt.

The smoke SHALL submit the validation prompt through the workbench prompt composer and run button rather than by posting directly to the gateway from the test harness.

The validation prompt SHALL ask the agent to publish one `houmao.graphic.template` chart to the current GUI thread and request a nonce-labeled text completion marker.

The smoke SHALL remain opt-in and SHALL NOT be part of the default unit-test command.

#### Scenario: Operator enables the real-agent GUI smoke
- **WHEN** an operator runs the real-agent GUI smoke with the required opt-in flag, passive-server URL, and test-agent selector
- **THEN** the smoke restarts the selected managed agent through maintained `houmao-mgr` lifecycle commands
- **AND THEN** the smoke opens the AG-UI workbench in Playwright
- **AND THEN** the smoke selects the same agent through the workbench agent picker
- **AND THEN** the smoke connects the workbench pane to the agent gateway before sending the prompt

#### Scenario: Missing prerequisites fail before model work
- **WHEN** the opt-in flag, passive-server URL, test-agent selector, live gateway, or Playwright browser prerequisite is missing
- **THEN** the smoke fails or skips with a diagnostic naming the missing prerequisite
- **AND THEN** the smoke does not submit a model prompt

### Requirement: Real workbench smoke validates rendered template graphics
The real-agent GUI smoke SHALL verify that the selected agent and gateway advertise AG-UI run submission, GUI connect streams, and live published-event fanout before submitting the validation prompt.

The smoke SHALL verify local `houmao.graphic.template` authoring support before submitting the validation prompt.

The smoke SHALL record template graphics presentation metadata when the gateway advertises it, but SHALL NOT require `generatedGraphics=true` for TUI-backed agents that publish already-rendered AG-UI events through `/v1/ag-ui/events`.

The validation prompt SHALL include a unique nonce, the current GUI thread id when available, the `houmao.graphic.template` component name, the requested `vega-lite` renderer preference, and a simple chart data set.

The smoke SHALL pass only when the workbench DOM contains the nonce-labeled chart title and visible renderer output.

The smoke SHALL record whether the workbench transcript contains the nonce-labeled completion marker when the agent emits one, but the completion marker SHALL NOT be required when the nonce-labeled chart is rendered.

The smoke SHALL prefer visible Vega-Lite SVG evidence for the chart renderer.

The smoke SHALL treat a text-only answer, Markdown-only chart, stale chart, wrong component name, or missing rendered chart as a failure.

#### Scenario: Agent publishes and GUI renders a template graphic
- **WHEN** the connected workbench pane submits the validation prompt to the selected real agent
- **AND WHEN** the agent publishes a complete `houmao.graphic.template` AG-UI tool-call sequence for the prompt nonce
- **THEN** the workbench displays the prompt-specific chart title
- **AND THEN** the workbench displays visible chart renderer output for that tool call
- **AND THEN** the smoke records whether the transcript contains the prompt-specific completion marker

#### Scenario: Text-only completion does not satisfy graphics smoke
- **WHEN** the connected workbench pane receives the prompt-specific completion marker but no `houmao.graphic.template` chart with the prompt-specific title
- **THEN** the smoke fails
- **AND THEN** the failure diagnostic distinguishes missing rendered graphics from optional missing text completion

### Requirement: Real workbench smoke records actionable failure evidence
The real-agent GUI smoke SHALL record diagnostics for setup, agent, gateway, and browser failures.

Failure evidence SHALL include the selected agent id or name, passive-server URL, resolved gateway target, GUI thread id when available, AG-UI capabilities response when available, submitted prompt, browser console output, screenshot, and visible transcript text.

When raw AG-UI events or reconstructed tool-call diagnostics are available through the workbench or gateway, the smoke SHALL preserve them as additional evidence.

The smoke SHALL detach or close GUI browser resources during cleanup. It SHALL NOT stop, restart again, shut down, or interrupt the selected managed agent after the smoke unless the operator enables an explicit cleanup option.

#### Scenario: Graphics assertion failure saves diagnostics
- **WHEN** the real-agent GUI smoke does not observe the expected rendered chart before the timeout
- **THEN** the smoke saves browser and gateway diagnostics sufficient to tell whether selection, connection, prompt submission, agent output, event delivery, or rendering failed
- **AND THEN** the smoke exits non-zero or reports a clear skipped status according to the missing prerequisite

#### Scenario: Cleanup preserves existing test agent ownership
- **WHEN** the real-agent GUI smoke completes or fails after relaunching an existing selected test agent
- **THEN** the smoke closes browser resources and detaches GUI subscriptions it opened
- **AND THEN** the smoke leaves the managed agent running unless an explicit stop-after-smoke option is enabled
