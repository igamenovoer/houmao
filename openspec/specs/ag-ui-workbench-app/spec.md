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

### Requirement: Docked multi-agent panes
The workbench SHALL use a dockable pane layout where each agent pane can be added, removed, moved within the main workbench, and configured independently for one running Houmao agent or watched AG-UI target.

Agent panes SHALL be presentation surfaces for target event state. They SHALL NOT be the only ownership boundary for a watched target's background AG-UI listener.

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

#### Scenario: Each pane presents its selected target independently
- **WHEN** two panes are configured with different AG-UI targets and both targets have event state
- **THEN** each pane presents only the cached and live events for its own target
- **AND THEN** events received by one target do not appear in the other pane's transcript, state view, or raw event list

#### Scenario: Pane close does not stop watched target listener
- **WHEN** a pane presenting a watched target is closed
- **THEN** the workbench removes that pane from the docked layout
- **AND THEN** the watched target listener remains active when the target is still marked watched
- **AND THEN** the workbench does not send any Houmao lifecycle stop, restart, shutdown, or interrupt request

#### Scenario: Explicit unwatch disconnects listener without controlling agent
- **WHEN** a tester explicitly unwatches or disconnects a watched target
- **THEN** the workbench aborts that target's active browser stream and performs explicit AG-UI connection cleanup when a connection id is available
- **AND THEN** the workbench does not send any Houmao lifecycle stop, restart, shutdown, or interrupt request

### Requirement: Direct AG-UI client and event reduction
The workbench SHALL include direct AG-UI client behavior for Houmao capabilities, connect, run, detach, SSE parsing, stream abort, raw event recording, and reduced display state.

For watched targets, the workbench SHALL route connect-stream events through the watched-target cache and reducer rather than storing them only in pane-local state.

Visible panes SHALL render the reduced state for their selected target from cached events plus live watcher updates.

Normal agent panes SHALL keep transcripts and rendered artifacts visible by default and SHALL expose state snapshots, activity/custom records, tool-call records, and raw event timelines through on-demand diagnostics instead of an always-visible diagnostics panel.

#### Scenario: Capabilities are fetched before interaction
- **WHEN** a pane target is configured
- **THEN** the workbench can request AG-UI capabilities for that target
- **AND THEN** the pane displays whether HTTP SSE, text input, state snapshots, generated graphics, frontend tool execution, state deltas, and multimodal input are reported as supported

#### Scenario: Connect attaches without prompt submission
- **WHEN** a user connects or watches a target without submitting a prompt
- **THEN** the workbench sends an AG-UI connect request rather than a run request
- **AND THEN** the target records state snapshot, activity, custom, text, tool-call, and error events received from that connection stream

#### Scenario: Run stream is reduced into visible state
- **WHEN** a run stream emits `RUN_STARTED`, text message events, state snapshot events, activity events, tool call events, custom events, and `RUN_FINISHED`
- **THEN** the pane shows run status and transcript messages in the main display
- **AND THEN** normal agent panes expose state snapshot content, activity/custom records, tool-call records, and the raw event timeline through on-demand diagnostics

#### Scenario: Cached connect stream is reduced into visible state
- **WHEN** a watched connect stream receives state snapshot events, activity events, tool call events, custom events, and errors
- **THEN** the workbench stores those events in the client cache
- **AND THEN** any pane for that target renders the reduced display state from those cached events

#### Scenario: Run error remains visible
- **WHEN** a target returns a pre-admission HTTP error or an admitted stream emits `RUN_ERROR`
- **THEN** the pane displays the error status and records enough raw event or response detail for debugging without crashing the workbench

#### Scenario: Message info opens scoped diagnostics
- **WHEN** a normal agent pane has at least one transcript message
- **AND WHEN** the user activates that message's info control
- **THEN** the pane opens a side inspector scoped to that message
- **AND THEN** the inspector shows deterministic diagnostics for the message and any related raw events, tool calls, activity/custom records, and current state snapshot evidence

### Requirement: Workbench run requests minimize agent-visible metadata
For normal agent pane prompt submissions, including operator-designated panes, the workbench SHALL submit AG-UI `RunAgentInput` requests with only protocol-required routing fields, the user message, an empty tools array, an empty state object, an empty forwarded props object, and at most one compact canvas context entry.

When a positive visible graphics surface size is available, the workbench SHALL include one context entry with `description` equal to `houmao.canvas_size_px.v1` and `value` equal to a compact JSON string containing integer `widthPx` and `heightPx` fields in CSS pixels.

When no positive visible graphics surface size is available, the workbench SHALL omit the canvas context entry rather than inventing a default size.

The workbench SHALL NOT duplicate pane id, pane kind, source labels, component schemas, CLI command recipes, agent identity, thread id, run id, delivery semantics, or safety guidance in `state`, `context`, or non-Houmao `forwardedProps` for normal prompt submissions.

The workbench MAY still use `forwardedProps.houmao` for explicit gateway-recognized runtime controls when a future caller intentionally requests those controls.

