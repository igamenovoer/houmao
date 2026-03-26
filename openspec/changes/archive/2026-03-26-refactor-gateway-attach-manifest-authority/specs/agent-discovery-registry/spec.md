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
- a top-level `gateway` object when externally useful live gateway metadata is available,
- a top-level `mailbox` object when mailbox bindings are available.

The record schema SHALL treat `agent_name` as friendly metadata rather than as a global uniqueness guarantee.

The record's `runtime` metadata SHALL include the manifest path required to locate runtime-owned session authority for that live session.

When mailbox bindings are available for the published session, the record SHALL publish mailbox identity metadata such as the active principal id and full mailbox address.

When a live gateway is attached, the record MAY publish exact live gateway connect metadata such as a loopback connect URL and protocol version.

Registry records MUST NOT embed copied session manifests, gateway queue state, mailbox contents, secrets, relaunch helper scripts, copied credentials, or per-agent launcher subdirectories.

Registry records MUST NOT be required to publish stable gateway attach-path or gateway-root pointers as part of attach resolution. Manifest location remains the required discovery contract, while gateway publication metadata remains optional and externally useful only.

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

### Requirement: Shared registry resolves live agents primarily by authoritative agent id
The system SHALL support direct resolution of a published live agent by authoritative `agent_id`.

When a caller resolves a live agent by friendly `agent_name` instead of `agent_id`, the system SHALL consult persisted registry metadata rather than deriving the lookup path from the name alone.

When more than one fresh live registry record shares the same friendly `agent_name` but carries different authoritative `agent_id` values, friendly-name lookup SHALL report ambiguity rather than silently choosing one record.

When current-session discovery cannot use a valid tmux-published manifest pointer, resolution by authoritative `agent_id` SHALL be sufficient to recover the published `runtime.manifest_path` for manifest-first attach and control flows.

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
- **WHEN** a tmux-backed attach or control flow has authoritative `AGENTSYS_AGENT_ID=abc123`
- **AND WHEN** the tmux-published manifest pointer is missing, blank, or stale
- **AND WHEN** `live_agents/abc123/record.json` is valid and lease-fresh
- **THEN** the system resolves `runtime.manifest_path` from that record as the fallback manifest locator
- **AND THEN** it does not require gateway attach-path or gateway-root metadata to recover the session authority
