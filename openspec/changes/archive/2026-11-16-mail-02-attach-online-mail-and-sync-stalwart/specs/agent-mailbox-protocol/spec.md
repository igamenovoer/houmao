# Spec Delta

## ADDED Requirements

### Requirement: Shared mailbox listing returns bounded metadata pages
Channel-selected list SHALL return a finite metadata page with continuation information and an enforced maximum size. Listing SHALL not return full message bodies or attachment content and SHALL not mark read. The former list `include_body` input SHALL be rejected. Peek/read SHALL remain the explicit content-inspection operations.

#### Scenario: Default list is bounded
- **WHEN** a caller lists either channel without a limit
- **THEN** the service applies its finite default and reports whether continuation is available
- **AND THEN** the response does not contain full bodies

#### Scenario: Caller requests bodies through list
- **WHEN** a list request supplies the removed `include_body` field
- **THEN** strict validation rejects it and identifies peek/read as the supported content operations

#### Scenario: Peek remains non-mutating
- **WHEN** a caller peeks a selected message from a metadata page
- **THEN** its content is retrieved explicitly without changing read state

### Requirement: Pagination counts and continuation scope are explicit
List responses SHALL distinguish returned-page counts from optional exact mailbox totals or lower bounds. A continuation SHALL preserve owner, channel, binding, filter, and sort scope. Stale or mismatched continuations SHALL fail explicitly or use the documented bounded reconciliation policy rather than silently restarting an unbounded scan.

#### Scenario: Page is not the whole inbox
- **WHEN** a page returns 50 eligible messages from a larger inbox
- **THEN** page counts describe those returned messages
- **AND THEN** the response does not label 50 as the exact inbox total

#### Scenario: Offline cursor is supplied to online list
- **WHEN** a continuation from the offline channel is used for online listing
- **THEN** validation rejects its scope before provider I/O

### Requirement: Mailbox content limits are visible
Explicit content retrieval SHALL report whether returned content is complete. Size limits or truncation SHALL identify the supported continuation/download path or explicit unsupported limitation. A partial body SHALL not be silently represented as the complete message. Read/peek lifecycle effects SHALL remain independent of content-transfer limits.

#### Scenario: Large body is truncated by the provider
- **WHEN** the provider reports a partial body value
- **THEN** the caller receives visible completeness/limit information
- **AND THEN** peek does not become a mutating read merely to retrieve more content
