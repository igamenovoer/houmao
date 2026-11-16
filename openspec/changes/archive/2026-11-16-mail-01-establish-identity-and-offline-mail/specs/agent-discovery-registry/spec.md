# Spec Delta

## MODIFIED Requirements

### Requirement: Shared registry records are strict, secret-free contracts that point to runtime-owned state
Each local runtime-presence `record.json` SHALL use the current strict versioned schema and include its schema version, friendly name, authoritative `agent_id`, stable-per-live-session generation, publication/lease information, identity metadata, runtime pointers, and terminal metadata. Names SHALL be friendly metadata rather than a global uniqueness guarantee. The local record SHALL retain its manifest locator. Externally useful live gateway coordinates SHALL remain optional presence metadata.

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

## ADDED Requirements

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
