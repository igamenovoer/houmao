## ADDED Requirements

### Requirement: Gateway-owned TUI history exposes bounded recent tracked snapshots
For attached TUI-backed sessions whose gateway owns live tracking authority, `GET /v1/control/tui/history` SHALL return recent tracked snapshots from that gateway-owned tracking runtime rather than only coarse transition summaries.

That snapshot history SHALL be retained in memory only and SHALL be bounded to the most recent 1000 snapshots per tracked session.

The returned history SHALL be ordered from oldest retained snapshot to newest retained snapshot.

#### Scenario: Gateway TUI history returns tracked snapshots for an attached TUI session
- **WHEN** a live gateway owns TUI tracking for an attached eligible TUI-backed session
- **AND WHEN** a caller requests `GET /v1/control/tui/history`
- **THEN** the response contains recent tracked snapshots from that gateway-owned tracking runtime
- **AND THEN** the response does not collapse those snapshots to coarse transition summaries only

#### Scenario: Gateway TUI history remains bounded in memory
- **WHEN** a gateway-owned tracker for one attached TUI-backed session has recorded more than 1000 tracked snapshots
- **AND WHEN** a caller requests `GET /v1/control/tui/history`
- **THEN** the response contains at most the most recent 1000 tracked snapshots for that session
- **AND THEN** older snapshots have been evicted from in-memory history rather than persisted as durable gateway state

## MODIFIED Requirements

### Requirement: Gateway-owned TUI tracking routes support attached runtime-owned local interactive sessions
For an attached runtime-owned `local_interactive` session outside `houmao-server`, the gateway SHALL treat that session as eligible for its gateway-owned live TUI state, bounded snapshot history, and explicit prompt-note tracking surface when durable attach metadata identifies the runtime-owned session and the tmux-backed session remains available.

For this path, the gateway SHALL start one gateway-owned continuous tracking runtime for the attached session and SHALL serve `GET /v1/control/tui/state`, `GET /v1/control/tui/history`, and `POST /v1/control/tui/note-prompt` from that runtime rather than returning unsupported-backend semantics.

The gateway SHALL derive tracked-session identity from durable attach-contract fields together with optional manifest-backed enrichment and SHALL NOT require a CAO terminal id to expose this tracking surface.

For this runtime-owned local-interactive path, `GET /v1/control/tui/history` SHALL be part of the supported gateway operator workflow.

#### Scenario: Gateway-local TUI state succeeds for attached local interactive session
- **WHEN** a gateway is attached to a runtime-owned `local_interactive` session outside `houmao-server`
- **AND WHEN** the durable attach metadata identifies the runtime session id, tmux session name, and manifest path for that session
- **THEN** the gateway starts its gateway-owned tracking runtime for that session
- **AND THEN** `GET /v1/control/tui/state` succeeds using gateway-owned tracked state rather than returning an unsupported-backend response

#### Scenario: Gateway-local TUI history succeeds for attached local interactive session
- **WHEN** a gateway-owned tracking runtime is active for an attached runtime-owned `local_interactive` session
- **THEN** `GET /v1/control/tui/history` succeeds for that session
- **AND THEN** the returned history contains recent gateway-owned tracked snapshots for that same session

#### Scenario: Gateway-local prompt-note route succeeds for attached local interactive session
- **WHEN** a gateway-owned tracking runtime is active for an attached runtime-owned `local_interactive` session
- **THEN** `POST /v1/control/tui/note-prompt` succeeds for that session
- **AND THEN** the prompt note is recorded against the same gateway-owned tracked session identity used by current tracked state
