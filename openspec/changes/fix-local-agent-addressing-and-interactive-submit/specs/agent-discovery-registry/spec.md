## ADDED Requirements

### Requirement: Shared registry identity inputs are filesystem-safe and URL-safe

The shared registry SHALL require both `agent_id` and `agent_name` to use forms that are safe to embed directly in filesystem path components and URL path segments.

The registry SHALL reject identity values that require path traversal handling, path-separator escaping, or URL-segment escaping in order to store or address the managed agent safely through Houmao-owned routes.

#### Scenario: Path-hostile agent id is rejected before publication

- **WHEN** a caller attempts to publish a live shared-registry record with `agent_id="../escape"`
- **THEN** the registry rejects that identity value before publication
- **AND THEN** the caller does not receive a live record that could be confused with filesystem traversal

#### Scenario: URL-hostile friendly name is rejected before publication

- **WHEN** a caller attempts to publish a live shared-registry record with an `agent_name` that contains characters requiring URL-segment escaping
- **THEN** the registry rejects that identity value before publication
- **AND THEN** managed-agent routes are not forced to special-case that name for basic path safety

## MODIFIED Requirements

### Requirement: Shared registry records are strict, secret-free contracts that point to runtime-owned state

Each shared-registry `record.json` SHALL use one strict versioned schema.

That record schema SHALL include at minimum:
- an explicit top-level `schema_version` field set to `2` for v2 records,
- the friendly `agent_name`,
- the authoritative globally unique `agent_id`,
- a stable-per-live-session `generation_id` that is reused across refreshes and resume-driven republishes of the same live session,
- top-level `published_at` and `lease_expires_at` timestamps,
- top-level `identity`, `runtime`, and `terminal` objects containing metadata sufficient to recognize the published agent and locate its runtime-owned artifacts,
- a top-level `gateway` object when stable or live gateway metadata is available,
- a top-level `mailbox` object when mailbox bindings are available.

The record schema SHALL treat `agent_name` as friendly metadata rather than as a global uniqueness guarantee.

When mailbox bindings are available for the published session, the record SHALL publish mailbox identity metadata such as the active principal id and full mailbox address.

When a live gateway is attached, the record MAY publish exact live gateway connect metadata such as a loopback connect URL and protocol version.

Registry records MUST NOT embed copied session manifests, gateway queue state, mailbox contents, or secrets.

#### Scenario: Registry record publishes runtime pointers without copying runtime payloads

- **WHEN** the system publishes a shared-registry record for a runtime-managed session
- **THEN** the record includes secret-free pointers such as the manifest path, runtime session root, and gateway attach path when available
- **AND THEN** the record does not embed the full `manifest.json` payload, mailbox message content, or gateway durable queue data

#### Scenario: Detached session omits live gateway connect metadata

- **WHEN** a gateway-capable session has no live gateway currently attached
- **THEN** the shared-registry record may still publish stable gateway pointers such as the attach-contract path
- **AND THEN** the record omits live gateway connect metadata that would imply an active listener exists

#### Scenario: Refresh keeps the same generation for the same live session

- **WHEN** the same live session republishes or refreshes its shared-registry record
- **THEN** the record keeps the same `generation_id` as earlier publications for that session
- **AND THEN** later resume-driven publication of that same live session does not manufacture a replacement generation

### Requirement: Shared-registry records persist authoritative agent identity rather than registry-specific agent keys

Each shared-registry `record.json` SHALL persist both the friendly `agent_name` and the authoritative globally unique `agent_id`.

The registry record schema for this capability SHALL replace the registry-specific `agent_key` field with authoritative `agent_id`.

The registry record SHALL continue to include the live terminal session metadata needed to locate the running session, but that terminal session name SHALL NOT be treated as authoritative managed-agent identity by contract.

The registry SHALL treat `agent_name` as user-facing lookup metadata and SHALL NOT require it to be unique across fresh live records.

#### Scenario: Shared-registry record persists both friendly and authoritative identity fields

- **WHEN** the system publishes a live shared-registry record for one agent
- **THEN** that `record.json` persists both friendly `agent_name` and authoritative `agent_id`
- **AND THEN** consumers can answer both “what is this agent called?” and “which exact globally unique agent identity is up?” from the same record

#### Scenario: Shared-registry terminal session metadata is not the source of truth for agent identity

- **WHEN** a published live record includes terminal session name `houmao-session-abc123`
- **AND WHEN** that same record persists friendly agent name `gpu`
- **THEN** consumers treat `agent_id` as authoritative identity and `gpu` as friendly managed-agent metadata
- **AND THEN** they do not assume `houmao-session-abc123` itself is managed-agent identity

