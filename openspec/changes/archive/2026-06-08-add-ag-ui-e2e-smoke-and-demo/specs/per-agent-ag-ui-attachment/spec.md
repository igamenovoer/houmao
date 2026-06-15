## ADDED Requirements

### Requirement: Per-agent AG-UI streams expose safe diagnostics
The live per-agent gateway SHALL emit safe diagnostics for AG-UI connect streams and run streams.

At minimum, AG-UI diagnostics SHALL cover connect creation, disconnect or detach, run admission, run stream start, run completion, stream client disconnect, and stream error outcomes.

AG-UI diagnostics SHALL include lifecycle identifiers and operational metadata such as connection id, thread id, run id, gateway request id, target transport family, terminal outcome, active connection count, active run count, duration, status code, and error category when available.

AG-UI diagnostics SHALL NOT include prompt text, full AG-UI message content, mailbox content, memory content, raw terminal history, credentials, authorization headers, or unmanaged forwarded props.

#### Scenario: Run diagnostics record lifecycle without private payloads
- **WHEN** an AG-UI run is admitted through `/v1/ag-ui/runs`
- **THEN** the gateway records safe diagnostics for admission and stream completion
- **AND THEN** the diagnostics include run id, gateway request id, target transport family, terminal outcome, and duration when available
- **AND THEN** the diagnostics do not include the submitted prompt text, AG-UI message bodies, credentials, or unmanaged forwarded props

#### Scenario: Connect diagnostics record attachment without submitting work
- **WHEN** a GUI attaches through `/v1/ag-ui/connect` and later disconnects
- **THEN** the gateway records safe diagnostics for connection creation and detachment
- **AND THEN** the diagnostics include the connection id and active AG-UI connection count
- **AND THEN** the diagnostics do not claim that a Houmao task run was started

### Requirement: Per-agent AG-UI diagnostics report active connection and run counts
The live per-agent gateway SHALL maintain lightweight AG-UI diagnostic counts for active GUI connections and active AG-UI run streams.

The counts SHALL reflect stream bookkeeping rather than the lifetime of the Houmao managed agent. A disconnected GUI stream SHALL decrement the relevant AG-UI count without stopping, restarting, shutting down, or interrupting the managed agent.

#### Scenario: Active counts update across connect and run streams
- **WHEN** one AG-UI connect stream and one AG-UI run stream are active
- **THEN** the gateway diagnostics report one active AG-UI connection and one active AG-UI run
- **AND WHEN** the connect stream and run stream close
- **THEN** the gateway diagnostics return those AG-UI counts to zero
- **AND THEN** the managed agent lifecycle remains unchanged by those stream closures

#### Scenario: Counts recover after stream error
- **WHEN** an AG-UI stream raises a mapping, encoding, or client-send error
- **THEN** the gateway records a stream-error diagnostic
- **AND THEN** the affected active AG-UI stream count is decremented during cleanup
- **AND THEN** unrelated AG-UI streams continue to be counted accurately

### Requirement: Per-agent AG-UI run streams emit deterministic terminal errors after admission
After an AG-UI run has been admitted and `RUN_STARTED` has been emitted, the live per-agent gateway SHALL convert stream mapping, encoding, or runtime-observation failures into a deterministic AG-UI `RUN_ERROR` event when the client is still connected and the stream can still write.

Pre-admission validation and availability failures SHALL remain HTTP errors and SHALL NOT emit `RUN_STARTED`.

Client disconnects SHALL clean up stream bookkeeping and SHALL NOT require a `RUN_ERROR` event because the client has detached from the stream.

#### Scenario: Mapping error after run start becomes RUN_ERROR
- **WHEN** an AG-UI run stream has emitted `RUN_STARTED`
- **AND WHEN** a mapping, encoding, or runtime-observation error occurs while the client is still connected
- **THEN** the stream emits a `RUN_ERROR` event with a stable Houmao error code
- **AND THEN** the gateway records a safe stream-error diagnostic with the error category
- **AND THEN** the stream performs active-run cleanup

#### Scenario: Pre-admission error remains an HTTP error
- **WHEN** an invalid AG-UI input, busy target, or unavailable gateway target is rejected before run admission
- **THEN** the gateway returns the appropriate HTTP error
- **AND THEN** the response does not contain `RUN_STARTED`
- **AND THEN** no active AG-UI run count is left behind

#### Scenario: Client abort detaches without interrupting by default
- **WHEN** an AG-UI client aborts the run stream after admission
- **THEN** the gateway detaches the stream and performs active-run cleanup
- **AND THEN** the gateway does not interrupt the underlying Houmao task unless an explicit abort policy opts into interruption
