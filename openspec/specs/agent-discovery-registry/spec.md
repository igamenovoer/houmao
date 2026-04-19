# agent-discovery-registry Specification

## Purpose
TBD - created by archiving change add-central-agent-registry. Update Purpose after archive.
## Requirements
### Requirement: Shared agent registry uses a fixed per-user root with isolated live-agent directories
The shared agent registry SHALL keep its fixed per-user root under the Houmao-owned home anchor and SHALL support an env-var override named `HOUMAO_GLOBAL_REGISTRY_DIR`.

When `HOUMAO_GLOBAL_REGISTRY_DIR` is set to an absolute directory path, the system SHALL use that value as the effective registry root instead of the home-relative default. The override SHALL support CI, tests, and similarly controlled environments.

#### Scenario: Env-var override relocates the shared registry root
- **WHEN** `HOUMAO_GLOBAL_REGISTRY_DIR` is set to an absolute directory path
- **THEN** the system uses that directory as the effective shared registry root

### Requirement: Shared registry records are strict, secret-free contracts that point to runtime-owned state

Each shared-registry `record.json` SHALL use one strict versioned schema.

That record schema SHALL include at minimum:
- an explicit top-level `schema_version` field set to `2` for v2 records
- the friendly `agent_name`
- the authoritative globally unique `agent_id`
- a stable-per-live-session `generation_id` that is reused across refreshes and resume-driven republishes of the same live session
- top-level `published_at` and `lease_expires_at` timestamps
- top-level `identity`, `runtime`, and `terminal` objects containing metadata sufficient to recognize the published agent and locate its runtime-owned artifacts
- a top-level `gateway` object only when externally useful live gateway metadata is available
- a top-level `mailbox` object when mailbox bindings are available

The record schema SHALL treat `agent_name` as friendly metadata rather than as a global uniqueness guarantee.

The record's `runtime` metadata SHALL include the manifest path required to locate runtime-owned session authority for that live session.

When mailbox bindings are available for the published session, the record SHALL publish mailbox identity metadata such as the active principal id and full mailbox address.

When a live gateway is attached, the record MAY publish exact live gateway connect metadata such as a loopback connect URL and protocol version.

Registry records MUST NOT embed copied session manifests, gateway queue state, mailbox contents, secrets, relaunch helper scripts, copied credentials, stable gateway roots, or stable gateway attach-path pointers as part of the required contract.

#### Scenario: Registry record publishes runtime pointers without copying runtime payloads

- **WHEN** the system publishes a shared-registry record for a runtime-managed session
- **THEN** the record includes secret-free pointers such as the manifest path and runtime session root
- **AND THEN** the record does not embed the full `manifest.json` payload, mailbox message content, or gateway durable queue data

#### Scenario: Detached session omits live gateway connect metadata

- **WHEN** a gateway-capable session has no live gateway currently attached
- **THEN** the shared-registry record may still publish the runtime manifest locator for that session
- **AND THEN** the record omits live gateway connect metadata that would imply an active listener exists

#### Scenario: Refresh keeps the same generation for the same live session

- **WHEN** the same live session republishes or refreshes its shared-registry record
- **THEN** the record keeps the same `generation_id` as earlier publications for that session
- **AND THEN** later resume-driven publication of that same live session does not manufacture a replacement generation

### Requirement: Shared-registry records persist authoritative agent identity rather than registry-specific agent keys
Shared-registry records SHALL persist the canonical `HOUMAO-...` agent identity together with the authoritative `agent_id`.

When the system bootstraps an initial `agent_id` from canonical agent identity, it SHALL use the full lowercase `md5("HOUMAO-<name>").hexdigest()` value.

#### Scenario: Initial authoritative agent id is derived from the HOUMAO canonical name
- **WHEN** the system bootstraps the initial `agent_id` for canonical agent name `HOUMAO-gpu`
- **THEN** it uses the full lowercase `md5("HOUMAO-gpu").hexdigest()` value as the authoritative identity

### Requirement: Shared registry agent-name input accepts an optional `AGENTSYS-` prefix and canonicalizes internally
The shared registry SHALL accept agent-name input in namespace-free form such as `gpu` or in canonical Houmao form such as `HOUMAO-gpu`.

