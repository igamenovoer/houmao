## ADDED Requirements

### Requirement: Gateway durable storage is current-schema only
The gateway SHALL create current durable queue, notifier, and audit SQLite schemas when a gateway root is new.

When an existing gateway root contains durable SQLite state whose schema is older than the current implementation requires, Houmao SHALL reject that gateway root explicitly and direct the operator to start with a fresh runtime session or gateway root. Houmao SHALL NOT apply in-place SQLite schema upgrades to gateway durable storage.

#### Scenario: Fresh gateway root creates current queue schema
- **WHEN** a runtime session starts with a fresh gateway root
- **THEN** the gateway creates the current durable queue, notifier, and audit tables needed by the current implementation
- **AND THEN** no old gateway schema upgrade path is executed

#### Scenario: Older gateway queue schema is rejected
- **WHEN** a gateway opens existing durable SQLite state that is missing required current queue, notifier, or audit schema shape
- **THEN** gateway startup or state access fails explicitly before mutating that SQLite database
- **AND THEN** the diagnostic directs the operator to recreate the affected runtime session or gateway root

#### Scenario: Notifier table is not upgraded in place
- **WHEN** an existing gateway notifier table lacks a current required column such as notifier mode
- **THEN** Houmao rejects the gateway root as incompatible current gateway state
- **AND THEN** it does not add the missing column through `ALTER TABLE`
