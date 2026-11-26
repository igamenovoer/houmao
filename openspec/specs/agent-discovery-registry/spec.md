# agent-discovery-registry Specification

## Purpose
Resolve managed agents by stable identity through a per-user registry. Track live runtime and gateway presence separately from durable addresses, mailbox membership, and owner execution locators.
## Requirements
### Requirement: Shared agent registry uses a fixed per-user root with isolated live-agent directories
The shared agent registry SHALL keep its fixed per-user root under the platformdirs user config path for app name `houmao` and no app author, and SHALL support an env-var override named `HOUMAO_GLOBAL_REGISTRY_DIR`.

On Linux, the default shared registry root is expected to be `~/.config/houmao/registry`.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

When `HOUMAO_GLOBAL_REGISTRY_DIR` is set to an absolute directory path, the system SHALL use that value as the effective registry root instead of the platformdirs-derived default. The override SHALL support CI, tests, and similarly controlled environments.

#### Scenario: Env-var override relocates the shared registry root
- **WHEN** `HOUMAO_GLOBAL_REGISTRY_DIR` is set to an absolute directory path
- **THEN** the system uses that directory as the effective shared registry root

#### Scenario: Default registry root uses platformdirs config path
- **WHEN** `HOUMAO_GLOBAL_REGISTRY_DIR` is unset
- **THEN** the system derives the effective shared registry root from the platformdirs user config path for `houmao`
- **AND THEN** on ordinary Linux systems the path is `~/.config/houmao/registry`
- **AND THEN** the default is not `~/.houmao/registry`

### Requirement: Shared registry records are strict, secret-free contracts that point to runtime-owned state
Each local runtime-presence `record.json` SHALL use the current strict versioned schema and include its schema version, friendly name, authoritative `agent_id`, stable-per-live-session generation, publication/lease information, identity metadata, runtime pointers, and terminal metadata. Names SHALL be friendly metadata rather than a global uniqueness guarantee. The local record SHALL retain its manifest locator. Externally useful live gateway coordinates SHALL remain optional presence metadata.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

When mail is configured, the record SHALL publish separate `mailboxes.offline` and `mailboxes.online` identity summaries and the derived canonical mail identity. Summaries SHALL contain owner/channel/binding scope, address, revision, and safe availability information; they SHALL NOT publish credential files or secret-resolution inputs.

Records SHALL NOT embed manifests, gateway queues, mailbox or memory contents, credentials, authorization headers, relaunch scripts, stable gateway roots, or stable attach-path pointers. Durable remote offline membership SHALL use the separate registry-host membership contract rather than pretending to be a local tmux presence record.

#### Scenario: Registry record publishes runtime pointers without copying runtime payloads
- **WHEN** a local runtime-managed session publishes its presence record
- **THEN** the record contains safe manifest/session locators and current mail identity summaries
- **AND THEN** it omits full manifests, message contents, credentials, and gateway queue payloads

#### Scenario: Detached session omits live gateway connect metadata
- **WHEN** a gateway-capable session has no live gateway attached
- **THEN** its known identity and configured mailbox summaries remain available
- **AND THEN** the record omits coordinates implying that a gateway is listening

#### Scenario: Refresh keeps the same generation for the same live session
- **WHEN** the same session refreshes its presence record after a mailbox update
- **THEN** it preserves the existing runtime generation and agent ID
- **AND THEN** it publishes the current binding revisions and canonical mail identity

### Requirement: Shared-registry records persist authoritative agent identity rather than registry-specific agent keys
Shared-registry records SHALL persist the authoritative opaque `agent_id` and friendly agent name. Fresh creation SHALL default to UUID generation. Explicit `name-hash` creation SHALL use the existing deterministic normalized-name derivation. Publication and lookup SHALL use the resolved persisted ID and SHALL NOT rederive it from names or mail addresses.

#### Scenario: Initial authoritative agent id is derived from the HOUMAO canonical name
- **WHEN** creation explicitly selects `name-hash` for canonical name `HOUMAO-gpu`
- **THEN** it uses the full lowercase existing normalized-name hash as its authoritative ID
- **AND THEN** later publication preserves that selected ID

#### Scenario: Default UUID is the registry key
- **WHEN** default agent creation generates a UUID
- **THEN** the registry publishes and resolves that exact ID
- **AND THEN** its path is not obtained by hashing the agent's friendly name

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

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

Published records for currently supported tmux-backed live agents SHALL use a dedicated long finite sentinel lease window so their discoverability does not expire at the ordinary 24-hour or 30-day boundary.

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

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

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
The system SHALL provide a local operator-facing cleanup entrypoint at `houmao-mgr admin cleanup registry` that classifies stale directories under `<platformdirs user config>/registry/live_agents/` or the effective override root.

