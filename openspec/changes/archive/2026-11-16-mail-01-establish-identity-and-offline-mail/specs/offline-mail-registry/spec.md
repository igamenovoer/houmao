# Spec Delta

## Purpose

Define registry-host authority for offline mail membership, address ownership, filesystem storage, and authenticated access from agents on other hosts.

## ADDED Requirements

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
Offline registration SHALL remain durable while an agent is stopped, its gateway is absent, or remote liveness evidence expires. Runtime presence SHALL be recorded separately. Local tmux probes and live-record cleanup SHALL NOT remove remote membership or release offline addresses. Mail delivery to a registered recipient SHALL not require a running body.

#### Scenario: Stopped recipient receives offline mail
- **WHEN** a registered recipient has no running body or gateway
- **THEN** delivery still commits mail to its registered inbox
- **AND THEN** it can inspect that mail after resuming

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
Remote membership and offline mail access SHALL require authorization separate from `agent_id`. Administrative credentials SHALL authorize enrollment and release; agent credentials SHALL be scoped to an admitted agent owner. Ordinary callers SHALL NOT select another sender or access another agent's inbox by changing request fields. Credentials SHALL be excluded from discovery and diagnostics.

#### Scenario: Agent ID is not an access credential
- **WHEN** a caller knows an agent ID but lacks the required authorization
- **THEN** the registry refuses private membership or mailbox operations

#### Scenario: Authenticated sender cannot impersonate another member
- **WHEN** an agent-scoped caller submits another member's sender identity
- **THEN** the service rejects the request before delivery
- **AND THEN** it does not return either member's credentials

### Requirement: Local and remote access use the same offline mail semantics
Registry-host local access and authorized remote API access SHALL preserve list, peek, read, send, reply, mark, move, and archive semantics against the same filesystem mailbox authority. Explicit unsupported operations SHALL be reported without attempting online delivery. Normal operation SHALL not require mounting mailbox files on remote hosts.

#### Scenario: Remote reply preserves offline ancestry
- **WHEN** a remote member replies through its registry's offline mail API
- **THEN** the reply remains in that registry's offline conversation
- **AND THEN** the parent becomes read and answered without implicit archive

#### Scenario: Remote archive updates authoritative state
- **WHEN** a member archives an offline message through the API
- **THEN** later local and remote reads report the same closed inbox state

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
