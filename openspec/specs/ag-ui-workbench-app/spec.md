# ag-ui-workbench-app Specification

## Purpose
TBD - created by archiving change add-ag-ui-workbench-app. Update Purpose after archive.
## Requirements
### Requirement: Standalone AG-UI workbench app
The repository SHALL provide a standalone AG-UI workbench application under `apps/ag-ui-workbench/` for testing Houmao AG-UI protocol behavior without including the GUI in the Python package distribution.

#### Scenario: Workbench app lives outside Python package contents
- **WHEN** a developer inspects the workbench files and Python build configuration
- **THEN** the workbench is located under `apps/ag-ui-workbench/`
- **AND THEN** the Python wheel target continues to include only the Houmao Python package under `src/houmao`

#### Scenario: Workbench can be started with Bun
- **WHEN** a developer follows the workbench README in a checkout with Bun available
- **THEN** the documented command starts the local workbench development server
- **AND THEN** the command does not require entering `pixi shell`

### Requirement: Operator input panel
The workbench SHALL provide a pinned operator input panel that connects to one configured Houmao operator agent through AG-UI run and connection semantics.

#### Scenario: Operator target can be configured
- **WHEN** a developer opens the operator panel
- **THEN** the panel allows configuring a label, AG-UI base URL or run URL, and thread identifier for the operator Houmao agent

#### Scenario: Operator prompt submits one AG-UI run
- **WHEN** the operator panel is connected and the user submits a text prompt
- **THEN** the workbench sends one AG-UI `RunAgentInput` request to the configured operator target
- **AND THEN** the request includes a stable `threadId`, generated `runId`, text user message, empty tools list unless tools are explicitly supported, context array, state object, and forwarded props object

#### Scenario: Operator input does not fan out by default
- **WHEN** multiple agent panes are open and the user submits text through the operator panel
- **THEN** only the configured operator target receives the submitted AG-UI run
- **AND THEN** other panes continue only their own configured connections and runs

### Requirement: Docked multi-agent panes
The workbench SHALL use a dockable pane layout where each agent pane can be added, removed, moved within the main workbench, and configured independently for one running Houmao agent.

#### Scenario: User can add multiple panes
- **WHEN** a developer clicks the add-pane control
- **THEN** the workbench creates a new docked agent pane with its own target configuration and event state

#### Scenario: User can move panes within the docked layout
- **WHEN** a developer drags an agent pane tab or group in the workbench
- **THEN** the pane can be moved into another tab group or into an in-app split position above, below, left, or right of another group
- **AND THEN** the pane remains inside the main workbench browser page

#### Scenario: Floating and popout panes are unavailable
- **WHEN** a developer uses the workbench pane controls, tab context menu, drag behavior, and restored saved layouts
- **THEN** the workbench does not create Dockview floating groups
- **AND THEN** the workbench does not create Dockview popout windows or require a `popout.html` page

#### Scenario: Each pane connects independently
- **WHEN** two panes are configured with different AG-UI targets and both are connected
- **THEN** each pane opens its own AG-UI connection stream or run stream
- **AND THEN** events received by one pane do not appear in the other pane's transcript, state view, or raw event list

#### Scenario: Pane close detaches GUI stream
- **WHEN** a connected pane is closed
- **THEN** the workbench aborts that pane's active browser stream and performs explicit AG-UI connection cleanup when a connection id is available
- **AND THEN** the workbench does not send any Houmao lifecycle stop, restart, shutdown, or interrupt request

### Requirement: Direct AG-UI client and event reduction
The workbench SHALL include direct AG-UI client behavior for Houmao capabilities, connect, run, detach, SSE parsing, stream abort, raw event recording, and reduced display state.

#### Scenario: Capabilities are fetched before interaction
- **WHEN** a pane target is configured
- **THEN** the workbench can request AG-UI capabilities for that target
- **AND THEN** the pane displays whether HTTP SSE, text input, state snapshots, generated graphics, frontend tool execution, state deltas, and multimodal input are reported as supported