#### Scenario: Prompt run includes only compact canvas context
- **WHEN** an agent pane submits a text prompt and the visible graphics surface measures 640 by 520 CSS pixels
- **THEN** the submitted `RunAgentInput.context` contains exactly one Houmao presentation entry
- **AND THEN** that entry has `description` equal to `houmao.canvas_size_px.v1`
- **AND THEN** that entry has `value` equal to `{"widthPx":640,"heightPx":520}` or an equivalent compact JSON string with those integer fields

#### Scenario: Prompt run omits redundant pane metadata
- **WHEN** an agent pane submits a normal text prompt
- **THEN** the submitted `RunAgentInput.state` is an empty object
- **AND THEN** the submitted `RunAgentInput.forwardedProps` is an empty object
- **AND THEN** the submitted request does not include pane id, pane kind, source label, agent identity, thread id duplicate, or run id duplicate outside the standard AG-UI routing fields

#### Scenario: Prompt run keeps typed graphics out of declared tools
- **WHEN** an agent pane submits a normal text prompt intended to produce Houmao typed graphics
- **THEN** the submitted `RunAgentInput.tools` is an empty array
- **AND THEN** the request does not declare `houmao.chart.bar`, `houmao.chart.line`, `houmao.chart.pie`, `houmao.table`, `houmao.metric_grid`, or `houmao.dashboard` as frontend tools

#### Scenario: Missing surface size omits canvas context
- **WHEN** an agent pane submits a text prompt before a positive visible graphics surface size can be measured
- **THEN** the submitted `RunAgentInput.context` does not include `houmao.canvas_size_px.v1`
- **AND THEN** the workbench does not send guessed width or height values

### Requirement: Send-capable prompt editors submit with Shift+Enter
The workbench SHALL submit send-capable prompt editor contents when the focused editor receives `Shift+Enter`.

Send-capable prompt editors include normal agent pane prompt composers and Debug Agent editor panes that send text or JSON-like payloads through an adjacent Run or Send action.

The `Shift+Enter` shortcut SHALL use the same submission path as the editor's visible Run or Send button.

The shortcut SHALL NOT submit empty or whitespace-only prompt content.

Plain `Enter` in textarea-based send-capable editors SHALL remain available for multiline editing and SHALL NOT submit the prompt.

Read-only text areas, target configuration fields, search fields, filters, tmux terminal input, and non-send editor controls SHALL NOT submit prompt content through this shortcut.

#### Scenario: Agent prompt submits with Shift+Enter
- **WHEN** a user focuses a normal agent pane prompt editor and enters non-empty prompt text
- **AND WHEN** the user presses `Shift+Enter`
- **THEN** the workbench submits the same AG-UI run request that the pane Run button would submit
- **AND THEN** the prompt editor is cleared according to the existing Run button behavior

#### Scenario: Debug Agent editor sends with Shift+Enter
- **WHEN** a user focuses a Debug Agent editor containing a valid sendable payload
- **AND WHEN** the user presses `Shift+Enter`
- **THEN** the workbench sends the same debug publish request that the Send button would send
- **AND THEN** the Debug Agent display updates according to the existing Send button behavior

#### Scenario: Plain Enter keeps multiline editing
- **WHEN** a user focuses a textarea-based send-capable prompt editor
- **AND WHEN** the user presses `Enter` without `Shift`
- **THEN** the editor inserts or preserves a newline according to normal textarea behavior
- **AND THEN** the workbench does not submit the prompt

#### Scenario: Empty prompt shortcut is ignored
- **WHEN** a user focuses a send-capable prompt editor whose content is empty or whitespace-only
- **AND WHEN** the user presses `Shift+Enter`
- **THEN** the workbench does not send an AG-UI run request or debug publish request
- **AND THEN** no visible error is introduced solely because the empty shortcut was pressed

### Requirement: Workbench connect requests do not send redundant GUI metadata
For AG-UI connect requests that attach or watch a target without submitting prompt work, the workbench SHALL avoid sending pane/source metadata through agent-visible fields.

Connect requests SHALL use empty `state`, empty `context`, empty `tools`, and empty non-Houmao `forwardedProps` unless a future gateway-recognized control explicitly requires otherwise.

#### Scenario: Connect request is metadata-minimal
- **WHEN** an operator, agent, watched-target, or Debug Agent pane opens an AG-UI connect stream
- **THEN** the submitted connect input has empty `state`, `context`, `tools`, and `forwardedProps`
- **AND THEN** it does not include pane id, pane kind, or source label in the request body

### Requirement: Houmao graphics rendering
The workbench SHALL render `houmao_render_graphic` AG-UI tool calls from reduced event state.

#### Scenario: SVG graphic renders visibly
- **WHEN** a stream emits a complete `houmao_render_graphic` tool-call sequence with `format` set to `svg`
- **THEN** the pane renders the graphic title, alt text or title fallback, and sanitized SVG content in the transcript or tool-call area