#### Scenario: Legacy agent-key directories are ignored after cutover

- **WHEN** a registry root still contains an old `live_agents/<agent-key>/` directory from before the `agent_id` cutover
- **AND WHEN** the runtime or registry reader is operating under the new `agent_id`-based contract
- **THEN** that old directory is not part of a required lookup or migration path
- **AND THEN** users may remove that legacy directory manually

### Requirement: Shared registry publication is atomic and lease-based

The system SHALL publish shared-registry updates by writing a temporary file in the target live-agent directory and atomically replacing `record.json`.

Published records SHALL use a default 24-hour lease TTL in v1.

Readers SHALL treat lease freshness rather than directory existence as the liveness signal for a published live agent.

If a publisher stops unexpectedly, the system MAY leave the live-agent directory behind, but readers SHALL treat records whose lease has expired as stale.

If a publisher attempts to refresh or replace a live record for the same authoritative `agent_id` but a different fresh `generation_id`, the system SHALL reject that publication or otherwise prevent both generations from being treated as the same live identity concurrently.

The registry SHALL allow different fresh live records to share the same `agent_name` so long as they carry different authoritative `agent_id` values.

V1 SHALL tolerate the narrow compare-then-replace race window created by lock-free filesystem publication, but a publisher that later observes a different fresh `generation_id` owning the same authoritative `agent_id` SHALL surface that conflict and stand down from claiming shared-registry ownership for that id.

#### Scenario: Readers ignore an expired record

- **WHEN** a shared-registry record still exists on disk
- **AND WHEN** its lease has expired
- **THEN** shared-registry resolution treats that record as stale rather than live
- **AND THEN** the lingering live-agent directory does not by itself make the agent discoverable

#### Scenario: Same friendly name may appear on different live identities

- **WHEN** two fresh live registry records share `agent_name = "gpu"`
- **AND WHEN** those records carry different authoritative ids such as `abc123` and `def456`
- **THEN** the registry allows both records to remain published concurrently
- **AND THEN** callers must disambiguate by `agent_id` or another explicit metadata surface

#### Scenario: Fresh duplicate publication for one authoritative agent id is rejected

- **WHEN** one publisher attempts to publish `agent_id=abc123`
- **AND WHEN** a different fresh registry record already exists for `agent_id=abc123` with a different `generation_id`
- **THEN** the system rejects the second publication or forces that publisher to stand down
- **AND THEN** readers are not presented with two simultaneously live records for the same authoritative identity

### Requirement: Shared registry resolves live agents primarily by authoritative agent id

The system SHALL support direct resolution of a published live agent by authoritative `agent_id`.

When a caller resolves a live agent by friendly `agent_name` instead of `agent_id`, the system SHALL consult persisted registry metadata rather than deriving the lookup path from the name alone.

When more than one fresh live registry record shares the same friendly `agent_name` but carries different authoritative `agent_id` values, friendly-name lookup SHALL report ambiguity rather than silently choosing one record.

#### Scenario: Direct agent-id resolution returns the published record for that exact identity

- **WHEN** a caller resolves authoritative `agent_id=abc123`
- **AND WHEN** `live_agents/abc123/record.json` is valid and lease-fresh
- **THEN** the system returns the validated record for that exact authoritative identity
- **AND THEN** that result answers whether agent `abc123` is currently up

#### Scenario: Friendly-name lookup scans registry metadata rather than hashing name to path

- **WHEN** a caller resolves friendly agent name `gpu`
- **AND WHEN** exactly one fresh live registry record persists friendly agent name `gpu`
- **THEN** the system returns that one validated record
- **AND THEN** it does not require name lookup to derive the filesystem path from the friendly name directly

#### Scenario: Friendly-name lookup reports ambiguity when more than one live identity shares the same name

- **WHEN** a caller resolves friendly agent name `gpu`
- **AND WHEN** more than one fresh live registry record persists friendly agent name `gpu`
- **AND WHEN** those records carry different authoritative ids such as `abc123` and `def456`
- **THEN** the system reports friendly-name lookup as ambiguous
- **AND THEN** it requires the caller to disambiguate by `agent_id` or another explicit metadata surface

#### Scenario: Registry root is not repurposed as mutable CAO home storage

- **WHEN** the system starts a launcher-managed CAO server while also using the shared registry for live-agent discovery
- **THEN** the shared registry root continues to contain registry-owned discovery state only
- **AND THEN** launcher-managed CAO home state and runtime task artifacts are stored elsewhere
