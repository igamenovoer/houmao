## ADDED Requirements

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
The workbench SHALL use a dockable pane layout where each agent pane can be added, removed, moved, and configured independently for one running Houmao agent.

#### Scenario: User can add multiple panes
- **WHEN** a developer clicks the add-pane control
- **THEN** the workbench creates a new docked agent pane with its own target configuration and event state

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

#### Scenario: Stream content is not persisted by default
- **WHEN** a pane receives prompts, messages, raw events, state snapshots, activity records, or graphics payloads
- **THEN** the workbench does not persist those stream contents to local storage by default

### Requirement: Deterministic browser E2E coverage
The repository SHALL include deterministic browser E2E coverage for the workbench using Bun-global Playwright and a fake AG-UI server or route fixture.

#### Scenario: E2E validates operator and multi-pane flow
- **WHEN** the workbench E2E smoke runs against a deterministic AG-UI fixture
- **THEN** it configures the operator panel, adds at least two agent panes, connects panes independently, submits at least one run, and verifies visible transcript or status evidence for each target

#### Scenario: E2E validates graphics and detach behavior
- **WHEN** the deterministic fixture emits a `houmao_render_graphic` sequence and the test closes or disconnects a pane
- **THEN** the test verifies visible graphic evidence
- **AND THEN** the test verifies the browser-side detach or abort path without expecting a Houmao interrupt request