#### Scenario: Unsupported graphic format degrades visibly
- **WHEN** a stream emits a `houmao_render_graphic` payload with an unsupported or unsafe format
- **THEN** the pane shows a deterministic unsupported-format message and preserves the raw tool-call event details for inspection

### Requirement: Agent pane can clear visible AG-UI canvas
The workbench SHALL provide a clear-canvas control on agent panes.

The clear-canvas control SHALL clear the pane's client-side AG-UI display evidence, including transcript messages, rendered graphics/tool calls, state snapshot, activity/custom records, raw timeline entries, and visible errors.

The clear-canvas control SHALL preserve target configuration, prompt text, active AG-UI connections, watcher reconnect behavior, gateway state, and managed Houmao agent lifecycle.

The clear-canvas control SHALL NOT send detach, stop, restart, shutdown, interrupt, or agent-memory-clear requests.

#### Scenario: Clear removes rendered graphics from agent pane
- **WHEN** an agent pane displays a rendered Houmao graphic from AG-UI events
- **AND WHEN** the tester activates the clear-canvas control
- **THEN** the rendered graphic is removed from the agent pane
- **AND THEN** the pane no longer shows the prior transcript, tool-call record, state snapshot, raw event evidence, or visible error evidence for that cleared display state

#### Scenario: Clear preserves connection and target metadata
- **WHEN** an agent pane is connected to a target and has prompt text or target metadata configured
- **AND WHEN** the tester activates the clear-canvas control
- **THEN** the pane remains configured for the same target
- **AND THEN** the prompt text remains unchanged
- **AND THEN** the workbench does not send an AG-UI detach request or any Houmao lifecycle command

#### Scenario: Future events render after clear
- **WHEN** an agent pane canvas has been cleared
- **AND WHEN** the same connected target later emits new AG-UI transcript, graphic, state, activity, custom, or error events
- **THEN** the pane renders those new events from an empty display baseline

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
The workbench SHALL persist layout and non-sensitive configuration in localStorage or an equivalent browser configuration store.

The workbench SHALL persist AG-UI stream events only in the client-owned event cache for watched targets.

The workbench SHALL NOT store stream content in localStorage by default.

The workbench SHALL NOT persist discovered-agent list responses, gateway-status response bodies, prompt text, AG-UI request bodies, forwarded props, mailbox content, memory content, raw terminal content, credentials, cookies, bearer tokens, or authorization headers.

#### Scenario: Layout and target metadata persist
- **WHEN** a developer creates panes, moves them, assigns labels, configures target URLs, and watches targets
- **THEN** the workbench can restore the pane layout, target metadata, and watched-target metadata after a browser reload
- **AND THEN** restored layout state contains only docked grid groups, not floating groups or popout groups

#### Scenario: Watched stream content persists only in client event cache
- **WHEN** a watched target receives messages, raw events, state snapshots, activity records, or graphics payloads
- **THEN** the workbench stores those received stream events in the client-owned event cache
- **AND THEN** the workbench does not store those stream contents in localStorage

#### Scenario: Unwatched pane stream content is not persisted by default
- **WHEN** an unwatched pane receives prompts, messages, raw events, state snapshots, activity records, or graphics payloads
- **THEN** the workbench does not persist those stream contents to localStorage by default
- **AND THEN** the workbench persists them in the client event cache only after the target is watched

### Requirement: Deterministic browser E2E coverage
The repository SHALL include deterministic browser E2E coverage for the workbench using Bun-global Playwright and a fake AG-UI server or route fixture.

#### Scenario: E2E validates multi-pane flow
- **WHEN** the workbench E2E smoke runs against a deterministic AG-UI fixture
- **THEN** it adds at least two agent panes, moves a pane into an in-app split, connects panes independently, submits at least one run, and verifies visible transcript or status evidence for each target

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

### Requirement: Workbench has no dedicated operator tab
The workbench SHALL NOT create a dedicated `operator` pane by default.

The workbench SHALL NOT treat `operator` as a first-class pane kind for new panes.

An empty workbench MAY show the normal empty workspace state until the user opens an agent pane, Debug Agent pane, or tmux tab.

Legacy persisted `operator` pane records SHALL NOT force the dedicated Operator tab to reappear.

#### Scenario: Fresh workbench does not create operator tab
- **WHEN** a developer opens a fresh workbench with no saved docked layout
- **THEN** the workbench does not create an Operator tab
- **AND THEN** the developer can open agent, Debug Agent, or tmux tabs from explicit workbench controls

#### Scenario: Empty workspace does not recreate operator tab
- **WHEN** a developer closes the last visible pane in the workbench
- **THEN** the workbench does not automatically create an Operator tab
- **AND THEN** the workbench remains usable through explicit tab-opening controls

#### Scenario: Legacy operator pane does not reappear
- **WHEN** localStorage contains a legacy persisted operator pane record
- **AND WHEN** the workbench loads the saved state
- **THEN** the workbench does not force a dedicated Operator tab to appear

### Requirement: Operator role is an agent-pane designation
The workbench SHALL allow the user to designate at most one ordinary Houmao agent pane as the operator pane.

