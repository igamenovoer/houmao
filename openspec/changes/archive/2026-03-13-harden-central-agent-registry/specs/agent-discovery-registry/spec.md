## ADDED Requirements

### Requirement: Shared-registry resolution treats malformed records as unusable stale entries
When shared-registry resolution loads a candidate `record.json` for a known agent name, the system SHALL treat missing, malformed, schema-invalid, or lease-expired records as unusable discovery state rather than as a successful live result.

Lookup-facing resolution SHALL return an explicit not-found or stale-record outcome for those unusable records.

Strict validation MAY still be used for diagnostics, cleanup classification, or publish-time verification, but malformed persisted records SHALL NOT force name-based discovery to abort before it can conclude that the record is unusable.

#### Scenario: Malformed JSON record resolves as stale rather than raising a lookup-stopping error
- **WHEN** a caller resolves a known shared-registry agent name
- **AND WHEN** the corresponding `record.json` contains invalid JSON
- **THEN** the resolution path returns an explicit not-found or stale-record result
- **AND THEN** the malformed record is not treated as a live discovered agent

#### Scenario: Schema-invalid record resolves as stale rather than live
- **WHEN** a caller resolves a known shared-registry agent name
- **AND WHEN** the corresponding `record.json` fails strict schema validation
- **THEN** the resolution path returns an explicit not-found or stale-record result
- **AND THEN** the invalid record is not returned as a usable live record

### Requirement: Shared-registry timestamps are timezone-aware
The shared-registry `record.json` contract SHALL require timezone-aware `published_at` and `lease_expires_at` timestamps.

Readers and validators SHALL reject naive timestamps that omit timezone information rather than interpreting them relative to the local timezone of the reading process.

#### Scenario: Naive published timestamp is rejected
- **WHEN** a shared-registry record contains `published_at` without timezone information
- **THEN** the record fails validation
- **AND THEN** the record is not treated as a valid live discovery entry

#### Scenario: UTC timestamp remains valid
- **WHEN** a shared-registry record contains timezone-aware UTC timestamps such as `Z` or `+00:00`
- **THEN** the record passes timestamp-format validation
- **AND THEN** lease freshness is evaluated deterministically from those persisted values

### Requirement: Shared-registry atomic write cleanup removes orphan temp files on replace failure
When the shared-registry publish path writes a temporary file for atomic replacement of `record.json`, the system SHALL remove that temp file if the final replace step fails.

#### Scenario: Failed replace removes temp file
- **WHEN** the publish path has already written a temporary registry file in the target live-agent directory
- **AND WHEN** the final atomic replace into `record.json` fails
- **THEN** the runtime removes the temporary file before surfacing the publish failure
- **AND THEN** the live-agent directory is not left with an orphaned temp file from that failed publish attempt

### Requirement: Shared-registry cleanup continues past per-directory removal failure and reports it explicitly
When stale-registry cleanup scans `live_agents/`, the cleanup pass SHALL continue processing later stale directories even if one earlier directory cannot be removed.

Cleanup results SHALL report failed removals explicitly rather than collapsing them into the same outcome as lease-fresh preserved directories.

#### Scenario: One failed stale-directory removal does not abort later cleanup
- **WHEN** stale-registry cleanup encounters one stale live-agent directory that cannot be removed
- **AND WHEN** later stale live-agent directories are still present in the same cleanup pass
- **THEN** the cleanup pass continues evaluating and removing the later stale directories
- **AND THEN** the overall cleanup result records which earlier directory failed removal

#### Scenario: Fresh directory remains distinct from failed stale removal in cleanup reporting
- **WHEN** stale-registry cleanup finishes with both a lease-fresh directory and a stale directory whose removal failed
- **THEN** the cleanup result distinguishes the failed removal from the preserved fresh directory
- **AND THEN** operators can tell whether a directory was preserved because it was live or because cleanup could not remove it
