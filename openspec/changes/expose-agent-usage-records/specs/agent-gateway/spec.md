# Spec Delta

## ADDED Requirements

### Requirement: Gateway exposes bounded finalized usage retrieval

The live gateway SHALL expose `GET /v1/usage` with optional `after` cursor and bounded `limit` inputs. It SHALL return versioned records, stream identity, evidence-based capability, a resumable cursor, and page-continuation state for supported headless and native-observed turns.

#### Scenario: Headless usage page is returned

- **WHEN** a caller queries a headless target with finalized usage
- **THEN** the gateway returns the requested bounded page in finalization order

#### Scenario: Qualified TUI usage page is returned

- **WHEN** a caller queries a TUI target with validated native-log accounting
- **THEN** the gateway returns its finalized records through the same usage page contract

#### Scenario: Polling continues after an empty page

- **WHEN** a caller saves a queryable stream's cursor from an empty page and a record later finalizes
- **THEN** a request after that cursor returns the later record without restarting history

#### Scenario: Invalid pagination input fails validation

- **WHEN** a caller supplies an invalid or wrong-stream cursor or an out-of-bounds limit
- **THEN** the gateway returns HTTP 422 without substituting an unbounded query

### Requirement: Gateway usage capability reflects available accounting evidence

Usage capability SHALL identify validated sources, observed scopes, turn-recording support, and safe limitation reasons. Unsupported sources SHALL NOT produce fabricated records. Existing finalized history SHALL remain readable when current collection becomes degraded or unavailable.

#### Scenario: Unsupported TUI source returns a capability response

- **WHEN** a TUI target has no validated structured accounting source
- **THEN** the gateway returns unavailable accounting capability without fabricated usage or unrelated headless-control errors

#### Scenario: Session-only source does not imply turn support

- **WHEN** a target exposes cumulative session evidence without verified turn association
- **THEN** its capability identifies that limitation and does not claim per-turn token accounting

#### Scenario: Collector failure preserves known records

- **WHEN** the current source becomes unreadable after earlier records were finalized
- **THEN** the gateway returns readable finalized history with degraded collection capability and a safe diagnostic

#### Scenario: Usage storage is incompatible

- **WHEN** the usage store cannot be read because its schema is incompatible or its storage is unavailable
- **THEN** the gateway returns HTTP 503 with safe diagnostics rather than reporting an empty successful history

### Requirement: Gateway manages bound usage collection through its lifecycle

For a qualified attached target, the gateway SHALL start or resume collection against the runtime-session binding, recover missed accounting after restart, and release its collection worker on shutdown. Replacement instances SHALL resume durable progress without duplicate records.

#### Scenario: Gateway restarts during native-log collection

- **WHEN** a gateway restarts after observing part of a bound native log
- **THEN** collection resumes from durable progress and known requests do not receive new charges

#### Scenario: Gateway attaches to a conversation with history

- **WHEN** collection first attaches to an existing provider conversation
- **THEN** it establishes a boundary and does not import earlier usage as new managed work

### Requirement: Gateway usage reads do not mutate or serialize agent execution

`GET /v1/usage` SHALL NOT acquire the terminal-mutation slot, enqueue prompts, interrupt execution, or require an idle agent. Ordinary reads SHALL use bounded finalized history without synchronously scanning provider-log or artifact trees.

#### Scenario: Active agent continues during a history query

- **WHEN** a caller requests usage while a turn is active
- **THEN** previously finalized records remain readable without changing active execution
- **AND THEN** the active turn remains absent from finalized history
