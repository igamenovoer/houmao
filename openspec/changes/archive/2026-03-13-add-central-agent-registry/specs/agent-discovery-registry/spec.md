## ADDED Requirements

### Requirement: Shared agent registry uses a fixed per-user root with isolated live-agent directories
The system SHALL store shared agent registry state under the fixed per-user root `~/.houmao/registry`.

Implementation SHALL resolve that root as `.houmao/registry` beneath the current user's home directory, and SHALL obtain that home directory through `platformdirs`-aware path handling rather than a hardcoded Linux-specific home prefix.

When `AGENTSYS_GLOBAL_REGISTRY_DIR` is set, the system SHALL use that environment variable as the effective registry root instead of the home-relative default. The override SHALL support CI, tests, and similarly controlled environments.

Published live-agent directories SHALL live under `~/.houmao/registry/live_agents/<agent-key>/`, where `agent-key` is the full lowercase SHA-256 hex digest of the canonical globally unique published agent name rather than the raw name itself.

Each published live agent SHALL own exactly one authoritative `record.json` file inside its directory.

The runtime directory associated with a published agent MAY live anywhere on the filesystem and SHALL NOT be required to live under `~/.houmao/registry`.

#### Scenario: Published agent uses a runtime directory outside the registry root
- **WHEN** a runtime-managed agent publishes shared-registry state for agent name `AGENTSYS-gpu`
- **AND WHEN** that agent's runtime session root lives outside `~/.houmao/registry`
- **THEN** the shared registry stores only the hashed live-agent directory and `record.json` under `~/.houmao/registry/live_agents/`
- **AND THEN** the published runtime pointers continue to reference the external runtime-owned session directory

#### Scenario: Home-relative registry root is not derived from a hardcoded Linux path
- **WHEN** the system derives the effective filesystem path for `~/.houmao/registry`
- **THEN** it resolves the current user's home directory through `platformdirs`-aware path handling
- **AND THEN** it does not assume a hardcoded Linux home-directory prefix such as `/home/<user>`

#### Scenario: CI override redirects the registry root
- **WHEN** `AGENTSYS_GLOBAL_REGISTRY_DIR` is set to an absolute directory path
- **THEN** the system uses that path as the effective shared-registry root
- **AND THEN** it does not publish under the default home-relative `~/.houmao/registry` for that process

#### Scenario: Different agent names do not share writable registry files
- **WHEN** two different agents publish records for two different globally unique agent names
- **THEN** each agent writes only inside its own `~/.houmao/registry/live_agents/<agent-key>/` directory
- **AND THEN** the registry does not require a shared writable `index.json` or shared SQLite file for publication

#### Scenario: Canonical agent key uses the full SHA-256 hex digest
- **WHEN** the system derives `agent-key` for canonical agent name `AGENTSYS-gpu`
- **THEN** it uses the full lowercase `sha256("AGENTSYS-gpu").hexdigest()` value as the live-agent directory name
- **AND THEN** it does not truncate that digest before path derivation

### Requirement: Shared registry records are strict, secret-free contracts that point to runtime-owned state
Each shared-registry `record.json` SHALL use one strict versioned schema.

That record schema SHALL include at minimum:
- an explicit top-level `schema_version` field set to `1` for v1 records,
- the globally unique `agent_name`,
- the deterministic `agent_key`,
- a stable-per-live-session `generation_id` that is reused across refreshes and resume-driven republishes of the same live session,
- top-level `published_at` and `lease_expires_at` timestamps,
- top-level `identity`, `runtime`, and `terminal` objects containing metadata sufficient to recognize the published agent and locate its runtime-owned artifacts,
- a top-level `gateway` object when stable or live gateway metadata is available,
- a top-level `mailbox` object when mailbox bindings are available.

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

### Requirement: Shared registry agent-name input accepts an optional `AGENTSYS-` prefix and canonicalizes internally
The system SHALL accept shared-registry agent-name input in either of these forms:
- the canonical reserved-prefix form such as `AGENTSYS-gpu`, or
- the namespace-free form such as `gpu`.

When the caller omits the exact `AGENTSYS-` prefix, the system SHALL canonicalize the input to `AGENTSYS-<name>` before hashing, publication, duplicate detection, lookup, or record comparison.

Shared-registry records SHALL persist the canonical reserved-prefix form in `agent_name`.