That tooling SHALL remove directories whose `record.json` is missing, malformed, or expired beyond a bounded grace period.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

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

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

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

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

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

### Requirement: Shared-registry cleanup mutates only lexical registry entries
Shared-registry record removal and stale-record cleanup SHALL treat `live_agents/<agent_id>/` entries as lexical registry-owned artifacts.

Registry cleanup SHALL NOT follow a symlinked record directory to choose the recursive deletion target.

#### Scenario: Removing a symlink-backed registry entry preserves the external target
- **WHEN** one shared-registry `live_agents/<agent_id>` entry exists as a symlink to a directory outside the registry root
- **AND WHEN** Houmao removes or cleans up that registry entry
- **THEN** Houmao removes only the lexical registry entry under `live_agents/`
- **AND THEN** it does not delete or rewrite the symlink target directory

#### Scenario: Malformed registry state does not widen cleanup authority
- **WHEN** shared-registry cleanup encounters one malformed or stale live-agent entry
- **THEN** cleanup stays confined to registry-owned lexical paths
- **AND THEN** malformed metadata does not authorize deletion outside the registry root

### Requirement: Shared registry preserves known agent addresses independently from live gateway presence
The shared registry SHALL provide enough secret-free metadata for callers to resolve a known managed agent by authoritative `agent_id` even when no live gateway is currently attached.

Known-agent address metadata SHALL include the authoritative `agent_id`, canonical `agent_name`, lifecycle state when available, relaunchability when available, and safe runtime pointers needed by supported relaunch or status flows.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

Known-agent address metadata SHALL treat live gateway coordinates, tmux session handles, live generation identifiers, and leases as volatile presence data rather than durable addresses.

Known-agent address metadata SHALL NOT include gateway queues, AG-UI event payloads, mailbox contents, memory contents, raw terminal history, credentials, authorization headers, cookies, bearer tokens, or copied manifests.

#### Scenario: Known agent remains addressable without a live gateway
- **WHEN** the registry contains known metadata for `agent_id=abc123`
- **AND WHEN** no fresh live-agent record for `abc123` has a gateway object
- **THEN** registry resolution can still identify `abc123` as a known agent address
- **AND THEN** the result does not invent live gateway coordinates

#### Scenario: Live record overlays current gateway presence
- **WHEN** the registry contains known metadata for `agent_id=abc123`
- **AND WHEN** a fresh live-agent record for `abc123` publishes gateway host and port
- **THEN** registry resolution reports `abc123` as known and live
- **AND THEN** the current gateway coordinates are reported as volatile live presence metadata

#### Scenario: Known-agent metadata stays secret-free
- **WHEN** a managed agent has mailbox bindings, memory pages, terminal output, and credential material
- **THEN** known-agent address metadata omits mailbox contents, memory contents, raw terminal history, and credentials

### Requirement: Friendly agent-name resolution reports known-agent ambiguity
The shared registry SHALL support friendly `agent_name` lookup across known-agent metadata.

When exactly one known agent matches a friendly `agent_name`, the registry SHALL return that known agent's authoritative `agent_id`.

When more than one known agent matches the same friendly `agent_name`, the registry SHALL report ambiguity and SHALL NOT choose one by publication time, gateway liveness, tmux liveness, or filesystem ordering.

#### Scenario: Unique known name resolves to agent id
- **WHEN** known-agent metadata contains exactly one agent named `HOUMAO-alpha`
- **AND WHEN** a caller resolves friendly name `alpha`
- **THEN** the registry returns the matching authoritative `agent_id`

#### Scenario: Ambiguous known name is not guessed
- **WHEN** known-agent metadata contains two agents named `HOUMAO-alpha` with different authoritative ids
- **AND WHEN** a caller resolves friendly name `alpha`
- **THEN** the registry reports an ambiguous-name result
- **AND THEN** the result requires the caller to select an `agent_id`

### Requirement: Durable mail membership is separate from local runtime presence
Local presence cleanup SHALL NOT delete offline membership, release addresses, or infer remote agent absence from local tmux probes. Registry-host membership SHALL be resolvable by `agent_id` while the body is stopped. A remote locator SHALL remain remote metadata rather than a path the registry host must open locally.

#### Scenario: Live cleanup preserves offline address ownership
- **WHEN** cleanup removes a dead local presence record or finds no local tmux session for a remote member
- **THEN** the durable membership and offline address claim remain intact

#### Scenario: Remote member has no registry-host manifest path
- **WHEN** a member runs on a different host with its own runtime paths
- **THEN** directory lookup can return its membership and safe remote presence
- **AND THEN** it does not require a readable local copy of that member's manifest

### Requirement: Canonical mail summaries are projections of binding authority
Registry mail summaries SHALL reflect configured channel bindings and online-first canonical mail identity. They SHALL NOT act as an independent mailbox configuration source. Delayed or failed publication SHALL be observable and repairable without inventing bindings or changing agent identity.

