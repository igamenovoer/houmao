# Spec Delta

## Purpose

Define an agent's independent offline and online mailbox bindings, their stable ownership, canonical mail identity, and runtime revision boundaries.

## ADDED Requirements

### Requirement: Agents have two independent optional mail bindings
An agent SHALL have at most one `offline` binding and at most one `online` binding. Offline mail SHALL use filesystem storage owned by the selected registry host. Online mail SHALL use an email-service provider, initially Stalwart. Configuring either binding SHALL preserve the other binding.

#### Scenario: Both bindings coexist
- **WHEN** an agent is configured with offline and online mail
- **THEN** status reports both bindings under separate channel keys
- **AND THEN** operations on either channel preserve the other mailbox and its state

#### Scenario: Mailbox-disabled agent remains valid
- **WHEN** an agent has neither binding
- **THEN** it remains manageable by its stable `agent_id`
- **AND THEN** mail status reports both bindings as absent

#### Scenario: Multiple accounts in one channel are rejected
- **WHEN** configuration attempts to assign two online accounts or two offline registrations to one agent
- **THEN** validation rejects the configuration before changing the active bindings

### Requirement: Canonical mail identity follows configured online-first precedence
The canonical mail identity SHALL be derived from the configured online address when present, otherwise the configured offline address, otherwise no mail identity. It SHALL include the selected channel. Reachability and credential health SHALL NOT change this selection. Historical message address snapshots SHALL remain unchanged.

#### Scenario: Online identity takes precedence without removing offline ownership
- **WHEN** both bindings are configured
- **THEN** the canonical mail identity is the online address
- **AND THEN** the offline address remains bound to the same `agent_id`

#### Scenario: Explicit online removal falls back to offline identity
- **WHEN** the online binding is removed while offline mail remains configured
- **THEN** the canonical mail identity becomes the offline address
- **AND THEN** the agent ID and existing message snapshots remain unchanged

#### Scenario: Outage does not rename the agent
- **WHEN** a configured online provider becomes unreachable or rejects expired credentials
- **THEN** the canonical mail identity remains the online address
- **AND THEN** status reports degraded online connectivity separately

### Requirement: Binding identity is distinct from configuration revision
Each binding SHALL expose a stable opaque binding ID, its owning `agent_id`, channel, and an opaque revision. Credential refresh for the same account SHALL preserve binding identity. Selecting another account or offline registration SHALL create a new binding identity. Removed bindings SHALL retain enough revision authority to reject stale mutations.

#### Scenario: Credential changes preserve account scope
- **WHEN** credentials for the same online account are refreshed
- **THEN** its binding ID remains stable and its revision changes
- **AND THEN** account-scoped operational state can remain associated with that binding

#### Scenario: Detached binding cannot be resurrected by an old writer
- **WHEN** a writer presents a revision from before an explicit detach
- **THEN** its mutation fails with a binding conflict
- **AND THEN** the removed binding is not restored

### Requirement: Runtime binding mutation is atomic and revision-checked
Runtime binding changes SHALL compare the expected revision, preserve the other channel, and publish a complete valid snapshot atomically. Ordinary session persistence SHALL preserve newer mailbox state rather than replacing it from stale controller state. Competing mutations SHALL report conflicts explicitly.

#### Scenario: Slow controller persistence preserves a new binding
- **WHEN** a controller loaded before an offline registration later persists backend state
- **THEN** the current offline registration and online binding remain in the durable snapshot
- **AND THEN** backend persistence does not restore the controller's older mailbox values

#### Scenario: Two binding updates race
- **WHEN** two updates to the same channel use the same expected revision
- **THEN** at most one commits
- **AND THEN** the other receives an explicit conflict without partial state changes

### Requirement: Mail references are scoped to their owner and binding
Opaque message, thread, and continuation references SHALL carry verifiable owner, channel, and binding scope. A reference from another scope SHALL be rejected before a message is read or mutated. Reference validation SHALL NOT derive identity from a display name or preferred mail address.

#### Scenario: Online reference cannot target offline mail
- **WHEN** an offline read or reply receives an online message reference
- **THEN** the request fails with a scope error before contacting the offline store

#### Scenario: Account replacement invalidates old targeting
- **WHEN** an online account is replaced and the new account happens to contain the same provider message ID
- **THEN** an old account's message reference is rejected
- **AND THEN** it cannot read, reply to, or archive the replacement account's message

### Requirement: Operational status separates binding presence from health
Mail status and live discovery SHALL report both channels, binding identity/revision, canonical mail identity, availability, and explicit backend limitations without credential material. A failed channel SHALL NOT hide the other channel or make core gateway health depend on mail connectivity.

#### Scenario: Online failure leaves offline mail available
- **WHEN** online authentication fails while offline registration remains actionable
- **THEN** status reports the online failure and the usable offline binding
- **AND THEN** explicitly selected offline operations remain available

### Requirement: Provider selection does not redefine the mail contract
Online bindings SHALL identify their provider and report supported mail operations and limitations. Shared mail semantics SHALL remain independent of the provider's wire protocol. Unsupported operations SHALL fail explicitly. Existing launch-time Stalwart configuration SHALL populate the online slot without replacing offline mail.

#### Scenario: Launch-time Stalwart and offline mail are configured together
- **WHEN** a supported launch input includes an offline registration and existing Stalwart startup configuration
- **THEN** the runtime constructs both bindings with the same agent owner
- **AND THEN** Stalwart remains the selected online provider

#### Scenario: Unsupported provider operation is visible
- **WHEN** a caller selects an operation the configured backend does not support
- **THEN** it receives a structured unsupported-operation result
- **AND THEN** the system does not switch providers or channels