#### Scenario: Connect attaches without prompt submission
- **WHEN** a user connects a pane without submitting a prompt
- **THEN** the workbench sends an AG-UI connect request rather than a run request
- **AND THEN** the pane records state snapshot, activity, custom, text, and error events received from that connection stream

#### Scenario: Run stream is reduced into visible state
- **WHEN** a run stream emits `RUN_STARTED`, text message events, state snapshot events, activity events, tool call events, custom events, and `RUN_FINISHED`
- **THEN** the pane shows run status, transcript messages, state snapshot content, activity/custom records, tool-call records, and the raw event timeline

#### Scenario: Run error remains visible
- **WHEN** a target returns a pre-admission HTTP error or an admitted stream emits `RUN_ERROR`
- **THEN** the pane displays the error status and records enough raw event or response detail for debugging without crashing the workbench

### Requirement: Houmao graphics rendering
The workbench SHALL render `houmao_render_graphic` AG-UI tool calls from reduced event state.

#### Scenario: SVG graphic renders visibly
- **WHEN** a stream emits a complete `houmao_render_graphic` tool-call sequence with `format` set to `svg`
- **THEN** the pane renders the graphic title, alt text or title fallback, and sanitized SVG content in the transcript or tool-call area

#### Scenario: Unsupported graphic format degrades visibly
- **WHEN** a stream emits a `houmao_render_graphic` payload with an unsupported or unsafe format
- **THEN** the pane shows a deterministic unsupported-format message and preserves the raw tool-call event details for inspection

### Requirement: Local AG-UI development proxy
The workbench SHALL provide a local development proxy for browser-to-Houmao AG-UI requests that preserves AG-UI HTTP and SSE semantics while restricting target URLs.

#### Scenario: Proxy preserves SSE stream behavior
- **WHEN** the browser sends a proxied AG-UI run or connect request to an allowed target that returns `text/event-stream`
- **THEN** the proxy forwards the upstream status, content type, and SSE bytes to the browser without buffering the full stream

#### Scenario: Proxy rejects disallowed targets
- **WHEN** a pane attempts to proxy an AG-UI request to a non-loopback or otherwise disallowed target
- **THEN** the proxy rejects the request before contacting the target
- **AND THEN** the workbench displays a deterministic target-policy error

#### Scenario: Browser abort aborts upstream request
- **WHEN** the browser aborts an in-flight proxied connect or run request
- **THEN** the proxy aborts the upstream request and releases stream resources

### Requirement: Workbench persistence boundary
The workbench SHALL persist only layout and non-sensitive configuration by default.

#### Scenario: Layout and target metadata persist
- **WHEN** a developer creates panes, moves them, assigns labels, and configures target URLs
- **THEN** the workbench can restore the pane layout and target metadata after a browser reload
- **AND THEN** restored layout state contains only docked grid groups, not floating groups or popout groups

#### Scenario: Stream content is not persisted by default
- **WHEN** a pane receives prompts, messages, raw events, state snapshots, activity records, or graphics payloads
- **THEN** the workbench does not persist those stream contents to local storage by default

### Requirement: Deterministic browser E2E coverage
The repository SHALL include deterministic browser E2E coverage for the workbench using Bun-global Playwright and a fake AG-UI server or route fixture.

#### Scenario: E2E validates operator and multi-pane flow
- **WHEN** the workbench E2E smoke runs against a deterministic AG-UI fixture
- **THEN** it configures the operator panel, adds at least two agent panes, moves a pane into an in-app split, connects panes independently, submits at least one run, and verifies visible transcript or status evidence for each target

#### Scenario: E2E validates graphics and detach behavior
- **WHEN** the deterministic fixture emits a `houmao_render_graphic` sequence and the test closes or disconnects a pane
- **THEN** the test verifies visible graphic evidence
- **AND THEN** the test verifies the browser-side detach or abort path without expecting a Houmao interrupt request

### Requirement: Kimi Code headless live validation guidance
The workbench documentation SHALL describe how to perform live/manual validation for this change with a Kimi Code headless Houmao agent while keeping deterministic fake-server E2E as the required automated test path.