#### Scenario: Provider outage leaves canonical summary unchanged
- **WHEN** online health degrades while the online binding remains configured
- **THEN** the summary retains the online canonical address and separately reports health

#### Scenario: Projection update fails after a binding change
- **WHEN** a binding commit succeeds but registry summary publication fails
- **THEN** the operation reports the projection failure safely
- **AND THEN** later reconciliation republishes the authoritative binding state without creating another agent

### Requirement: Owner lifecycle records preserve execution bindings

Owner-side managed-agent lifecycle records SHALL identify the persisted execution binding alongside logical agent identity and existing runtime pointers. Publication, resume, stop, and relaunch SHALL preserve that binding independently of volatile presence. Registry content SHALL remain secret-free and SHALL NOT itself grant delegation or replace owner-side manifest authority.

#### Scenario: Stopped agent retains execution ownership

- **WHEN** an execution-bound managed agent stops while retaining relaunchable runtime artifacts
- **THEN** its owner lifecycle record preserves the execution binding and logical agent ID
- **AND THEN** current live handles are cleared according to the existing stopped lifecycle contract

#### Scenario: Relaunch updates presence without changing owner

- **WHEN** an execution-bound managed agent is relaunched successfully
- **THEN** owner publication reports the new generation with the original execution binding
- **AND THEN** it does not replace execution ownership with the invoking controller's account

### Requirement: Operator execution locators remain separate from runtime presence and communication imports

The operator registry SHALL store executor-managed locators separately from owner-local runtime records and external communication-only imports. A locator SHALL contain the authoritative agent ID, friendly name, configured route reference, captured execution binding, and safe owner lookup information. It SHALL omit credentials, copied manifests, mutable runtime state, and authority-implying caller-local control endpoints.

#### Scenario: Delegated launch publishes a routing locator after owner admission

- **WHEN** a delegated launch succeeds and the owner returns its admitted binding and managed-agent identity
- **THEN** the operator publishes a locator for that identity in the execution-locator collection
- **AND THEN** the actual manifest and runtime lifecycle record remain owned by the target context

#### Scenario: Foreign path and loopback endpoint are not local authority

- **WHEN** a target context reports a manifest path, home path, or owner-loopback gateway address
- **THEN** the operator treats those values as context-qualified metadata
- **AND THEN** it does not open the path locally or connect to the same loopback port on the operator's host as a substitute

#### Scenario: Conflicting bindings cannot replace an existing logical identity

- **WHEN** publication would associate one known authoritative agent ID with a different execution binding
- **THEN** publication reports an identity/context conflict
- **AND THEN** it does not silently overwrite the existing locator or claim a second owner

### Requirement: Local registry cleanup cannot infer foreign liveness or remove owner state

Local stale-presence cleanup SHALL NOT classify execution locators using caller-local tmux probes or local lease rules. A failed owner connection SHALL indicate unavailable or unverified state rather than stopped state. Removing an operator locator SHALL remove only the lexical locator entry and SHALL NOT stop an agent, remove owner artifacts, or change communication-only imports or offline membership.

#### Scenario: Local tmux absence preserves execution locator

- **WHEN** a local cleanup pass finds no caller-local tmux session corresponding to an execution locator
- **THEN** it preserves that locator without inferring that the owner-side agent is dead

#### Scenario: Locator removal leaves owner runtime intact

- **WHEN** an operator removes an execution locator
- **THEN** only that operator-owned lexical registry entry is removed
- **AND THEN** the owner-side agent, manifest, runtime files, and independent communication records remain intact

### Requirement: Failed operator publication preserves an admitted owner launch

If owner launch succeeds but operator locator publication fails, Houmao SHALL report partial success with the admitted agent identity and execution context. It SHALL NOT create another agent to repair publication. Explicit reconciliation through the authorized owner route SHALL be able to recover and publish that agent's locator without repeating birth.

#### Scenario: Operator cannot publish after owner launch

- **WHEN** owner launch completes but the operator registry cannot accept the returned locator
- **THEN** the result identifies the admitted agent and reports failed locator publication
- **AND THEN** the existing owner agent remains the recovery target without an automatic second launch

#### Scenario: Explicit reconciliation repairs only the routing locator

- **WHEN** the operator explicitly reconciles an admitted agent through its authorized owner route
- **THEN** Houmao verifies that owner's agent identity and binding before publishing the locator
- **AND THEN** it does not repeat launch or replace the owner runtime state

### Requirement: Live gateway advertisements expose a non-secret remote descriptor

Live gateway presence SHALL support an advertised URL, protocol, target and presence identity, current `admin_mode`, supported proof protocol and challenge location, and enabled public actions. The descriptor SHALL omit key membership, per-caller grants, credentials, signatures, challenge material, and private runtime state. Listener coordinates SHALL remain separately qualified local metadata.

