## ADDED Requirements

### Requirement: Shared registry preserves known agent addresses independently from live gateway presence
The shared registry SHALL provide enough secret-free metadata for callers to resolve a known managed agent by authoritative `agent_id` even when no live gateway is currently attached.

Known-agent address metadata SHALL include the authoritative `agent_id`, canonical `agent_name`, lifecycle state when available, relaunchability when available, and safe runtime pointers needed by supported relaunch or status flows.

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