When the caller omits the exact `HOUMAO-` prefix, the system SHALL canonicalize the input to `HOUMAO-<name>` before hashing, publication, duplicate detection, lookup, or record comparison.

#### Scenario: Namespace-free agent input is canonicalized to the HOUMAO form
- **WHEN** a caller resolves shared-registry agent input `gpu`
- **THEN** the system canonicalizes that input to `HOUMAO-gpu` before publication, duplicate detection, lookup, or record comparison

#### Scenario: Canonical HOUMAO agent input is accepted directly
- **WHEN** a caller resolves shared-registry agent input `HOUMAO-gpu`
- **THEN** the system treats `HOUMAO-gpu` as the canonical name

### Requirement: Shared registry publication is atomic and lease-based

The system SHALL publish shared-registry updates by writing a temporary file in the target live-agent directory and atomically replacing `record.json`.

Published records whose publication path uses a bounded lease SHALL continue to be treated as stale after their lease expires.

Published records for currently supported tmux-backed live agents SHALL use a dedicated long finite sentinel lease window so their discoverability does not expire at the ordinary 24-hour boundary or the existing 30-day joined-session boundary.

The tmux-backed sentinel lease SHALL apply to all current tmux-backed registry publications, including joined tmux sessions.

This change SHALL NOT introduce a new non-tmux registry publication contract.

Readers SHALL treat lease freshness rather than directory existence as the liveness signal for a published live agent.

If a publisher stops unexpectedly, the system MAY leave the live-agent directory behind, but readers SHALL treat records whose lease has expired as stale.

For tmux-backed live agents, stale removal SHALL rely on explicit teardown or cleanup-time local tmux liveness classification rather than on the ordinary 24-hour lease boundary.

Passive server discovery SHALL remain a probe-backed index that includes tmux-backed records only when they are lease-fresh and the owning tmux session is live on the local host.

If a publisher attempts to refresh or replace a live record for the same authoritative `agent_id` but a different fresh `generation_id`, the system SHALL reject that publication or otherwise prevent both generations from being treated as the same live identity concurrently.

The registry SHALL allow different fresh live records to share the same `agent_name` so long as they carry different authoritative `agent_id` values.

V1 SHALL tolerate the narrow compare-then-replace race window created by lock-free filesystem publication, but a publisher that later observes a different fresh `generation_id` owning the same authoritative `agent_id` SHALL surface that conflict and stand down from claiming shared-registry ownership for that id.

#### Scenario: Readers ignore an expired bounded-lease record

- **WHEN** a shared-registry record that uses bounded lease semantics still exists on disk
- **AND WHEN** its lease has expired
- **THEN** shared-registry resolution treats that record as stale rather than live
- **AND THEN** the lingering live-agent directory does not by itself make the agent discoverable

#### Scenario: Tmux-backed record remains discoverable past the old lease boundaries

- **WHEN** a tmux-backed live agent remains bound to a still-live owning tmux session
- **AND WHEN** more than 24 hours and more than 30 days have elapsed since the last registry publication
- **THEN** the published record still remains lease-fresh for ordinary discovery
- **AND THEN** local list and resolve flows continue to treat that tmux-backed agent as discoverable

#### Scenario: Passive discovery preserves its tmux liveness filter
- **WHEN** a tmux-backed live-agent record remains lease-fresh under the sentinel tmux-backed lease rule
- **AND WHEN** passive server discovery scans the shared registry
- **AND WHEN** the owning tmux session is absent on the local host
- **THEN** passive discovery excludes that record from its probe-backed index
- **AND THEN** ordinary local registry lookup semantics are unchanged by that passive-discovery exclusion

#### Scenario: Cleanup still removes a dead tmux-backed record despite the sentinel lease

- **WHEN** a tmux-backed live-agent directory exists under `live_agents/`
- **AND WHEN** its `record.json` remains lease-fresh under the sentinel tmux-backed lease rule
- **AND WHEN** the owning tmux session is absent on the local host during stale-registry cleanup
- **THEN** the cleanup tool classifies that directory as stale
- **AND THEN** the tmux-backed record is removable even though the ordinary lease window has not expired

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

When current-session discovery cannot use a valid tmux-published manifest pointer, resolution by authoritative `agent_id` SHALL be sufficient to recover the published `runtime.manifest_path` for manifest-first attach, resume, and relaunch flows.

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

