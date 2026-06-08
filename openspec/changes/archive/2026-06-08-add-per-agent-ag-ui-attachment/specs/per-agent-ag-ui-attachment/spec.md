## ADDED Requirements

### Requirement: Per-agent gateway exposes an AG-UI attachment namespace

The live per-agent gateway SHALL expose AG-UI routes under `/v1/ag-ui` without changing existing Houmao gateway routes.

The gateway SHALL expose:

- `GET /v1/ag-ui/capabilities`
- `POST /v1/ag-ui/connect`
- `POST /v1/ag-ui/runs`
- `DELETE /v1/ag-ui/connections/{connection_id}`

The AG-UI namespace SHALL be served by the same live per-agent gateway runtime that serves `/v1/status` for the target agent.

#### Scenario: AG-UI routes are registered on the per-agent gateway

- **WHEN** the per-agent gateway FastAPI app is created
- **THEN** the app route inventory includes `GET /v1/ag-ui/capabilities`
- **AND THEN** the app route inventory includes `POST /v1/ag-ui/connect`
- **AND THEN** the app route inventory includes `POST /v1/ag-ui/runs`
- **AND THEN** the app route inventory includes `DELETE /v1/ag-ui/connections/{connection_id}`

#### Scenario: Existing gateway routes remain available

- **WHEN** the per-agent gateway FastAPI app is created with AG-UI routes enabled
- **THEN** existing routes such as `GET /v1/status` remain registered
- **AND THEN** AG-UI route registration does not replace or rename existing Houmao gateway routes

### Requirement: AG-UI capabilities report conservative attachment support

The gateway SHALL provide `GET /v1/ag-ui/capabilities` so GUI clients can discover supported AG-UI behavior before connecting.

The capabilities response SHALL report HTTP SSE support, GUI connect support, text input parsing support, and state snapshot support as enabled.

The capabilities response SHALL report task-run submission, state delta support, frontend tool execution, generated graphics, Open Generative UI, and multimodal input as disabled for this milestone.

The capabilities response SHALL identify that GUI lifecycle does not manage the Houmao agent lifecycle.

#### Scenario: Capabilities are conservative before run streaming exists

- **WHEN** a caller requests `GET /v1/ag-ui/capabilities`
- **THEN** the response reports HTTP SSE support as enabled
- **AND THEN** the response reports GUI connect support as enabled
- **AND THEN** the response reports state snapshot support as enabled
- **AND THEN** the response reports task-run submission as disabled
- **AND THEN** the response reports generated graphics as disabled
- **AND THEN** the response reports frontend tool execution as disabled

#### Scenario: Capabilities state that GUI does not own agent lifecycle

- **WHEN** a caller requests `GET /v1/ag-ui/capabilities`
- **THEN** the response contains Houmao metadata indicating that the GUI does not manage the agent lifecycle

### Requirement: AG-UI request parsing and SSE encoding follow the protocol wire shape

The AG-UI adapter SHALL accept AG-UI camelCase request fields for connect input, including `threadId`, `runId`, `parentRunId`, and `forwardedProps`.

The AG-UI SSE encoder SHALL emit text/event-stream frames in the form `data: <json>\n\n`.

Encoded event JSON SHALL use camelCase field names and SHALL omit null optional fields.

#### Scenario: Connect input accepts camelCase AG-UI fields

- **WHEN** a caller submits AG-UI connect input containing `threadId`, `runId`, `parentRunId`, and `forwardedProps`
- **THEN** the gateway parses the request successfully
- **AND THEN** the parsed values preserve the caller-provided thread, run, parent-run, and forwarded-props values

#### Scenario: SSE encoder emits AG-UI JSON frames

- **WHEN** the gateway encodes an AG-UI state snapshot event
- **THEN** the encoded bytes start with `data: `
- **AND THEN** the encoded bytes end with a double newline
- **AND THEN** the event JSON uses camelCase field names
- **AND THEN** optional null fields are absent from the event JSON

### Requirement: Connect attaches a GUI stream without submitting work

`POST /v1/ag-ui/connect` SHALL create a GUI attachment connection for the existing Houmao agent and return an AG-UI SSE stream.

The connect stream SHALL emit an initial AG-UI `STATE_SNAPSHOT` describing sanitized current Houmao gateway status for that agent.

The connect handler SHALL NOT submit a prompt, create a gateway request, start a task run, stop the agent, interrupt the agent, restart the agent, or shut down the agent.

The connect handler SHALL accept an optional `lastSeenEventId` field, but this milestone SHALL guarantee replay only of the current sanitized state snapshot.

#### Scenario: Connect emits a state snapshot

- **WHEN** a caller posts valid AG-UI connect input to `POST /v1/ag-ui/connect`
- **THEN** the response content type is `text/event-stream`
- **AND THEN** the first AG-UI data event is a `STATE_SNAPSHOT`
- **AND THEN** the snapshot identifies the Houmao connection and current gateway status using a namespaced Houmao state object

