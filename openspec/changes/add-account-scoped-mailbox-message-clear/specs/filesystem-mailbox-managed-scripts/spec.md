## ADDED Requirements

### Requirement: Managed filesystem mailbox operations clear one account without corrupting shared message state

The managed filesystem mailbox layer SHALL provide an account-scoped delivered-message clear operation for one active mailbox registration under a filesystem mailbox root.

The operation SHALL validate the requested address before mutation and SHALL fail before mutation if no active registration exists for that address.

The operation SHALL plan account-scoped clear targets before applying mutations. The plan SHALL distinguish:

- selected-account projection artifacts and projection rows,
- selected-account mailbox-local message and thread state,
- canonical message files and shared message rows that can be removed because no projection will remain after clearing the selected account,
- canonical message files and shared message rows that must be preserved because another registration still has a projection,
- mailbox-owned managed-copy attachment artifacts that can be removed because no retained message references them,
- external `path_ref` attachment targets that must be preserved,
- unsafe paths outside registered mailbox or mailbox-owned artifact roots that must be blocked.

In dry-run mode, the operation SHALL return planned, preserved, and blocked actions without deleting files or mutating SQLite state.

When applying, the operation SHALL mutate shared SQLite catalog state and filesystem artifacts consistently enough that subsequent structural message inspection for the selected account no longer lists cleared messages, while structural message inspection for other accounts still lists any messages they retained.

The operation SHALL preserve mailbox registrations and mailbox account directories.

#### Scenario: Account-scoped operation preserves retained projections

- **WHEN** a filesystem mailbox root contains active registrations for `alice@houmao.localhost` and `bob@houmao.localhost`
- **AND WHEN** one message has projections for both registrations
- **WHEN** the managed account-scoped clear operation runs for `alice@houmao.localhost`
- **THEN** the operation removes `alice@houmao.localhost` projection state for the message
- **AND THEN** the operation preserves `bob@houmao.localhost` projection state for the message
- **AND THEN** the operation preserves the shared canonical message file

#### Scenario: Account-scoped operation removes orphaned canonical message content

- **WHEN** a filesystem mailbox root contains a message whose only remaining projection belongs to `alice@houmao.localhost`
- **WHEN** the managed account-scoped clear operation runs for `alice@houmao.localhost`
- **THEN** the operation removes the selected projection artifact
- **AND THEN** the operation removes the canonical message file and shared message rows for that message
- **AND THEN** the operation preserves the `alice@houmao.localhost` mailbox registration

#### Scenario: Account-scoped operation handles attachments by retained message references

- **WHEN** a cleared-last-projection message has one mailbox-owned managed-copy attachment and one external `path_ref` attachment
- **WHEN** the managed account-scoped clear operation applies successfully
- **THEN** the operation removes the unreferenced mailbox-owned managed-copy attachment artifact
- **AND THEN** the operation preserves the external `path_ref` attachment target

#### Scenario: Account-scoped dry-run does not mutate state

- **WHEN** a filesystem mailbox root contains messages visible to `alice@houmao.localhost`
- **WHEN** the managed account-scoped clear operation runs in dry-run mode for `alice@houmao.localhost`
- **THEN** the operation returns planned clear actions
- **AND THEN** the operation does not delete projection artifacts, canonical messages, managed-copy attachments, registrations, or SQLite rows