#### Scenario: Current-session fallback uses agent id to recover the manifest locator

- **WHEN** a tmux-backed attach, resume, or relaunch flow has authoritative `HOUMAO_AGENT_ID=abc123`
- **AND WHEN** the tmux-published manifest pointer is missing, blank, or stale
- **AND WHEN** `live_agents/abc123/record.json` is valid and lease-fresh
- **THEN** the system resolves `runtime.manifest_path` from that record as the fallback manifest locator
- **AND THEN** it does not require gateway attach-path or gateway-root metadata to recover the session authority

#### Scenario: Registry root is not repurposed as mutable CAO home storage

- **WHEN** the system starts a launcher-managed CAO server while also using the shared registry for live-agent discovery
- **THEN** the shared registry root continues to contain registry-owned discovery state only
- **AND THEN** launcher-managed CAO home state and runtime task artifacts are stored elsewhere

### Requirement: The system provides a minimal operator-facing cleanup entrypoint for stale `live_agents/` directories
The system SHALL provide a local operator-facing cleanup entrypoint at `houmao-mgr admin cleanup registry` that classifies stale directories under `~/.houmao/registry/live_agents/` or the effective override root.

That tooling SHALL remove directories whose `record.json` is missing, malformed, or expired beyond a bounded grace period.

For tmux-backed records, that tooling SHALL perform a local tmux liveness probe by default. When a record is still lease-fresh but its tmux authority is absent on the local host, the cleanup tool SHALL classify that record as stale.

That tooling SHALL accept `--no-tmux-check`. When tmux checking is disabled, lease-fresh records SHALL remain preserved unless they are otherwise removable by malformed-state or expiry classification.

That tooling SHALL accept `--dry-run`. In dry-run mode, it SHALL classify removable, preserved, and blocked directories using the same rules as ordinary execution, but it SHALL NOT delete anything.

#### Scenario: Cleanup tool removes an expired live-agent directory
- **WHEN** a directory exists under `live_agents/`
- **AND WHEN** its `record.json` lease is expired beyond the cleanup grace period
- **AND WHEN** an operator invokes the cleanup entrypoint
- **THEN** the cleanup tool removes that directory
- **AND THEN** later directory listings better reflect only currently live published agents

#### Scenario: Default tmux probing removes a lease-fresh dead tmux-backed record
- **WHEN** a directory exists under `live_agents/`
- **AND WHEN** its `record.json` is valid and lease-fresh
- **AND WHEN** the record identifies a tmux-backed live authority whose tmux session is absent on the local host
- **AND WHEN** an operator invokes the cleanup entrypoint without `--no-tmux-check`
- **THEN** the cleanup tool classifies that directory as stale
- **AND THEN** the cleanup result reports local tmux liveness failure rather than lease expiry as the removal reason

#### Scenario: Default tmux probing preserves a lease-fresh live tmux-backed record
- **WHEN** a directory exists under `live_agents/`
- **AND WHEN** its `record.json` is valid and lease-fresh
- **AND WHEN** the record identifies a tmux-backed live authority whose tmux session exists on the local host
- **AND WHEN** an operator invokes the cleanup entrypoint without `--no-tmux-check`
- **THEN** the cleanup tool leaves that directory in place
- **AND THEN** the cleanup result reports that local tmux probing confirmed the owning session

#### Scenario: No-tmux-check flag preserves a lease-fresh live-agent directory without tmux probing
- **WHEN** a directory exists under `live_agents/`
- **AND WHEN** its `record.json` is valid and lease-fresh
- **AND WHEN** the operator invokes the cleanup entrypoint with `--no-tmux-check`
- **THEN** the cleanup tool leaves that directory in place unless another stale classification applies
- **AND THEN** the cleanup result distinguishes skipped tmux checking from probe-confirmed liveness

#### Scenario: Dry-run reports tmux-probe stale registry candidates without deleting them
- **WHEN** a directory exists under `live_agents/`
- **AND WHEN** its `record.json` is valid and lease-fresh
- **AND WHEN** the record identifies a tmux-backed live authority whose tmux session is absent on the local host
- **AND WHEN** an operator runs `houmao-mgr admin cleanup registry --dry-run`
- **THEN** the cleanup result reports that directory as removable
- **AND THEN** the directory still exists after the dry-run finishes

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
