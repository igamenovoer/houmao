## ADDED Requirements

### Requirement: Per-agent gateway accepts published standard AG-UI event batches
The live per-agent gateway SHALL expose an AG-UI event ingestion route under `/v1/ag-ui` for callers that already have standard AG-UI events.

The ingestion route SHALL accept a bounded batch of AG-UI event JSON objects plus routing metadata needed to attach those events to a thread, run, or GUI connection.

The ingestion route SHALL validate each event against AG-UI core event shapes.

The ingestion route SHALL validate AG-UI event sequencing within the submitted batch when sequencing is locally checkable, including tool-call args and end events referencing a started tool call.

The ingestion route SHALL NOT validate Houmao component schemas, chart data semantics, table semantics, or dashboard layout semantics.

The ingestion route SHALL NOT submit a Houmao prompt, create a gateway request, stop, interrupt, restart, or otherwise manage the Houmao agent lifecycle.

#### Scenario: Valid standard AG-UI events are accepted
- **WHEN** a caller submits a bounded event batch containing valid AG-UI `TOOL_CALL_START`, `TOOL_CALL_ARGS`, and `TOOL_CALL_END` events
- **THEN** the gateway accepts the batch
- **AND THEN** the gateway records the accepted event count
- **AND THEN** no Houmao prompt request is created

#### Scenario: Gateway treats component names as opaque strings
- **WHEN** a caller submits a valid AG-UI tool-call sequence whose `toolCallName` is `houmao.chart.bar`
- **THEN** the gateway validates the AG-UI event envelope and sequence
- **AND THEN** it does not inspect or validate the chart payload against the `houmao.chart.bar` schema

#### Scenario: Malformed AG-UI event is rejected
- **WHEN** a caller submits `TOOL_CALL_ARGS` without a `toolCallId`
- **THEN** the gateway rejects the batch with a validation error
- **AND THEN** the gateway does not broadcast any event from that batch

### Requirement: Published AG-UI events are broadcast to matching streams
The gateway SHALL broadcast accepted published AG-UI events to active AG-UI connect or run streams whose routing metadata matches the submitted batch.

The gateway SHALL preserve the submitted AG-UI event payloads except for safe metadata needed for replay, diagnostics, or stream framing.

The gateway SHALL expose deterministic behavior when no matching stream is connected.

The gateway SHALL keep published-event stream bookkeeping separate from the Houmao task-run lifecycle.

#### Scenario: Connected GUI receives published events
- **WHEN** a GUI has an active AG-UI connect stream for a thread
- **AND WHEN** a caller publishes a valid AG-UI event batch for that thread
- **THEN** the connect stream emits the accepted events in submission order

#### Scenario: No active GUI still accepts or rejects deterministically
- **WHEN** no GUI stream matches the submitted routing metadata
- **AND WHEN** a caller publishes a valid AG-UI event batch
- **THEN** the gateway responds deterministically with accepted-but-not-delivered or an explicit no-subscriber status
- **AND THEN** the response does not imply that a Houmao task run was started

### Requirement: Published AG-UI events use bounded replay and safe diagnostics
The gateway SHALL maintain bounded replay bookkeeping for accepted published AG-UI events when replay is enabled for the target route.

The gateway SHALL bound event count, event size, total batch size, and replay retention.

Gateway diagnostics for published events SHALL include safe operational metadata such as route, status code, event count, thread id, run id, delivery count, and validation error locations.

Gateway diagnostics SHALL NOT include full tool-call argument payloads, message contents, credentials, authorization headers, cookies, or raw request-body dumps by default.

#### Scenario: Oversized event batch is rejected before broadcast
- **WHEN** a caller submits an AG-UI event batch larger than the configured limit
- **THEN** the gateway rejects the batch before broadcasting
- **AND THEN** the diagnostic identifies the limit category without dumping the full payload

#### Scenario: Diagnostics omit raw component payloads
- **WHEN** a published event batch contains a large chart payload
- **THEN** gateway diagnostics record safe counts and routing metadata
- **AND THEN** gateway diagnostics do not record the full chart data
