# offline-mail-registry Specification

## Purpose
Define registry-host authority for offline mail membership, address ownership, filesystem storage, and authenticated access from agents on other hosts.

## Requirements

### Requirement: Registry selection provides offline mail scope
An offline cluster SHALL consist of agents registered with one selected registry authority. That registry's host SHALL own its filesystem mail store. Offline membership and addressing SHALL NOT require a `cluster_id` or another separately assigned cluster identifier. An offline address SHALL be interpreted only in the selected registry context.

#### Scenario: Separate registries may use the same address
- **WHEN** two independent registries each register `alice@houmao.localhost`
- **THEN** each address resolves only within its selected registry
- **AND THEN** neither registration enables delivery to the other registry

#### Scenario: Remote agent joins without a cluster identifier
- **WHEN** an authorized agent on another host supplies its `agent_id`, requested address, and registry connection
- **THEN** the registry can register that agent without a cluster identifier
- **AND THEN** it does not require the agent to share the registry host's filesystem

### Requirement: Offline address ownership is exclusive and atomic
The registry SHALL atomically assign an offline address to at most one agent owner. A different `agent_id` claiming an owned address SHALL be rejected without changing existing membership or mail. Repeating a valid claim by the same agent for the same registration SHALL be idempotent. Identical IDs SHALL be interpreted as the same agent, without accidental-ID-collision detection.

#### Scenario: Conflicting agent cannot join
- **WHEN** agent B requests an address currently owned by a different agent A
- **THEN** the registry returns an address-conflict result
- **AND THEN** A's registration and messages remain unchanged and B receives no registration

#### Scenario: Concurrent claims have one winner
- **WHEN** two different agent IDs concurrently claim one free address
- **THEN** exactly one ownership assignment succeeds
- **AND THEN** the losing claim has no mailbox or membership side effects

#### Scenario: Owner retries registration
- **WHEN** the current owner repeats its registration request after losing the first response
- **THEN** it receives the existing registration identity
- **AND THEN** its inbox and historical state are preserved

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

### Requirement: Offline release is explicit and preserves ownership history
Offline address release SHALL require an authorized explicit leave or unregister operation. Merely stopping an agent, changing its canonical mail identity, or attaching online mail SHALL NOT release it. A later different owner SHALL receive a fresh registration with no access to the previous owner's mailbox-view state or private history.

#### Scenario: Online attachment preserves offline membership
- **WHEN** an offline member gains online mail
- **THEN** its offline registration remains active
- **AND THEN** another agent still cannot claim its offline address

#### Scenario: Released address is reassigned safely
- **WHEN** an authorized owner releases an address and another agent later claims it
- **THEN** the new owner receives a new registration identity
- **AND THEN** old mailbox content is retained or removed under explicit retention controls, never inherited by the new owner

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

### Requirement: Remote attachment access is independent of host-local paths
Remote offline mail composition SHALL upload attachment content into registry-owned managed storage. Attachment reads SHALL use authorized transport locators. A path on an agent host SHALL NOT be interpreted as a path on the registry host, and ordinary remote callers SHALL NOT select registry filesystem or symlink targets.

#### Scenario: Sender path is not available on registry host
- **WHEN** a remote sender attaches a file that exists only on its own host
- **THEN** composition transfers the content through the supported attachment API
- **AND THEN** the recipient retrieves it without sharing the sender's path

### Requirement: Communication membership grants no remote lifecycle ownership
Offline cluster registration SHALL grant only the configured communication rights. It SHALL NOT grant the registry host or another member authority to stop, relaunch, join, or replace a remotely owned agent body. Runtime control SHALL continue to follow its existing authority boundary.

#### Scenario: Member attempts remote body control
- **WHEN** a caller authorized only for offline mail requests another member's body lifecycle action
- **THEN** membership alone does not authorize the action

### Requirement: Registry restart restores membership and mail authority
Registry-host service restart SHALL restore durable membership and mailbox ownership independently of runtime heartbeat recovery. Retried registration and mailbox mutations SHALL expose confirmed or uncertain outcomes without silently assigning another owner or changing channels.

#### Scenario: Registry restarts while agents remain remote
- **WHEN** the registry service restarts with its durable state intact
- **THEN** existing address owners and inboxes remain associated with the same agent IDs
- **AND THEN** remote agents can reconnect without creating replacement registrations
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
