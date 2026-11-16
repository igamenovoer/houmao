# Spec Delta

## Purpose

Define bounded metadata discovery and incremental Stalwart mailbox synchronization without copying retained message bodies into gateway state.

## ADDED Requirements

### Requirement: Stalwart list queries are bounded and filtered on the server
Stalwart listing SHALL apply supported mailbox, read, answered, archive-membership, and time filters before pagination. Every request SHALL have a finite default and enforced maximum page size. Unsupported filters or missing required mailbox roles SHALL produce explicit errors rather than unfiltered account queries or post-limit filtering that hides matching work.

#### Scenario: Old unread mail is behind newer read mail
- **WHEN** a bounded unread query matches messages older than many read messages
- **THEN** server-side filtering allows the requested unread page to be returned
- **AND THEN** the client does not fetch newer read messages merely to discard them

#### Scenario: Inbox role is absent
- **WHEN** the selected account has no required inbox role
- **THEN** the client reports the missing role
- **AND THEN** it does not query every message in the account as a fallback

### Requirement: Metadata discovery never retrieves message body values
Listing and synchronization SHALL retrieve only the metadata required for selection, state, and bounded previews. They SHALL not request text-body values, full MIME content, or attachment bytes. Peek/read SHALL retrieve explicitly selected content and report truncation or content-size limits without presenting partial content as complete.

#### Scenario: Metadata page has no body transfer
- **WHEN** a caller lists a Stalwart mailbox without reading a message
- **THEN** wire requests exclude body-value retrieval and attachment downloads
- **AND THEN** returned metadata remains sufficient for scoped peek/read targeting

#### Scenario: Explicit content exceeds a supported limit
- **WHEN** selected message content cannot be returned completely under the configured limit
- **THEN** the result identifies the limit or truncation and its supported retrieval path explicitly

### Requirement: Continuation cursors preserve query and account scope
Opaque continuation cursors SHALL bind owner, online binding, provider account, filters, sort, page position, and query state. Another account or changed query SHALL reject the cursor. Query-state drift SHALL produce an explicit stale-cursor outcome or a documented bounded reconciliation, never silently combine incompatible pages.

#### Scenario: Credential refresh keeps a valid account cursor
- **WHEN** credentials change for the same binding/account and the server query state remains valid
- **THEN** the continuation can remain usable without rebuilding retained history

#### Scenario: Filter changes invalidate continuation
- **WHEN** an unread-only cursor is supplied for an any-inbox query
- **THEN** validation fails without issuing a broader query

#### Scenario: Mail changes between pages
- **WHEN** the server can no longer continue the cursor's query state consistently
- **THEN** the client reports stale pagination or performs only its documented bounded reconciliation

### Requirement: Discovery and mailbox-role lookup are reused per connection scope
The Stalwart adapter SHALL reuse validated session/account and mailbox-role information within a connection scope, refresh it when stale, and batch bounded message metadata fetches. A page SHALL not issue a separate mailbox enumeration for every message. Credential or account replacement SHALL not reuse another scope's discovery state.

#### Scenario: A multi-message page avoids per-message role queries
- **WHEN** the client normalizes a page containing many messages
- **THEN** it uses the cached or once-refreshed mailbox-role map
- **AND THEN** mailbox lookup count does not grow once per message

### Requirement: Incremental checkpoints are account-scoped and distinct from query state
Synchronization SHALL use supported JMAP change tracking and keep email-object state distinct from query-specific state. Checkpoints SHALL be scoped to owner, binding, account, and relevant view policy. Credential refresh for the same identity SHALL preserve eligible checkpoints; account replacement SHALL start a separate scope.

#### Scenario: Changes have intermediate states
- **WHEN** an email change response indicates further changes remain
- **THEN** later bounded batches continue from its returned intermediate state
- **AND THEN** a newer state seen in an unrelated metadata fetch does not skip the remaining changes

#### Scenario: Account replacement has overlapping provider IDs
- **WHEN** the new account uses message IDs that appeared in the old account
- **THEN** it does not inherit the old checkpoint or metadata view

### Requirement: Applied metadata and checkpoint progress commit together
The synchronizer SHALL advance its checkpoint only after all returned changes in that batch are applied or explicitly reconciled. A failed metadata fetch or local commit SHALL leave progress retryable. Retries SHALL be idempotent, and superseded workers SHALL not commit into a current binding's state.

#### Scenario: Fetch fails after a change response
- **WHEN** change IDs are received but their required metadata cannot be fetched
- **THEN** the checkpoint does not advance past that unapplied batch
- **AND THEN** retry can process it again without duplicate logical entries

#### Scenario: Message disappears before metadata retrieval
- **WHEN** a changed message is authoritatively reported missing during metadata fetch
- **THEN** the view reconciles it as absent before committing progress

### Requirement: Stale-state recovery has finite work budgets
Expired or unsupported change state and oversized query deltas SHALL trigger invalidation of derived views and bounded rebase from current server-filtered inbox queries. Recovery SHALL not fetch full bodies or enumerate all retained history before mail can be discovered. Work that exceeds per-cycle budgets SHALL report pending/degraded progress and resume later.

#### Scenario: Old checkpoint cannot be calculated
- **WHEN** the server rejects a persisted checkpoint as too old
- **THEN** the synchronizer rebuilds a bounded eligible metadata view and establishes a new checkpoint boundary
- **AND THEN** it does not scan the archive or download old bodies

#### Scenario: Query delta exceeds the maximum
- **WHEN** query-change tracking reports more changes than its configured limit
- **THEN** recovery respects its bounded requery policy
- **AND THEN** it does not retry with an unlimited delta or assume query-change responses have email-change pagination semantics

### Requirement: Metadata view eviction does not redefine mailbox truth
The synchronized view SHALL be derived, bounded metadata rather than a second authoritative mailbox or message-delivery spool. Historical mail SHALL remain available through explicit server pages. Eviction SHALL not imply read, archive, removal, processing completion, or a new compaction eligibility stretch.

#### Scenario: Eligible mail falls outside the cached window
- **WHEN** a metadata entry is evicted while its message remains in the inbox
- **THEN** explicit pagination can still discover it from the server
- **AND THEN** cache eviction does not change mail state or reset compaction history

### Requirement: Synchronization status exposes bounded progress and limitations
Status SHALL distinguish idle/up-to-date, catching up, rebasing, degraded, and unsupported behavior, with safe last-success/error information and budget-limited progress. It SHALL distinguish page counts or lower bounds from exact mailbox totals and SHALL not expose credentials or message bodies.

#### Scenario: Catch-up spans several cycles
- **WHEN** pending changes exceed one cycle's budget
- **THEN** status reports remaining catch-up rather than claiming complete synchronization

### Requirement: Qualification measures retained-history independence
The change SHALL include deterministic wire-level tests and a documented load plan for approximately 100 agents and millions of retained messages. The plan SHALL measure request counts, bytes, latency, memory, and backlog recovery under idle, new-mail, stale-state, and reconnect conditions. Unexecuted target-scale runs SHALL not be presented as proven capacity.

#### Scenario: Idle mailbox has a large archive
- **WHEN** qualification compares idle polling with small and large retained histories
- **THEN** it records whether client request/payload work remains bounded without full-body scans
- **AND THEN** the report states the actual scale and environment tested