#### Scenario: Namespace-free input resolves to the canonical stored name
- **WHEN** a caller resolves shared-registry agent input `gpu`
- **THEN** the system canonicalizes that input to `AGENTSYS-gpu` before deriving `agent_key`
- **AND THEN** lookup targets the same stored record that would be used for input `AGENTSYS-gpu`

#### Scenario: Canonical input is preserved
- **WHEN** a caller resolves shared-registry agent input `AGENTSYS-gpu`
- **THEN** the system treats `AGENTSYS-gpu` as the canonical name
- **AND THEN** it does not create a second logical identity distinct from input `gpu`

### Requirement: Shared registry publication is atomic and lease-based
The system SHALL publish shared-registry updates by writing a temporary file in the target live-agent directory and atomically replacing `record.json`.

Published records SHALL use a default 24-hour lease TTL in v1.

Readers SHALL treat lease freshness rather than directory existence as the liveness signal for a published live agent.

If a publisher stops unexpectedly, the system MAY leave the hashed live-agent directory behind, but readers SHALL treat records whose lease has expired as stale.

If a publisher attempts to claim an agent name whose record is still fresh for a different `generation_id`, the system SHALL reject that publication or otherwise prevent both generations from being treated as concurrently live for the same agent name.

V1 SHALL tolerate the narrow compare-then-replace race window created by lock-free filesystem publication, but a publisher that later observes a different fresh `generation_id` owning the same canonical `agent_name` SHALL surface that conflict and stand down from claiming shared-registry ownership for that name.

#### Scenario: Readers ignore an expired record
- **WHEN** a shared-registry record still exists on disk
- **AND WHEN** its lease has expired
- **THEN** shared-registry resolution treats that record as stale rather than live
- **AND THEN** the lingering live-agent directory does not by itself make the agent discoverable

#### Scenario: Fresh duplicate publication for one agent name is rejected
- **WHEN** one publisher attempts to publish `agent_name=AGENTSYS-gpu`
- **AND WHEN** a different fresh registry record already exists for `AGENTSYS-gpu` with a different `generation_id`
- **THEN** the system rejects the second publication or forces that publisher to stand down
- **AND THEN** readers are not presented with two simultaneously live records for the same agent name

#### Scenario: Losing publisher stands down after detecting a conflicting fresh generation
- **WHEN** two publishers race for the same canonical `agent_name`
- **AND WHEN** one publisher later refreshes and discovers that a different fresh `generation_id` now owns that same `agent_name`
- **THEN** that publisher surfaces an explicit conflict and stops claiming shared-registry ownership for that name
- **AND THEN** the conflict is not normalized as healthy steady-state discovery

### Requirement: Shared registry resolves agents by globally unique agent name
The system SHALL support direct resolution of a published agent by its globally unique agent name.

Resolution SHALL first canonicalize the requested input name using the shared agent-name normalization rule, then derive the deterministic `agent-key`, load the corresponding `record.json`, validate that the stored `agent_name` matches the canonical requested name, and validate that the record is structurally valid and lease-fresh before returning it.

The system MAY additionally support listing active published records, but known-name resolution SHALL NOT require scanning a shared mutable index file.

#### Scenario: Known-name resolution returns the published record
- **WHEN** a caller resolves the shared-registry agent name `AGENTSYS-gpu`
- **AND WHEN** the corresponding `record.json` is valid and lease-fresh
- **THEN** the system returns the validated record for `AGENTSYS-gpu`
- **AND THEN** the returned record includes the published secret-free runtime and discovery pointers for that agent

#### Scenario: Unprefixed known-name resolution returns the same published record
- **WHEN** a caller resolves the shared-registry agent name `gpu`
- **AND WHEN** the corresponding `record.json` for canonical name `AGENTSYS-gpu` is valid and lease-fresh
- **THEN** the system returns the validated record for canonical name `AGENTSYS-gpu`
- **AND THEN** the unprefixed input does not require a second copy of the registry record

#### Scenario: Name resolution fails when the record is missing or invalid
- **WHEN** a caller resolves the shared-registry agent name `AGENTSYS-gpu`
- **AND WHEN** the corresponding `record.json` is missing, malformed, or fails freshness validation
- **THEN** the system returns an explicit not-found or stale-record result
- **AND THEN** it does not silently fabricate a registry entry from unrelated runtime-root state

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
