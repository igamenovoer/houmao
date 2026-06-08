## MODIFIED Requirements

### Requirement: AG-UI capabilities report conservative attachment support

The gateway SHALL provide `GET /v1/ag-ui/capabilities` so GUI clients can discover supported AG-UI behavior before connecting or starting a run.

The capabilities response SHALL report HTTP SSE support, GUI connect support, text input parsing support, state snapshot support, and task-run submission as enabled when AG-UI run streaming is implemented for the live per-agent gateway.

The capabilities response SHALL report generated graphics support as enabled only when `houmao_render_graphic` artifact validation and event mapping are available for the target.

The capabilities response SHALL report state delta support, frontend tool execution, Open Generative UI, and unsupported multimodal input as disabled for this milestone.

The capabilities response SHALL identify that GUI lifecycle does not manage the Houmao agent lifecycle.

#### Scenario: Capabilities report run streaming support

- **WHEN** a caller requests `GET /v1/ag-ui/capabilities` after AG-UI run streaming is enabled
- **THEN** the response reports HTTP SSE support as enabled
- **AND THEN** the response reports GUI connect support as enabled
- **AND THEN** the response reports state snapshot support as enabled
- **AND THEN** the response reports task-run submission as enabled
- **AND THEN** the response reports text input parsing as enabled

#### Scenario: Capabilities report graphics support when enabled

- **WHEN** a caller requests `GET /v1/ag-ui/capabilities` for a gateway target with `houmao_render_graphic` mapping enabled
- **THEN** the response reports generated graphics as enabled
- **AND THEN** the response identifies `houmao_render_graphic` in Houmao metadata or tool capability metadata

#### Scenario: Capabilities remain conservative for unsupported features

- **WHEN** a caller requests `GET /v1/ag-ui/capabilities`
- **THEN** the response reports state delta support as disabled
- **AND THEN** the response reports frontend tool execution as disabled
- **AND THEN** the response reports Open Generative UI as disabled
- **AND THEN** the response reports unsupported multimodal input as disabled

#### Scenario: Capabilities state that GUI does not own agent lifecycle

- **WHEN** a caller requests `GET /v1/ag-ui/capabilities`
- **THEN** the response contains Houmao metadata indicating that the GUI does not manage the agent lifecycle

## REMOVED Requirements

### Requirement: AG-UI runs route reports task submission as unavailable

**Reason**: Milestone 2 replaces the placeholder unavailable route with a real AG-UI run stream.

**Migration**: Clients SHALL read `GET /v1/ag-ui/capabilities` and, when task-run submission is enabled, post valid `RunAgentInput` JSON to `POST /v1/ag-ui/runs` and consume the returned SSE stream.

#### Scenario: Runs route no longer returns the placeholder unavailable response

- **WHEN** a caller posts valid AG-UI run input to `POST /v1/ag-ui/runs` and the target gateway admits the run
- **THEN** the gateway returns a `text/event-stream` response
- **AND THEN** the gateway does not return the milestone-1 `ag_ui_runs_unavailable` response