The operator designation SHALL be UI metadata only.

The operator designation SHALL NOT change AG-UI request bodies, target resolution, watched-target behavior, gateway routing, prompt delivery, event caching, tmux attachment, or managed-agent lifecycle behavior.

Only panes targeting a discovered Houmao agent SHALL be eligible for the operator designation.

If the designated pane is closed or retargeted away from a discovered Houmao agent, the workbench SHALL clear the operator designation.

#### Scenario: User marks a Houmao agent pane as operator
- **WHEN** a developer has an ordinary agent pane targeting a discovered Houmao agent
- **AND WHEN** the developer activates the operator-designation control for that pane
- **THEN** the workbench marks that pane as the operator pane
- **AND THEN** no other pane is marked as operator

#### Scenario: Operator marker does not change AG-UI requests
- **WHEN** an operator-marked agent pane submits an AG-UI run or opens an AG-UI connect stream
- **THEN** the workbench sends the same protocol-minimal request shape used by an ordinary agent pane
- **AND THEN** the request does not include an operator role, operator flag, pane kind, or operator-specific forwarded props

#### Scenario: Operator marker clears when pane becomes ineligible
- **WHEN** a pane is marked as operator
- **AND WHEN** the pane is closed or retargeted to a manual or non-discovered target
- **THEN** the workbench clears the operator designation

### Requirement: Workbench supports docked tmux tabs
The workbench SHALL provide a docked `tmux` pane kind for direct attachment to local tmux sessions.

Tmux tabs SHALL use the same Dockview workspace as agent and Debug Agent panes.

Tmux tabs SHALL be distinct from AG-UI panes and SHALL NOT send AG-UI connect, run, detach, stop, restart, shutdown, interrupt, or agent-memory-clear requests as part of tmux attachment.

#### Scenario: User can open a tmux tab
- **WHEN** a developer activates the workbench control for opening a tmux tab
- **THEN** the workbench creates a docked pane with kind `tmux`
- **AND THEN** the pane shows a tmux session picker when no session is attached

#### Scenario: Tmux tab stays inside docked workspace
- **WHEN** a developer moves a tmux tab within the workbench
- **THEN** the pane can be moved into an in-app tab group or split
- **AND THEN** the pane remains inside the main workbench browser page without Dockview floating groups or popout windows

#### Scenario: Tmux tab does not use AG-UI lifecycle
- **WHEN** a developer opens, attaches, detaches, or closes a tmux tab
- **THEN** the workbench does not send AG-UI run, AG-UI detach, Houmao stop, Houmao restart, Houmao shutdown, Houmao interrupt, or agent-memory-clear requests

### Requirement: Workbench lists and searches tmux sessions
The workbench SHALL provide a local tmux session picker for tmux tabs.

The picker SHALL be presented as a top-placed searchable combobox/dropdown so the tmux terminal can use the pane's full content width.

The picker SHALL list local tmux sessions available to the host running the workbench development server when the user opens the dropdown or explicitly refreshes the picker.

The picker SHALL support quick fuzzy search using Fuse.js while the user types in the combobox input.

The searchable fields SHALL include tmux session name and matched Houmao agent metadata when available, including agent name, agent id, tool, backend, and generation id.

The picker SHALL provide a checkbox filter that shows only tmux sessions matched to Houmao managed agents.

The workbench SHALL NOT require a persistent left-side tmux session list for normal tmux attachment.

#### Scenario: Picker lists local tmux sessions on open
- **WHEN** tmux is available and the host has local tmux sessions
- **AND WHEN** the user opens the tmux session combobox
- **THEN** the tmux picker refreshes inventory and displays matching sessions with at least session name, window count, attached status, and created time

#### Scenario: Picker degrades when tmux is unavailable
- **WHEN** tmux is unavailable on the host running the workbench development server
- **AND WHEN** the user opens the tmux session combobox
- **THEN** the tmux picker shows a deterministic unavailable or empty state
- **AND THEN** the workbench does not crash

#### Scenario: Search matches tmux and Houmao fields
- **WHEN** a developer types a search query matching a session name or matched Houmao agent metadata into the combobox
- **THEN** the tmux picker filters the visible dropdown rows using Fuse.js fuzzy search
- **AND THEN** non-matching sessions are hidden while the query is active

#### Scenario: Houmao-only filter hides non-agent sessions
- **WHEN** the tmux picker has the Houmao-only checkbox enabled
- **THEN** the picker shows only tmux sessions whose session name matches a discovered Houmao agent `tmux_session_name`
- **AND THEN** tmux sessions without a matched Houmao agent are hidden

#### Scenario: Houmao-only filter handles discovery outage
- **WHEN** passive-server agent discovery is unavailable
- **AND WHEN** the Houmao-only checkbox is enabled
- **THEN** the picker shows a deterministic no-matched-Houmao-sessions or discovery-error state
- **AND THEN** disabling the checkbox still allows raw tmux sessions to be listed when tmux itself is available

