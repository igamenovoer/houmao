# Spec Delta

## ADDED Requirements

### Requirement: Server-managed headless finalization persists normalized usage

A completed, failed, or interrupted server-managed headless turn SHALL produce its final accounting in the shared runtime-session ledger using the existing managed turn ID. Selection of structured output and native-log evidence SHALL follow the shared scope and deduplication rules.

#### Scenario: Server-managed completion is recorded

- **WHEN** a turn submitted through `POST /houmao/agents/{agent_ref}/turns` completes
- **THEN** its usage is queryable with the same managed turn ID and recorded outcome

#### Scenario: Interruption preserves partial usage

- **WHEN** a server-managed turn is interrupted after writing provider usage evidence
- **THEN** finalization records the interrupted outcome and available partial metrics

#### Scenario: Native log repeats headless stdout usage

- **WHEN** one server-managed request appears in structured stdout and the bound native log
- **THEN** shared finalization counts it once without creating a second source-specific history

#### Scenario: Resumed completion contains cumulative usage

- **WHEN** a resumed server-managed turn reports cumulative usage
- **THEN** its turn metrics use verified request evidence or a comparable baseline rather than charging the entire session total

### Requirement: Server-managed recovery preserves terminal evidence

Server-managed accounting recovery SHALL preserve the original identity, outcome, timing, and evidence cutoff of a durably finalized turn. A controller timeout alone SHALL NOT finalize accounting while execution remains active.

#### Scenario: Recorder stops after durable completion

- **WHEN** terminal evidence exists but the accounting recorder stops before committing
- **THEN** recovery creates one final record with the original terminal facts

#### Scenario: Controller loses contact with a running turn

- **WHEN** the controller times out while the provider process is still active
- **THEN** accounting remains pending until terminal evidence establishes the outcome

### Requirement: Passive server queries server-managed usage without a live controller

The passive server SHALL expose `GET /houmao/agents/{agent_ref}/usage` with optional `after` and bounded `limit` inputs for server-managed headless agents. Readable durable history SHALL NOT require a live controller or attached gateway.

#### Scenario: Controller downtime preserves history

- **WHEN** a caller requests usage for a server-managed agent without a live controller
- **THEN** the passive server returns stored finalized history and identifies any current collection limitation

#### Scenario: End cursor remains usable

- **WHEN** a caller saves the cursor from the current final page and another turn later finalizes
- **THEN** the next request after that cursor returns the new record without repeating earlier history
