# agent-discovery-registry Specification

## Purpose
TBD - created by archiving change add-central-agent-registry. Update Purpose after archive.
## Requirements

### Requirement: Shared agent registry uses a fixed per-user root with isolated live-agent directories
The system SHALL store shared agent registry state under the fixed per-user root `~/.houmao/registry`.

Implementation SHALL resolve that root as `.houmao/registry` beneath the current user's home directory, and SHALL obtain that home directory through `platformdirs`-aware path handling rather than a hardcoded Linux-specific home prefix.

When `AGENTSYS_GLOBAL_REGISTRY_DIR` is set, the system SHALL use that environment variable as the effective registry root instead of the home-relative default. The override SHALL support CI, tests, and similarly controlled environments.

Published live-agent directories SHALL live under `~/.houmao/registry/live_agents/<agent-id>/`, where `agent-id` is the authoritative globally unique agent id for that published agent.

That authoritative `agent_id` SHALL replace registry-specific `agent_key` as the registry's stable live-agent identity key.

When no explicit `agent_id` is supplied by the publishing runtime and no previously persisted `agent_id` exists for that same built or resumed agent, the initial `agent_id` SHALL be bootstrapped as the full lowercase `md5(canonical agent name).hexdigest()`.

When a previously persisted `agent_id` already exists for that same built or resumed agent, the publishing runtime SHALL reuse that persisted `agent_id` rather than recomputing it from the current canonical agent name.

Each published live agent SHALL own exactly one authoritative `record.json` file inside its directory.

Each published live-agent record SHALL persist both the canonical agent name and the authoritative `agent_id`.

The registry root SHALL remain a discovery-oriented locator layer. Mutable runtime session state, launcher-managed CAO home state, task-specific logs or outputs, and mailbox content MUST NOT be stored under the registry root as part of this capability.

The runtime directory associated with a published agent MAY live anywhere on the filesystem and SHALL NOT be required to live under `~/.houmao/registry`.

Legacy registry directories keyed by the retired `agent_key` are not part of a compatibility contract and MAY be removed manually by the user after cutover.

#### Scenario: Published agent uses a runtime directory outside the registry root
- **WHEN** a runtime-managed agent publishes shared-registry state for agent name `AGENTSYS-gpu`
- **AND WHEN** the authoritative `agent_id` for that publication is `deadbeef`
- **AND WHEN** that agent's runtime session root lives outside `~/.houmao/registry`
- **THEN** the shared registry stores only `live_agents/deadbeef/record.json` under `~/.houmao/registry`
- **AND THEN** the published runtime pointers continue to reference the external runtime-owned session directory

#### Scenario: Home-relative registry root is not derived from a hardcoded Linux path
- **WHEN** the system derives the effective filesystem path for `~/.houmao/registry`
- **THEN** it resolves the current user's home directory through `platformdirs`-aware path handling
- **AND THEN** it does not assume a hardcoded Linux home-directory prefix such as `/home/<user>`

#### Scenario: CI override redirects the registry root
- **WHEN** `AGENTSYS_GLOBAL_REGISTRY_DIR` is set to an absolute directory path
- **THEN** the system uses that path as the effective shared-registry root
- **AND THEN** it does not publish under the default home-relative `~/.houmao/registry` for that process

#### Scenario: Different agent ids do not share writable registry files
- **WHEN** two different agents publish records for two different authoritative `agent_id` values
- **THEN** each agent writes only inside its own `~/.houmao/registry/live_agents/<agent-id>/` directory
- **AND THEN** the registry does not require a shared writable `index.json` or shared SQLite file for publication

#### Scenario: Initial default agent id uses the full MD5 hex digest of the canonical agent name
- **WHEN** the system bootstraps the initial `agent_id` for canonical agent name `AGENTSYS-gpu`
- **AND WHEN** no explicit or previously persisted `agent_id` exists for that same built or resumed agent
- **THEN** it uses the full lowercase `md5("AGENTSYS-gpu").hexdigest()` value as the authoritative identity
- **AND THEN** it does not truncate that digest before path derivation

