## ADDED Requirements

### Requirement: Gateway-owned TUI tracking routes support attached runtime-owned local interactive sessions
For an attached runtime-owned `local_interactive` session outside `houmao-server`, the gateway SHALL treat that session as eligible for its gateway-owned TUI tracking surface when durable attach metadata identifies the runtime-owned session and the tmux-backed session remains available.

For this path, the gateway SHALL start one gateway-owned continuous tracking runtime for the attached session and SHALL serve `GET /v1/control/tui/state` and `GET /v1/control/tui/history` from that runtime rather than returning unsupported-backend semantics.

The gateway SHALL derive tracked-session identity from durable attach-contract fields together with optional manifest-backed enrichment and SHALL NOT require a CAO terminal id to expose this tracking surface.

#### Scenario: Gateway-local TUI state succeeds for attached local interactive session
- **WHEN** a gateway is attached to a runtime-owned `local_interactive` session outside `houmao-server`
- **AND WHEN** the durable attach metadata identifies the runtime session id, tmux session name, and manifest path for that session
- **THEN** the gateway starts its gateway-owned tracking runtime for that session
- **AND THEN** `GET /v1/control/tui/state` succeeds using gateway-owned tracked state rather than returning an unsupported-backend response

#### Scenario: Gateway-local TUI history succeeds for attached local interactive session
- **WHEN** a gateway-owned tracking runtime is active for an attached runtime-owned `local_interactive` session
- **THEN** `GET /v1/control/tui/history` succeeds for that session
- **AND THEN** the returned history is keyed to the same gateway-owned tracked session identity used by current tracked state

### Requirement: Gateway prompt execution preserves explicit prompt-note evidence for tracked local interactive sessions
When the gateway accepts and executes `submit_prompt` for an attached runtime-owned `local_interactive` session, the gateway SHALL forward that explicit prompt-submission evidence to its gateway-owned tracking runtime for the same session.

That prompt-note behavior SHALL use the same gateway-owned tracking authority as the gateway-local TUI state and history routes for that attached session.

#### Scenario: Prompt submission updates gateway-owned tracked state for local interactive
- **WHEN** the gateway executes an accepted `submit_prompt` request for an attached runtime-owned `local_interactive` session
- **THEN** the gateway delivers the prompt through the local tmux-backed execution adapter for that session
- **AND THEN** the gateway records explicit prompt-submission evidence on the gateway-owned tracker for that same attached session
- **AND THEN** later tracked state for that session can preserve explicit-input provenance for the completed turn