#### Scenario: Owner exports a remote endpoint without sharing runtime files

- **WHEN** an owner publishes a bound gateway with public input enabled
- **THEN** an external hub can discover the advertised URL, available public notification and prompt actions, and whether `admin_mode` is `open`, `keyed`, or `unavailable`
- **AND THEN** it can identify the supported proof protocol and challenge location without obtaining a challenge, signature, or decision about a protected action

#### Scenario: Proxy endpoint differs from local listener

- **WHEN** the owner-local gateway listens on loopback behind an explicitly configured HTTPS proxy
- **THEN** the remote descriptor publishes that HTTPS URL
- **AND** local listener metadata does not replace it with caller-local loopback

### Requirement: Gateway advertisement follows live presence without owning access policy

Advertised gateway availability SHALL be ephemeral presence metadata. Gateway stop or detach SHALL clear or invalidate live advertised availability while preserving logical identity and independently retained owner-side access configuration. Publication and discovery SHALL NOT become policy authority or infer that a stopped agent is controllable from its prior advertised mode.

#### Scenario: Gateway detaches while its agent remains known

- **WHEN** a protected gateway detaches from a known agent
- **THEN** live discovery ceases advertising a reachable gateway instance
- **AND** retained owner-side protection and execution ownership remain unchanged

#### Scenario: Discovery publication lags a configuration change

- **WHEN** a published descriptor is stale or cannot be refreshed
- **THEN** clients treat it as possibly unavailable locator metadata
- **AND** the gateway applies current owner policy and verifies the exact target and execution authority independently

#### Scenario: Discovery still advertises open access after first enrollment

- **WHEN** discovery's last publication predates first-key registration
- **THEN** the request must satisfy the current keyed policy for the selected target and action

### Requirement: Remote descriptors grant no credentials or lifecycle rights

Discovery SHALL treat endpoint metadata as a locator. Protected credential selection, execution delegation, and lifecycle control SHALL require their own authority. Communication-only imports SHALL retain their existing scope. Foreign paths and loopback addresses SHALL remain owner-context metadata. Changed advertised target or endpoint bindings SHALL require explicit client rebinding before credential-bearing access.

#### Scenario: Communication import contains an authenticated gateway URL

- **WHEN** a communication-only import references a gateway with public input enabled
- **THEN** it can locate and call the available public operations
- **AND** each protected operation requires a current grant for the selected domain, resource, and action, and execution delegation requires its existing authority

#### Scenario: Registry descriptor is replaced with another origin

- **WHEN** discovery returns a different origin or base path for an existing credential-bearing client binding
- **THEN** the existing credential is not automatically attached to that replacement endpoint

#### Scenario: Owner loopback port also exists on the caller host

- **WHEN** a remote execution record contains owner-local loopback listener coordinates
- **THEN** remote discovery does not authorize connecting to the same port on the caller host as a substitute

### Requirement: Retired joined-session records convey no live presence
A record for a retired `joined_tmux` manifest SHALL confer no active discovery, live gateway coordinates, or runtime control even while its lease is fresh. Known address and durable mail membership MAY remain available through their independent read and delivery contracts.

#### Scenario: A retired record is still published
- **WHEN** a fresh registry record points to a retired joined-session manifest
- **THEN** the active manager list and passive live discovery omit that runtime
- **AND THEN** selected runtime control refuses the retired authority without substituting another target
- **AND THEN** discovery does not modify the record or the runtime's files

#### Scenario: A known address outlives retired presence
- **WHEN** a caller resolves a known address or uses a valid durable mail membership for a retired joined session
- **THEN** known-address resolution may identify the agent without live gateway coordinates
- **AND THEN** mail delivery continues under the mailbox authority's existing rules

### Requirement: Supported managed presence identifies the run mode and native surface

A current local managed presence record SHALL identify the selected tool, run mode, concrete backend, managed generation, and optional native human surface consistently with the current manifest. Public Web location metadata SHALL contain only a token-free origin and the bound session identity. A service control socket, stdio handle, or supervisor pane SHALL confer no human interface.

#### Scenario: Web presence survives gateway detach

- **WHEN** an operator detaches the gateway from a live owned Web host
- **THEN** the record retains its safe browser reference and mode and omits any discarded gateway endpoint

#### Scenario: A managed terminal publishes its identity

- **WHEN** a supported Houmao launch starts a managed TUI with verified terminal authority
- **THEN** its new record reports tui and the verified terminal surface

#### Scenario: A record disagrees with the manifest

- **WHEN** a service record claims a terminal UI or names a backend belonging to another mode
- **THEN** the reader reports unusable authority before routing an operation