#### Scenario: Connect does not submit prompt work

- **WHEN** a caller posts valid AG-UI connect input to `POST /v1/ag-ui/connect`
- **THEN** the gateway does not call prompt-control submission
- **AND THEN** the gateway does not create a queued gateway request
- **AND THEN** the gateway does not emit `RUN_STARTED`

#### Scenario: Connect accepts last seen event id without claiming historical replay

- **WHEN** a caller posts valid AG-UI connect input with `lastSeenEventId`
- **THEN** the gateway accepts the field
- **AND THEN** the gateway emits at least the current sanitized state snapshot
- **AND THEN** the gateway does not claim that full historical replay is supported in capabilities

### Requirement: AG-UI state snapshots expose only safe Houmao status

The AG-UI `STATE_SNAPSHOT` payload SHALL put Houmao-specific state under a namespaced Houmao object.

The snapshot SHALL include only safe observation fields needed by a GUI attachment, such as connection id, thread id, run id, gateway availability, target transport family, and a compact active-execution summary.

The snapshot SHALL NOT include mailbox message content, memory page content, raw terminal history, credentials, authorization headers, cookies, bearer tokens, raw prompt text, or unmanaged forwarded props.

#### Scenario: Snapshot contains namespaced Houmao status

- **WHEN** a connect stream emits its initial `STATE_SNAPSHOT`
- **THEN** the snapshot contains a namespaced Houmao object
- **AND THEN** the namespaced object contains the AG-UI connection id
- **AND THEN** the namespaced object contains a compact gateway status summary

#### Scenario: Snapshot omits sensitive state

- **WHEN** the gateway status source contains memory, mailbox, terminal, credential, or prompt-adjacent data
- **THEN** the AG-UI snapshot omits mailbox message content
- **AND THEN** the AG-UI snapshot omits memory page content
- **AND THEN** the AG-UI snapshot omits raw terminal history
- **AND THEN** the AG-UI snapshot omits credential and authorization material
- **AND THEN** the AG-UI snapshot omits raw prompt text

### Requirement: Disconnect detaches GUI bookkeeping only

The gateway SHALL support GUI detachment by both HTTP/SSE client disconnect and `DELETE /v1/ag-ui/connections/{connection_id}`.

Detaching a GUI connection SHALL remove the connection from AG-UI connection bookkeeping.

Detaching a GUI connection SHALL NOT stop, abort, interrupt, restart, shut down, or otherwise manage the Houmao agent or its active work.

#### Scenario: Closing the connect stream detaches only the GUI connection

- **WHEN** a caller opens `POST /v1/ag-ui/connect`
- **AND WHEN** the caller closes the SSE client connection
- **THEN** the AG-UI connection is detached from connection bookkeeping
- **AND THEN** the gateway does not stop, abort, interrupt, restart, or shut down the Houmao agent

#### Scenario: Explicit disconnect removes connection bookkeeping

- **WHEN** a caller has an active AG-UI connection id
- **AND WHEN** the caller sends `DELETE /v1/ag-ui/connections/{connection_id}`
- **THEN** the gateway removes that AG-UI connection from connection bookkeeping
- **AND THEN** the gateway does not stop, abort, interrupt, restart, or shut down the Houmao agent

#### Scenario: Unknown explicit disconnect is deterministic

- **WHEN** a caller sends `DELETE /v1/ag-ui/connections/{connection_id}` for an unknown connection id
- **THEN** the gateway returns a deterministic not-found or already-detached response
- **AND THEN** the gateway does not call any Houmao agent lifecycle control path

### Requirement: AG-UI runs route reports task submission as unavailable

`POST /v1/ag-ui/runs` SHALL be registered during this milestone, but it SHALL reject task-run submission with a deterministic error response until AG-UI run streaming is implemented.

The runs route SHALL NOT open an AG-UI run stream, submit a prompt, create a gateway request, emit `RUN_STARTED`, or modify agent lifecycle state.

#### Scenario: Runs route rejects task submission before run streaming exists

- **WHEN** a caller posts valid AG-UI run input to `POST /v1/ag-ui/runs`
- **THEN** the gateway returns a deterministic error explaining that AG-UI task runs are not enabled
- **AND THEN** the gateway does not submit a prompt
- **AND THEN** the gateway does not create a queued gateway request
- **AND THEN** the gateway does not emit `RUN_STARTED`

#### Scenario: Runs route behavior matches capabilities

- **WHEN** a caller reads `GET /v1/ag-ui/capabilities`
- **AND WHEN** the caller then posts to `POST /v1/ag-ui/runs`
- **THEN** the disabled task-run capability matches the deterministic runs-route rejection
