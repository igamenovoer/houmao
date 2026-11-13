# Spec Delta

## ADDED Requirements

### Requirement: Maintained usage query selects the authoritative agent source

For `GET /houmao/agents/{agent_ref}/usage`, the passive server SHALL use authoritative server-managed headless history when present and otherwise proxy the resolved live gateway's usage route. The query SHALL NOT create a second accounting history or independently ingest the gateway's provider logs.

#### Scenario: Server-managed authority takes precedence

- **WHEN** an agent has server-managed headless authority and an attached gateway
- **THEN** its usage query reads the authoritative shared ledger rather than a second gateway-derived history

#### Scenario: Gateway-attached agent uses its live projection

- **WHEN** an agent has no server-managed authority and has a live attached gateway
- **THEN** the passive server forwards pagination inputs and returns the gateway's versioned usage page

### Requirement: Usage proxy preserves capabilities and stream cursors

The passive server SHALL preserve gateway-reported source capability, limitations, stream identity, record identities, resumable cursor, and page-continuation state. Qualified TUI records and unavailable-accounting responses SHALL remain normal usage responses.

#### Scenario: Qualified TUI usage passes through

- **WHEN** a gateway returns finalized native-observed TUI records
- **THEN** the maintained route returns those records with unchanged accounting identities and cursor semantics

#### Scenario: Unsupported source remains a capability response

- **WHEN** a gateway reports unavailable accounting because no validated structured source exists
- **THEN** the passive server preserves that response without fabricating records or converting it into a connectivity failure

#### Scenario: Degraded collection preserves prior history

- **WHEN** a gateway returns finalized history with degraded collection capability
- **THEN** the passive server preserves both the history and its limitation reasons

#### Scenario: Empty-page cursor passes through

- **WHEN** a gateway returns a resumable cursor with an empty page and no further current records
- **THEN** the passive server preserves that cursor for later polling

### Requirement: Usage proxy preserves resolution and storage errors

The usage query SHALL preserve existing resolution behavior: 404 for unknown agents, 409 for ambiguous references, and 502 for missing or unreachable gateways. Upstream pagination validation and usage-storage failures SHALL remain explicit.

#### Scenario: Missing gateway returns 502

- **WHEN** a query targets a non-server-managed agent without a live attached gateway
- **THEN** the passive server returns HTTP 502 explaining the required gateway connection

#### Scenario: Ambiguous reference returns 409

- **WHEN** an agent reference matches multiple managed identities
- **THEN** the passive server returns HTTP 409 without choosing arbitrary history

#### Scenario: Wrong-stream cursor remains invalid

- **WHEN** the gateway rejects a cursor from another usage stream
- **THEN** the passive server preserves the HTTP 422 validation failure

#### Scenario: Unreadable ledger remains a storage failure

- **WHEN** the gateway cannot read its usage ledger and returns HTTP 503
- **THEN** the passive server preserves the explicit safe storage failure rather than returning empty history