#### Scenario: Selecting dropdown row attaches session
- **WHEN** a developer selects a tmux session row from the combobox dropdown
- **THEN** the tmux tab attaches to that selected session using the currently selected read-only/read-write mode
- **AND THEN** the dropdown closes and the full-width terminal remains available for session output

### Requirement: Tmux tabs attach read-write or read-only
Tmux tabs SHALL attach to one selected local tmux session.

Read-write attachment SHALL be the default mode.

Read-only attachment SHALL be available through an explicit checkbox or equivalent binary control before attachment.

Read-only mode SHALL be enforced by both the browser terminal and the host tmux bridge.

#### Scenario: Default attachment is read-write
- **WHEN** a developer selects a tmux session and attaches without enabling read-only mode
- **THEN** the tmux tab attaches in read-write mode
- **AND THEN** keyboard input in the terminal is forwarded to the attached tmux session

#### Scenario: Read-only attachment does not forward input
- **WHEN** a developer enables read-only mode and attaches to a tmux session
- **THEN** the tmux tab displays terminal output from the session
- **AND THEN** keyboard input is not forwarded to the attached tmux session
- **AND THEN** crafted browser input messages for that read-only attachment are rejected or ignored by the host tmux bridge

#### Scenario: Attachment failure is visible
- **WHEN** the selected tmux session disappears before or during attachment
- **THEN** the tmux tab shows a deterministic attachment error
- **AND THEN** the rest of the workbench remains usable

### Requirement: Tmux tab close is browser-detach only
Closing or disconnecting a tmux tab SHALL close only the browser attachment to the tmux session.

The host tmux bridge SHALL clean up the spawned browser-client attach process for that tab.

Closing or disconnecting a tmux tab SHALL NOT kill the tmux session, detach unrelated tmux clients, mutate the shared registry, or control the managed Houmao agent lifecycle.

#### Scenario: Closing tab keeps tmux session alive
- **WHEN** a developer closes a tmux tab attached to a tmux session
- **THEN** the workbench closes the tab's browser attachment
- **AND THEN** the underlying tmux session remains alive

#### Scenario: Closing tab does not detach other clients
- **WHEN** a tmux session has another tmux client outside the workbench
- **AND WHEN** a developer closes the workbench tmux tab for that session
- **THEN** the other tmux client remains attached

#### Scenario: Closing Houmao agent tmux tab does not control agent
- **WHEN** a tmux tab is attached to a tmux session matched to a Houmao managed agent
- **AND WHEN** the developer closes or disconnects the tmux tab
- **THEN** the workbench does not stop, restart, shut down, interrupt, or clear memory for the matched Houmao agent
- **AND THEN** the workbench does not mutate the agent's shared-registry record

### Requirement: Tmux terminal content is not persisted
The workbench SHALL persist tmux tab layout and non-sensitive tmux tab configuration in the same browser configuration boundary as other pane metadata.

The workbench SHALL NOT persist raw tmux terminal output, terminal input, terminal scrollback, WebSocket payloads, credentials, cookies, bearer tokens, or authorization headers in localStorage or IndexedDB.

Restored tmux tab metadata MAY remember the selected session name and attachment mode, but restored visible terminal scrollback SHALL start from a fresh attachment stream.

#### Scenario: Tmux pane metadata can persist
- **WHEN** a developer creates a tmux tab, selects a session, chooses an attachment mode, and reloads the workbench
- **THEN** the workbench may restore the docked tmux pane and non-sensitive selected-session metadata
- **AND THEN** restored layout state contains only docked grid groups, not floating groups or popout groups

#### Scenario: Terminal bytes are not stored in browser persistence
- **WHEN** a tmux tab receives terminal output or forwards read-write terminal input
- **THEN** the workbench does not write that terminal content to localStorage
- **AND THEN** the workbench does not write that terminal content to the AG-UI client event cache

#### Scenario: Reload starts with fresh terminal evidence
- **WHEN** a tmux tab is restored after page reload
- **THEN** the restored visible terminal scrollback is not replayed from browser persistence
- **AND THEN** any visible terminal content comes from a new live attachment stream after attachment

### Requirement: Workbench tests cover tmux tabs
The repository SHALL include deterministic browser coverage for tmux tab behavior.

The coverage SHALL verify tmux session listing, Fuse-powered search, Houmao-only filtering, read-write attachment, read-only input suppression, close lifecycle boundaries, and persistence boundaries.

#### Scenario: E2E validates tmux picker
- **WHEN** the workbench E2E suite runs with a deterministic tmux bridge fixture
- **THEN** the test verifies that the tmux picker lists sessions
- **AND THEN** the test verifies search and Houmao-only filtering behavior

#### Scenario: E2E validates read-only and read-write attachment
- **WHEN** the workbench E2E suite attaches tmux tabs in read-write and read-only modes
- **THEN** the read-write tab forwards terminal input to the fixture
- **AND THEN** the read-only tab suppresses or rejects terminal input

