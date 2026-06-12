## MODIFIED Requirements

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
- **WHEN** a caller submits a valid AG-UI tool-call sequence whose `toolCallName` is `houmao.graphic.template`
- **THEN** the gateway validates the AG-UI event envelope and sequence
- **AND THEN** it does not inspect or validate the chart payload against the `houmao.graphic.template` schema

#### Scenario: Malformed AG-UI event is rejected
- **WHEN** a caller submits `TOOL_CALL_ARGS` without a `toolCallId`
- **THEN** the gateway rejects the batch with a validation error
- **AND THEN** the gateway does not broadcast any event from that batch
