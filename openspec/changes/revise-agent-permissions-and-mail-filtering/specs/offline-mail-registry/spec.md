# Offline Mail Registry Delta

## MODIFIED Requirements

### Requirement: Membership outlives runtime presence

Offline registration SHALL remain durable while an agent is stopped, its gateway is absent, or remote liveness evidence expires. Runtime presence SHALL be recorded separately. Local tmux probes and live-record cleanup SHALL preserve remote membership and addresses. Delivery and enforcement of the effective recipient policy SHALL operate independently of the recipient body and gateway.

#### Scenario: Stopped recipient receives offline mail

- **WHEN** a registered recipient has no running body or gateway
- **THEN** the registry still commits delivery to the registered mailbox
- **AND THEN** the registry delivers a blocklist match directly to Archive and other deliveries to Inbox
- **AND THEN** that placement remains available to the recipient when it resumes

#### Scenario: Registry host cannot probe remote tmux

- **WHEN** remote runtime presence is unavailable on the registry host
- **THEN** membership and address ownership remain intact
- **AND THEN** status reports unavailable presence separately

### Requirement: Registry-host APIs authorize agent-scoped mail access

Remote membership and offline mail access SHALL require authorization separate from `agent_id`. Administrative credentials SHALL authorize enrollment and release. Agent credentials SHALL be scoped to an admitted registration. The registry SHALL bind sender identity and Inbox access to the authenticated scope and omit credentials from discovery and diagnostics. Protected placement SHALL require separate authority.

#### Scenario: Agent ID is not an access credential

- **WHEN** a caller knows an agent ID but lacks the required authorization
- **THEN** the registry refuses private membership or mailbox operations

#### Scenario: Authenticated sender cannot impersonate another member

- **WHEN** an agent-scoped caller submits another member's sender identity
- **THEN** the service rejects the request before delivery
- **AND THEN** the result excludes both members' credentials

#### Scenario: An ordinary runtime credential attempts to change protected placement

- **WHEN** a gateway or direct mailbox process uses a runtime credential to change a protected policy or to move, archive, or mark protected mail as archived
- **THEN** the registry refuses the change to protected state
- **AND THEN** a gateway administrator grant alone supplies no additional registry placement authority

### Requirement: Local and remote access use the same offline mail semantics

Registry-host local access and authorized remote API access SHALL use the same authoritative filesystem mailbox state and preserve list, peek, read, send, reply, mark, move, and archive semantics within each caller's scope. The backend SHALL report unsupported or unauthorized operations explicitly and keep them on the offline channel. Normal remote operation SHALL avoid mounting registry mailbox files.

#### Scenario: Remote reply preserves offline ancestry

- **WHEN** a remote member replies through its registry's offline mail API
- **THEN** the reply remains in that registry's offline conversation
- **AND THEN** the parent becomes read and answered without implicit archive

#### Scenario: Remote archive updates authoritative state

- **WHEN** a member uses the API to archive an offline message with the required authority for that mailbox
- **THEN** later local and remote reads report the same closed Inbox state

## ADDED Requirements

### Requirement: The registry verifies independent owner authority for protected offline mail

The registry SHALL verify owner-signed blocklist updates against an independently enrolled owner credential. The signed payload SHALL bind the operation, backend identity, recipient registration, expected policy revision, operation ID, and exact blocklist content. The signing credential SHALL remain outside gateway and ordinary mailbox runtime authority.

#### Scenario: A signed policy is applied to the intended registration

- **WHEN** the registry verifies an owner's signature and expected revision for the specified backend and active registration
- **THEN** it persists the new effective mail policy for that registration
- **AND THEN** subsequent deliveries use that policy while existing mail retains its placement
- **AND THEN** the owner can verify the committed revision through the registry while its gateway is unavailable

#### Scenario: An old registration's owner cannot affect a replacement registration

- **WHEN** an address is released and a signed operation for the previous registration is presented after reassignment
- **THEN** the registry rejects the operation for the replacement registration
- **AND THEN** the new registration starts with its own rules and mailbox history

#### Scenario: The registry discloses only the sender's transport outcome

- **WHEN** a sender submits a message to recipients with different protected policies
- **THEN** the registry omits the recipients' rules and individual placements from the sender-facing outcome
- **AND THEN** policy inspection and placement verification require separate authorization scoped to the affected mailbox