#### Scenario: E2E validates close and persistence boundaries
- **WHEN** the workbench E2E suite closes an attached tmux tab
- **THEN** the test verifies the fixture tmux session remains alive
- **AND THEN** the test verifies no lifecycle-control request was sent
- **AND THEN** the test verifies browser persistence does not contain terminal content

#### Scenario: E2E validates no dedicated operator tab
- **WHEN** the workbench E2E suite opens a fresh workbench
- **THEN** the test verifies no dedicated Operator tab is created by default
- **AND THEN** the test verifies a Houmao agent pane can be marked as operator without changing AG-UI request bodies

### Requirement: Agent panes expose explicit active-thread controls
The workbench SHALL provide an active-thread control or marker on each eligible Houmao agent pane.

The control SHALL be eligible only when the pane targets a discovered Houmao agent gateway that supports the Houmao active-thread extension.

The active-thread control SHALL show an inactive gray state when the pane's thread is not the gateway active thread.

The active-thread control SHALL show an active green state when the pane's thread matches the gateway active thread.

The active-thread control SHALL show a deterministic unavailable or error state when the workbench cannot read active-thread status from a gateway that previously appeared to support active-thread.

The active-thread control SHALL show a deterministic unsupported state, or be disabled with unsupported text, when the gateway responds as if `/active-thread` is not implemented.

The active-thread presentation SHALL NOT label a pane inactive merely because the gateway does not support the active-thread extension.

Activating the control from an inactive eligible pane SHALL set the gateway active-thread to that pane's current thread id.

#### Scenario: User marks a pane as active thread
- **WHEN** a developer has an eligible Houmao agent pane whose active-thread control is gray
- **AND WHEN** the developer activates the control
- **THEN** the workbench sends the gateway an active-thread update for that pane's current thread id
- **AND THEN** the pane's control becomes green after the gateway reports that thread as active

#### Scenario: Active marker moves between panes
- **WHEN** two eligible panes target the same gateway with different thread ids
- **AND WHEN** the developer marks the second pane active
- **THEN** the second pane shows the active green state
- **AND THEN** the first pane shows the inactive gray state after the next active-thread status update

#### Scenario: Unsupported gateway is not shown as inactive
- **WHEN** a discovered agent pane targets a live gateway whose `/active-thread` route returns `404` or `405`
- **THEN** the pane shows active-thread as unsupported or disabled
- **AND THEN** the pane does not show `Inactive thread` with an active-thread error for that unsupported extension

### Requirement: Connect marks eligible pane active automatically
When a user connects an eligible discovered Houmao agent pane, the workbench SHALL set that pane's current thread as the gateway active-thread with source `gui_connect`.

Background watchers, passive reconnects, hidden panes, and client event-cache listeners SHALL NOT set active-thread merely because they open or reopen an AG-UI stream.

#### Scenario: Connect auto-activates pane thread
- **WHEN** a developer clicks Connect on an eligible discovered Houmao agent pane
- **THEN** the workbench sets the gateway active-thread to that pane's current thread id
- **AND THEN** the normal AG-UI connect request remains metadata-minimal

#### Scenario: Background watcher does not steal active thread
- **WHEN** one pane is active for a gateway
- **AND WHEN** a watched target for another thread on the same gateway reconnects in the background
- **THEN** the gateway active-thread remains the foreground pane's active thread

### Requirement: Active-thread status is polled and reflected in pane UI
The workbench SHALL poll each interested gateway's active-thread status periodically when that gateway is eligible and not known to be unsupported.

The default poll interval SHALL be 1 second.

The workbench SHALL update eligible pane active-thread presentation from the polled gateway state.

The polling implementation SHALL be shared per gateway rather than duplicated per pane.

The workbench SHALL stop active-thread polling for a gateway after the gateway is classified as unsupported until the pane target or gateway key changes.

The workbench SHALL avoid UI flicker caused by overlapping or aborting active-thread polls under ordinary slow-response conditions.

#### Scenario: External active-thread change updates pane controls
- **WHEN** an external caller changes the gateway active-thread
- **THEN** the workbench reflects the new active-thread state in eligible pane controls after the next poll

#### Scenario: Poll failure is visible without disconnecting pane stream
- **WHEN** active-thread polling fails for a gateway that is not known to be unsupported
- **THEN** panes for that gateway show a deterministic unavailable or error state for active-thread
- **AND THEN** existing AG-UI streams for those panes remain connected unless they fail independently

#### Scenario: Unsupported active-thread extension stops polling
- **WHEN** active-thread polling receives a deterministic unsupported-route response such as `404` or `405`
- **THEN** the workbench marks active-thread unsupported for that gateway
- **AND THEN** the workbench stops scheduling active-thread polls for that gateway until the target or gateway key changes

#### Scenario: Slow poll does not flash error
- **WHEN** an active-thread poll takes longer than the default poll interval but eventually succeeds
- **THEN** the pane does not flash an active-thread error caused only by the next scheduled poll tick
- **AND THEN** the pane updates from the successful poll result