#### Scenario: Persisted agent id wins over later name-derived recomputation during publication
- **WHEN** a publishing runtime already has persisted agent metadata with `agent_id=abc123`
- **AND WHEN** that same agent is later republished under a canonical agent name that could otherwise produce a different bootstrap id
- **THEN** the registry publication reuses `agent_id=abc123`
- **AND THEN** it does not silently replace that authoritative identity by recomputing from the current canonical agent name

#### Scenario: Different names sharing one explicit agent id trigger a warning and one registry directory
- **WHEN** the shared registry already contains `live_agents/abc123/record.json` for canonical agent name `AGENTSYS-gpu`
- **AND WHEN** a later publication explicitly reuses `agent_id=abc123` with canonical agent name `AGENTSYS-editor`
- **THEN** the system emits a warning that different canonical names are sharing one authoritative `agent_id`
- **AND THEN** it continues to publish into `~/.houmao/registry/live_agents/abc123/record.json`

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

### Requirement: Shared registry agent-name input accepts an optional `AGENTSYS-` prefix and canonicalizes internally
The system SHALL accept shared-registry agent-name input in either of these forms:
- the canonical reserved-prefix form such as `AGENTSYS-gpu`, or
- the namespace-free form such as `gpu`.

When the caller omits the exact `AGENTSYS-` prefix, the system SHALL canonicalize the input to `AGENTSYS-<name>` before hashing, publication, duplicate detection, lookup, or record comparison.

Shared-registry records SHALL persist the canonical reserved-prefix form in `agent_name`.

#### Scenario: Namespace-free input resolves to the canonical stored name
- **WHEN** a caller resolves shared-registry agent input `gpu`
- **THEN** the system canonicalizes that input to `AGENTSYS-gpu` before publication, duplicate detection, lookup, or record comparison
- **AND THEN** lookup targets the same stored record that would be used for input `AGENTSYS-gpu`

#### Scenario: Canonical input is preserved
- **WHEN** a caller resolves shared-registry agent input `AGENTSYS-gpu`
- **THEN** the system treats `AGENTSYS-gpu` as the canonical name
- **AND THEN** it does not create a second logical identity distinct from input `gpu`

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

### Requirement: The system provides a minimal operator-facing cleanup entrypoint for stale `live_agents/` directories
The system SHALL provide a minimal operator-facing cleanup entrypoint that removes stale directories under `~/.houmao/registry/live_agents/` or the effective override root when those directories no longer correspond to lease-fresh live agents.

That tooling SHALL remove directories whose `record.json` is missing, malformed, or expired beyond a bounded grace period.

#### Scenario: Cleanup tool removes an expired live-agent directory
- **WHEN** a directory exists under `live_agents/`
- **AND WHEN** its `record.json` lease is expired beyond the cleanup grace period
- **AND WHEN** an operator invokes the cleanup entrypoint
- **THEN** the cleanup tool removes that directory
- **AND THEN** later directory listings better reflect only currently live published agents

#### Scenario: Cleanup tool preserves a lease-fresh live-agent directory
- **WHEN** a directory exists under `live_agents/`
- **AND WHEN** its `record.json` is valid and lease-fresh
- **THEN** the cleanup tool leaves that directory in place
- **AND THEN** the currently running published agent remains discoverable

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

### Requirement: Agent-discovery registry specs do not describe current canonicalization in terms of retired `agent_key`
The shared agent discovery registry specification SHALL describe current canonicalization, publication, and lookup behavior in terms of canonical agent names and authoritative `agent_id`, and SHALL NOT describe retired `agent_key` derivation as part of the live post-cutover flow.

Historical references to legacy `agent_key` directories may remain only when they are explicitly marked as pre-cutover cleanup context rather than as the active contract.

#### Scenario: Canonical name input is normalized without implying a current `agent_key` lookup path
- **WHEN** a caller resolves shared-registry agent input `gpu`
- **THEN** the spec describes that input as canonicalized to `AGENTSYS-gpu` before publication, duplicate detection, lookup, or record comparison
- **AND THEN** it does not describe the live canonicalization flow as deriving a current `agent_key`

