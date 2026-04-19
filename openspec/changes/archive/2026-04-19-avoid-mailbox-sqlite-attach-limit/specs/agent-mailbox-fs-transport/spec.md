## ADDED Requirements

### Requirement: Filesystem mailbox operations do not depend on SQLite attached-database capacity
The filesystem mailbox transport SHALL support mailbox roots and affected-account operation sets larger than the SQLite attached-database capacity available in the running environment.

Houmao-owned filesystem mailbox operations SHALL NOT enforce an account-count, recipient-count, fanout-count, initialization-count, or repair-count ceiling derived from SQLite `ATTACH DATABASE` limits.

When a filesystem mailbox operation needs to mutate or inspect mailbox-local SQLite state for multiple accounts, it SHALL access each affected account's mailbox-local state without requiring all affected mailbox-local databases to be attached to one SQLite connection at the same time.

The transport SHALL preserve the existing shared/root authority boundary: the shared mailbox-root index remains authoritative for structural registration, message, recipient, attachment, and projection state, while each resolved mailbox-local SQLite database remains authoritative for that mailbox's mutable view state.

Mailbox-local state updates performed outside a cross-database attached transaction SHALL be idempotent or repairable from committed structural mailbox state and canonical message artifacts.

#### Scenario: Local-state initialization handles more accounts than the attached-database limit
- **WHEN** a filesystem mailbox root contains more active mailbox registrations than SQLite can attach to one connection
- **AND WHEN** Houmao initializes or refreshes mailbox-local state for all active registrations
- **THEN** the initialization completes without failing because of SQLite attached-database capacity
- **AND THEN** each active mailbox registration has initialized mailbox-local SQLite state at its resolved mailbox directory

#### Scenario: Multi-recipient delivery handles more affected accounts than the attached-database limit
- **WHEN** a filesystem mailbox message delivery affects a sender plus recipients whose unique mailbox registrations exceed SQLite's attached-database capacity
- **THEN** the delivery does not fail because of SQLite attached-database capacity
- **AND THEN** the shared structural message, recipient, attachment, and projection state is recorded for the delivered message
- **AND THEN** each affected mailbox's local SQLite state reflects the delivered message according to existing sender, recipient, and self-addressed unread semantics

#### Scenario: Repair handles more discovered accounts than the attached-database limit
- **WHEN** filesystem mailbox repair discovers more mailbox accounts than SQLite can attach to one connection
- **THEN** repair rebuilds structural state and mailbox-local state without requiring all mailbox-local databases to be attached simultaneously
- **AND THEN** repaired mailbox-local state remains queryable for each discovered active mailbox

#### Scenario: Local-state partial failure remains repairable
- **WHEN** a filesystem mailbox operation commits structural shared state but fails while updating one affected mailbox's local SQLite state
- **THEN** the operation reports an explicit failure rather than silently treating the local mailbox as fully updated
- **AND THEN** a later repair or local-state initialization can rebuild the missing deterministic mailbox-local rows from committed structural state and canonical message artifacts