### Requirement: Inactive panes still render explicitly addressed AG-UI events
The workbench SHALL treat active-thread as a default destination marker only.

Inactive panes SHALL continue to receive, reduce, cache when watched, and render AG-UI events that are explicitly addressed to their target thread.

Inactive panes SHALL NOT be hidden, disconnected, cleared, or prevented from rendering merely because another pane is active.

#### Scenario: Inactive pane renders explicit publish
- **WHEN** pane alpha is the active thread for a gateway
- **AND WHEN** pane beta is connected to the same gateway with thread id `beta-thread`
- **AND WHEN** an agent publishes AG-UI events with explicit `threadId = "beta-thread"`
- **THEN** pane beta receives and renders those events
- **AND THEN** pane alpha remains the gateway active thread

### Requirement: Active-thread clear is conditional when pane ownership is stale
When a pane closes or retargets away, the workbench SHALL clear gateway active-thread only if the gateway still reports the pane's old thread as active.

The workbench SHALL NOT clear a newer active-thread value set by another pane.

#### Scenario: Closing stale pane does not clear newer active thread
- **WHEN** pane alpha was active
- **AND WHEN** pane beta becomes active for the same gateway
- **AND WHEN** pane alpha closes
- **THEN** the workbench does not clear pane beta's active-thread state

### Requirement: Agent panes delegate AG-UI lifecycles to runtime
Agent panes SHALL delegate long-lived AG-UI lifecycle ownership to the workbench runtime.

Agent panes SHALL dispatch runtime actions for target changes, connect/watch requests, run requests, stream cancellation, clear-canvas requests, and pane disposal.

Agent panes SHALL keep UI-local concerns such as prompt editor state, target form editing, measured canvas size, and rendered DOM outside the runtime lifecycle effects.

Agent panes SHALL NOT keep component-local reconnect timers, stream abort refs, connection ids, or duplicated connect/run status after the equivalent workflow has moved into the runtime.

#### Scenario: Agent pane connect uses runtime action
- **WHEN** a user connects an agent pane to a target
- **THEN** the pane dispatches a runtime connect or watch action for that target
- **AND THEN** runtime effects own passive resolution, AG-UI connect stream startup, reconnect behavior, and detach cleanup

#### Scenario: Agent pane run uses runtime action
- **WHEN** a user submits a prompt from an agent pane
- **THEN** the pane dispatches a runtime run action containing the submitted message and compact canvas-size context when available
- **AND THEN** runtime effects own the AG-UI run stream and reduce the received events into pane-visible state

#### Scenario: Pane close cancels pane-owned AG-UI streams
- **WHEN** an agent pane with a live pane-owned run stream closes
- **THEN** the pane dispatches disposal to the runtime
- **AND THEN** runtime effects abort that pane-owned stream without stopping watched-target listeners still required by storage state

### Requirement: Tmux panes delegate tmux lifecycles to runtime
Tmux panes SHALL delegate tmux status refresh, tmux session refresh, discovered Houmao agent refresh, tmux attach WebSocket lifecycle, tmux input, tmux resize, and tmux detach to the workbench runtime.

Tmux panes SHALL keep xterm `Terminal`, `FitAddon`, DOM refs, layout measurement, and direct terminal rendering outside reduced runtime state.

Tmux panes SHALL register and unregister an ephemeral terminal output sink for the active runtime attachment.

#### Scenario: Tmux picker refresh uses runtime selector
- **WHEN** a user opens or refreshes the tmux session combobox
- **THEN** the pane dispatches a runtime refresh action
- **AND THEN** the pane renders tmux status, session list, discovered-agent list, loading state, and errors from runtime selectors

#### Scenario: Tmux attach keeps terminal DOM local
- **WHEN** a user attaches to a tmux session
- **THEN** the pane creates or reuses its xterm DOM objects locally
- **AND THEN** runtime effects own the WebSocket and send terminal output to the pane through the registered sink

### Requirement: Runtime migration preserves pane-visible behavior
The runtime lifecycle refactor SHALL preserve existing workbench pane behavior unless this change explicitly changes ownership or presentation.

Agent panes SHALL continue to render transcripts, Houmao graphics, typed components, visible errors, and active-thread status.

Normal agent panes SHALL expose state snapshots, activity, custom events, raw event timelines, and per-message tool-call evidence through the on-demand message diagnostics inspector.

Tmux panes SHALL continue to search/filter sessions, filter Houmao agent sessions, attach read-write by default, support read-only attachment, send input only for read-write attachment, and show attach status through the top session combobox and full-width terminal layout.

#### Scenario: Graphics remain visible after runtime migration
- **WHEN** an AG-UI stream emits a valid Houmao chart or graphic event sequence
- **THEN** the agent pane renders the graphic from reduced runtime event state
- **AND THEN** the migration does not require a gateway protocol change

#### Scenario: Read-only tmux attach suppresses input
- **WHEN** a tmux pane is attached in read-only mode
- **AND WHEN** the user types in the terminal
- **THEN** the pane does not dispatch tmux input to the runtime attachment
- **AND THEN** output received from the tmux session remains visible