#### Scenario: Documentation names Kimi Code headless live lane
- **WHEN** a developer reads the workbench README or change documentation for live validation
- **THEN** the documentation names Kimi Code headless as the preferred real-agent lane for this change
- **AND THEN** the documentation identifies the local Kimi credential fixture path `tests/fixtures/auth-bundles/kimi/personal-a-default/` as the preferred fixture when available

#### Scenario: Live validation attaches to existing agent gateway
- **WHEN** a developer runs the workbench against a live Kimi Code headless Houmao agent
- **THEN** the workbench attaches to the already-running agent gateway through AG-UI connect or run routes
- **AND THEN** the workbench does not start, stop, restart, shut down, or interrupt the Kimi Code headless agent as part of GUI lifecycle

### Requirement: Workbench renders Houmao typed components from standard AG-UI events
The workbench SHALL render known Houmao typed components carried by standard AG-UI tool-call or custom events.

The renderer registry SHALL be keyed by component or tool-call name.

The initial renderer registry SHALL support `houmao.chart.bar`, `houmao.chart.line`, `houmao.chart.pie`, `houmao.table`, `houmao.metric_grid`, and `houmao.dashboard`.

The workbench SHALL preserve unknown component events as visible raw tool-call or custom-event records rather than failing the pane.

The workbench SHALL continue to render existing `houmao_render_graphic` events through the same rendering path or a compatibility registry entry.

#### Scenario: Bar chart tool call renders visibly
- **WHEN** a stream emits a complete AG-UI tool-call sequence with `toolCallName` equal to `houmao.chart.bar`
- **AND WHEN** the tool-call args validate as a `houmao.chart.bar` payload
- **THEN** the pane renders a visible bar chart with the provided title, labels, and values

#### Scenario: Dashboard event renders contained components
- **WHEN** a stream emits a valid `houmao.dashboard` component payload containing chart and metric-grid children
- **THEN** the pane renders the dashboard layout
- **AND THEN** the child components render through their registered component renderers

#### Scenario: Unknown component remains inspectable
- **WHEN** a stream emits a complete AG-UI tool call with an unknown `toolCallName`
- **THEN** the pane keeps the raw tool-call record visible
- **AND THEN** the pane does not crash or hide the event timeline

### Requirement: Workbench validates component payloads before rendering
The workbench SHALL defensively validate known Houmao component payloads before rendering them.

Invalid known-component payloads SHALL render a deterministic unsupported or invalid-component placeholder.

The placeholder SHALL preserve enough raw event detail for debugging.

The workbench SHALL NOT render raw unsanitized HTML, scriptable SVG, iframe content, or JavaScript URLs from component payloads.

#### Scenario: Invalid chart payload degrades visibly
- **WHEN** a stream emits `houmao.chart.line` with malformed series data
- **THEN** the pane renders an invalid-component placeholder
- **AND THEN** the raw tool-call args remain available in the event timeline or tool-call detail

#### Scenario: Unsafe inline content is not rendered
- **WHEN** a component payload contains raw HTML or scriptable SVG content
- **THEN** the pane does not inject that content into the DOM
- **AND THEN** the pane shows a deterministic unsupported-content placeholder

### Requirement: Workbench renderer tests cover dashboard-style graphics
The repository SHALL include deterministic workbench browser coverage for the Houmao typed component registry.

The browser fixture SHALL emit at least one chart component, one table or metric-grid component, one dashboard component, and one unknown component over AG-UI event streams.

The test SHALL verify visible chart/dashboard evidence and fallback behavior for unknown or invalid components.

#### Scenario: E2E fixture renders typed components
- **WHEN** the workbench E2E suite runs against the deterministic AG-UI fixture
- **THEN** it verifies visible evidence for a Houmao chart component
- **AND THEN** it verifies visible evidence for a dashboard or metric-grid component

#### Scenario: E2E fixture verifies fallback
- **WHEN** the deterministic fixture emits an unknown component name
- **THEN** the E2E test verifies that the raw tool-call or custom-event record remains visible
- **AND THEN** the pane continues processing later AG-UI events

### Requirement: Discovered-agent panes actively reconnect by agent address
For a pane whose target source is a discovered Houmao agent, the workbench SHALL actively resolve the pane's durable agent address through the configured passive server before opening an AG-UI stream.

