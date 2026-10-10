## ADDED Requirements

### Requirement: Mindset revisions may have non-canonical workspace projections
The mindset projection contract SHALL permit a Private Agent Workspace Contract to bind a semantic label for immutable mindset revision payloads.

#### Scenario: Admin publishes a revision
- **WHEN** an admin explicitly publishes one canonical mindset revision
- **THEN** Houmao SHALL write an immutable payload and index it in workspace SQLite

#### Scenario: Projection is edited
- **WHEN** the payload differs from its indexed digest
- **THEN** validation SHALL report drift and SHALL leave canonical instance state unchanged