#### Scenario: Normal agent diagnostics are available on demand
- **WHEN** a normal agent pane receives state snapshots, activity records, tool calls, and raw events
- **AND WHEN** the user opens a transcript message info inspector
- **THEN** the pane shows diagnostics related to the selected message without requiring the default transcript layout to reserve a permanent diagnostics column

### Requirement: Tmux tabs fill available workspace height
Tmux tabs SHALL make the terminal attachment area consume the remaining vertical space inside the Dockview panel after fixed tmux controls are laid out.

Tmux tabs SHALL make the terminal attachment area consume the pane's available content width instead of reserving a permanent side column for tmux sessions.

Tmux tabs SHALL refit the visible xterm terminal when the browser viewport, Dockview panel, or terminal host size changes.

Session discovery controls and dropdown lists SHALL remain usable without causing the attached terminal to shrink below the available panel area.

#### Scenario: Browser resize refits tmux terminal
- **WHEN** a tmux tab is attached to a session
- **AND WHEN** the browser window or Dockview panel is resized
- **THEN** the tmux tab refits the terminal to the new visible terminal host size
- **AND THEN** the runtime receives the updated terminal columns and rows for the active attachment

#### Scenario: Tmux terminal consumes remaining panel height and width
- **WHEN** a developer opens a tmux tab in a tall or wide Dockview panel
- **THEN** the terminal attachment area expands to use the vertical space not needed by the header, picker, and fixed controls
- **AND THEN** the terminal attachment area expands to use the pane width not needed by fixed controls
- **AND THEN** the tmux tab does not leave an unused side list or footer area that prevents the terminal from filling the pane

### Requirement: Tmux session lists remove dead sessions
The workbench SHALL remove a tmux session from visible tmux session picker results after the host tmux bridge reports that the session no longer exists.

The workbench SHALL refresh tmux session inventory after a tmux attachment exits or disconnects, when the user opens the session combobox, and when the user explicitly refreshes the picker.

If an attached session exits, the tmux tab SHALL mark the attachment disconnected, preserve any terminal output already written to the xterm instance, and update the next shown session list without sending a Houmao agent lifecycle command or tmux kill command.

#### Scenario: Session closed from attached terminal disappears from list
- **WHEN** a user is attached to tmux session `HOUMAO-alpha` in a workbench tmux tab
- **AND WHEN** the user exits the session from inside the terminal
- **THEN** the tab marks the attachment disconnected
- **AND THEN** the next tmux session list shown by the workbench does not include `HOUMAO-alpha`
- **AND THEN** the workbench does not send any Houmao stop, restart, shutdown, interrupt, launch, registry cleanup, or prompt-control request

#### Scenario: Externally killed tmux session disappears from list
- **WHEN** the tmux session picker previously listed tmux session `HOUMAO-beta`
- **AND WHEN** that session is killed outside the browser
- **AND WHEN** the user next opens or refreshes the tmux session picker
- **THEN** the workbench removes `HOUMAO-beta` from the visible session list

### Requirement: Toolbar agent creation is consolidated into Agents
The workbench SHALL expose one top-level Agents control for discovered-agent selection, watch actions, retargeting, and blank agent-pane creation.

The workbench SHALL NOT expose a separate top-level `Agent Pane` toolbar control when blank agent-pane creation is available through the Agents picker.

#### Scenario: Top-level toolbar has a single Agents entry point
- **WHEN** a developer views the workbench top toolbar
- **THEN** the toolbar shows the Agents entry point
- **AND THEN** it does not show a separate `Agent Pane` entry point for creating a blank agent pane

#### Scenario: Blank agent pane is created from Agents picker
- **WHEN** a developer opens the Agents picker from the toolbar
- **AND WHEN** the developer activates the picker New action
- **THEN** the workbench creates a new docked blank agent pane with manual target configuration
- **AND THEN** the picker row actions for discovered agents remain available

### Requirement: Workbench tests cover tmux and Agents UX updates
The deterministic workbench browser coverage SHALL exercise tmux terminal resize, tmux dead-session removal, Agents picker auto-refresh, and blank agent-pane creation from the Agents picker.

#### Scenario: E2E validates responsive tmux tab
- **WHEN** the workbench E2E suite attaches a tmux tab through the deterministic tmux bridge fixture
- **AND WHEN** the test resizes the browser viewport or Dockview panel
- **THEN** the test verifies that the terminal area remains visible and reports updated dimensions

#### Scenario: E2E validates dead-session removal
- **WHEN** the workbench E2E suite lists a fixture tmux session
- **AND WHEN** the fixture session exits or is removed
- **THEN** the test verifies that the workbench removes that session from the visible list

#### Scenario: E2E validates consolidated Agents creation
- **WHEN** the workbench E2E suite opens the Agents picker from the toolbar
- **THEN** the test verifies discovery refresh evidence
- **AND THEN** the test creates a blank manual agent pane through the picker New action