#### Scenario: Legacy agent-key references remain clearly historical
- **WHEN** the spec mentions a legacy `live_agents/<agent-key>/` directory
- **THEN** that mention is explicitly framed as pre-cutover cleanup or historical context
- **AND THEN** readers are not left to infer that `agent_key` still participates in the active registry identity contract

### Requirement: Shared-registry creation follows launch authority and cleanup follows the terminating actor
The system SHALL create a shared-registry record for a live agent according to the authority that launched or admitted that agent.

The launch authority SHALL be persisted in runtime-readable session or authority metadata so runtime and `houmao-server` consult the same signal before any shared-registry publish or refresh attempt.

For agents created or admitted through `houmao-server`-owned authority, `houmao-server` SHALL create and refresh the shared-registry record for that agent.

For direct runtime-owned workflows outside `houmao-server`-owned admission, runtime publication MAY continue to create and refresh the shared-registry record for that live agent.

Discovery or later management by `houmao-server` SHALL NOT by itself transfer shared-registry creation responsibility or imply that `houmao-server` must republish an already valid live entry.

The system SHALL assign shared-registry cleanup responsibility to the actor that terminates the live agent. If a user or external launcher terminates the agent outside `houmao-server` control, that same actor remains responsible for removing or repairing the registry entry.

The system SHALL NOT infer launch authority or cleanup responsibility from current shared-registry contents alone.

This launch-and-cleanup split SHALL NOT change the pointer-oriented nature of the shared registry. Regardless of who writes or clears the record, the shared-registry entry SHALL remain a secret-free locator layer that points at runtime-owned or server-owned artifacts rather than copying queue state, mailbox content, or other mutable per-agent control state into the registry.

#### Scenario: Server-launched managed headless agent is published by `houmao-server`
- **WHEN** `houmao-server` launches and admits a managed headless agent through its own launch authority
- **THEN** `houmao-server` creates and refreshes the shared-registry record for that agent
- **AND THEN** the registry record continues to publish only secret-free pointers rather than per-agent queue or mailbox state

#### Scenario: Pair-managed server-admitted TUI agent is published by `houmao-server`
- **WHEN** a TUI agent is admitted into `houmao-server` authority through the supported pair-managed launch path
- **THEN** `houmao-server` creates and refreshes the shared-registry record for that agent
- **AND THEN** runtime-owned session and gateway pointers remain the source material for that published record rather than a copied runtime payload

#### Scenario: Direct runtime-owned workflow continues runtime publication
- **WHEN** a live tmux-backed session is created through a direct runtime-owned workflow outside `houmao-server`-owned admission
- **THEN** the runtime may continue creating and refreshing the shared-registry record for that session
- **AND THEN** the registry does not require a running `houmao-server` instance solely to publish that direct runtime-owned session

#### Scenario: Runtime consults persisted launch authority and defers registry writes
- **WHEN** a runtime-managed session started under `houmao-server` authority reads launch metadata showing that `houmao-server` launched that session
- **THEN** the runtime does not independently publish or refresh the shared-registry record for that session
- **AND THEN** it still preserves the pointer artifacts that `houmao-server` needs for its own registry publication

#### Scenario: Server discovery does not republish an externally launched live agent
- **WHEN** `houmao-server` reads a valid shared-registry entry for an externally launched live agent
- **THEN** `houmao-server` may manage that agent through its APIs
- **AND THEN** it does not republish or overwrite the existing registry entry solely because discovery occurred

#### Scenario: Terminating actor clears or repairs the registry entry
- **WHEN** an externally launched live agent is terminated through a `houmao-server` termination path after discovery
- **THEN** `houmao-server` clears or updates the shared-registry entry as part of keeping registry integrity
- **AND THEN** cleanup responsibility follows the terminating actor rather than the original discovering actor

#### Scenario: Manual external termination keeps cleanup responsibility external
- **WHEN** an externally launched live agent is terminated manually outside `houmao-server` control
- **THEN** the external actor remains responsible for removing or repairing the shared-registry entry
- **AND THEN** the system does not assume discovery alone transferred cleanup ownership to `houmao-server`

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