If the agent is offline, live without a gateway, or temporarily unreachable, the pane SHALL show a deterministic waiting, offline, reconnecting, or gateway-unavailable state and SHALL retry resolution using bounded backoff.

If an active AG-UI stream ends unexpectedly, the pane SHALL mark the stream disconnected and return to the agent-address resolution loop without requiring the user to reselect the agent.

If resolution later returns a different current gateway for the same authoritative agent id, the pane SHALL connect to the new gateway.

The reconnect loop SHALL NOT send Houmao lifecycle start, stop, restart, shutdown, interrupt, or launch requests.

#### Scenario: GUI starts before agent gateway
- **WHEN** a pane targets known agent `abc123`
- **AND WHEN** the passive server reports that no current gateway is available
- **THEN** the pane displays a waiting or offline state
- **AND WHEN** the agent later publishes a live gateway for `abc123`
- **THEN** the pane resolves the current gateway and connects without requiring a new target selection

#### Scenario: Agent gateway restarts on a new port
- **WHEN** a discovered-agent pane is connected to agent `abc123`
- **AND WHEN** the gateway stream fails because the gateway process went offline
- **AND WHEN** passive-server resolution later reports a new gateway port for `abc123`
- **THEN** the pane reconnects to the new gateway
- **AND THEN** the pane still treats `abc123` as the same durable target

#### Scenario: Reconnect does not control lifecycle
- **WHEN** a discovered-agent pane enters reconnecting state
- **THEN** the workbench performs only passive-server resolution and AG-UI connect attempts
- **AND THEN** it does not send start, stop, restart, shutdown, interrupt, launch, or prompt-control requests

### Requirement: Workbench reconnect uses event cursors when supported
The workbench SHALL track the latest applied SSE event id for each pane and thread when the AG-UI stream provides event ids.

When reconnecting to a gateway whose capabilities indicate resumable replay, the workbench SHALL send the latest applied event id as `lastSeenEventId` in the AG-UI connect input.

The workbench SHALL tolerate at-least-once replay by ignoring already applied SSE event ids when possible and by keeping existing AG-UI reducer behavior safe for duplicate payloads.

When replay is unavailable or cursor recovery fails, the pane SHALL still process the fresh `STATE_SNAPSHOT` and later live events.

#### Scenario: Reconnect sends last seen event id
- **WHEN** a pane receives an AG-UI event frame with SSE id `abc123:thread-1:42`
- **AND WHEN** the pane reconnects to a gateway that advertises resumable replay
- **THEN** the connect request includes `lastSeenEventId = "abc123:thread-1:42"`

#### Scenario: Duplicate replay does not duplicate visible state
- **WHEN** a reconnect stream replays an event whose SSE id was already applied
- **THEN** the workbench ignores the duplicate frame when the id is known
- **AND THEN** the pane continues processing later replayed or live events

#### Scenario: Snapshot fallback remains usable
- **WHEN** a reconnect request cannot be replayed from the saved cursor
- **THEN** the pane processes the gateway's current `STATE_SNAPSHOT`
- **AND THEN** the pane remains connected for future live events

### Requirement: Manual direct AG-UI targets remain explicit and non-reconnecting by agent address
For manual targets, the workbench SHALL continue to use the configured label, AG-UI URL, and thread id directly.

Manual targets SHALL NOT perform passive-server agent-address resolution unless the user converts or retargets the pane to a discovered-agent target.

Manual targets MAY retry the same configured URL after transient stream failures, but they SHALL NOT infer an agent id, scan the registry, or resolve a replacement gateway URL.

#### Scenario: Manual URL stays direct
- **WHEN** a tester enters `http://127.0.0.1:8765/v1/ag-ui` as a manual target
- **THEN** the pane uses that URL directly for capabilities, connect, run, and detach requests
- **AND THEN** it does not query passive-server agent resolution

#### Scenario: Manual reconnect does not guess agent identity
- **WHEN** a manual target stream fails
- **THEN** the workbench does not infer an agent id from the URL
- **AND THEN** it does not scan or resolve the registry for a replacement gateway
