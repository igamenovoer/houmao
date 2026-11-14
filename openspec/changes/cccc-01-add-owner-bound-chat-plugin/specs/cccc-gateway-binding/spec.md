# Spec Delta

## Purpose

Define how an independently installed CCCC gateway integration binds a provisioned service Actor to one Houmao owner without changing the agent body or its email identities.

## ADDED Requirements

### Requirement: CCCC Integration Is an Optional Installed Distribution

An operator SHALL be able to install and explicitly enable the CCCC plugin against an installed Houmao distribution without modifying Houmao files or configuring the agent body's MCP servers. An installed but unselected CCCC plugin SHALL remain inactive.

#### Scenario: Independent Wheels Work Outside Their Source Checkouts

- **WHEN** Houmao and the CCCC plugin wheels are installed in a fresh environment and an operator selects the plugin
- **THEN** a normal gateway process serves the integration from an unrelated working directory
- **AND THEN** neither checkout nor import-path modification is required

#### Scenario: Installation Alone Does Not Connect

- **WHEN** the CCCC distribution is installed without a configured instance
- **THEN** no CCCC credentials are read and no CCCC connection or worker starts

### Requirement: Binding Authority Comes From the Gateway Owner

A CCCC binding SHALL associate the gateway's persisted agent ID with a selected endpoint, Group, Actor, and Actor registration generation. Requests SHALL NOT override owner, sender, authenticated Group, or credential selection. Display names and email addresses SHALL NOT establish this association.

#### Scenario: Caller Attempts Sender Substitution

- **WHEN** an ordinary operation supplies another sender, owner, Group, or credential reference
- **THEN** it fails before any provider mutation
- **AND THEN** the selected Actor remains the only sending identity

#### Scenario: Two Owners Use Distinct Actors

- **WHEN** two gateways select distinct Actor bindings on the same CCCC service
- **THEN** each uses only its own Actor credentials, references, and private state

### Requirement: CCCC Does Not Change Email Identity

Attaching, reconnecting, or removing CCCC SHALL preserve the agent ID, offline and online email slots, canonical mail identity, and email registration ownership. CCCC Actor addresses SHALL remain service-specific addresses outside those email slots.

#### Scenario: Agent Has Both Email Bindings and CCCC

- **WHEN** an agent with offline and online email attaches CCCC
- **THEN** both email bindings remain configured and canonical mail identity remains online-first
- **AND THEN** CCCC membership is reported separately

#### Scenario: CCCC Is the Only Communication Integration

- **WHEN** an agent with neither email slot configured attaches CCCC
- **THEN** its agent ID remains unchanged and canonical mail identity remains absent

### Requirement: Attachment Preserves the Running Body

Operators SHALL enable or replace a CCCC selection through supported gateway configuration. New code, immutable configuration, or credential-reference selection SHALL require only gateway restart when needed. The integration SHALL NOT launch, stop, restart, or reconfigure the agent body.

#### Scenario: Operator Adds CCCC to a Running Agent

- **WHEN** an operator installs and selects the integration for an already-running agent
- **THEN** any required gateway detach/attach preserves the body's PID and conversation
- **AND THEN** the body receives no new MCP configuration

#### Scenario: Ordinary Route Attempts Account Replacement

- **WHEN** an ordinary connection operation attempts to select another endpoint or Actor
- **THEN** it fails without changing active or persisted configuration
- **AND THEN** status identifies the need for operator-selected gateway reconfiguration

### Requirement: Attachment Uses Preprovisioned Membership

The integration SHALL validate the selected Actor and its current registration generation using normal binding credentials. It SHALL NOT create Groups or Actors, rotate provider passwords, or require CCCC administration credentials for attachment or recovery.

#### Scenario: Selected Actor Does Not Exist

- **WHEN** the configured Group or Actor is absent or its generation differs
- **THEN** the integration reports an unavailable or stale binding
- **AND THEN** it creates no replacement membership

#### Scenario: Matching Normal Credential Is Sufficient

- **WHEN** the hub has provisioned a valid Actor grant and the compatible receiver interface
- **THEN** attachment succeeds without management credentials or provider account changes

### Requirement: Credentials Are Explicit and Private

The integration SHALL read credentials only from its selected private reference and validate their owner and Actor scope. It SHALL reject unsafe files, ambient-auth fallback, credential-bearing URLs, and request-supplied secrets. Refresh SHALL reread the same selected source without changing binding identity.

#### Scenario: Credential Source Is Missing

- **WHEN** the selected file is absent while unrelated credentials exist in the environment or home
- **THEN** attachment fails without using those other credentials

#### Scenario: Rotated File Refers to Another Actor

- **WHEN** a credential refresh finds a different owner, endpoint, Group, Actor, or registration generation
- **THEN** refresh fails without switching binding or reusing another Actor's state

#### Scenario: Same Binding Receives a New Token

- **WHEN** the selected private source contains a valid rotated token for the same owner and Actor
- **THEN** reconnect uses the new credential while preserving binding identity and compatible observation state

### Requirement: Connection Lifecycle Is Supervised and Bounded

A configured instance SHALL support connect, disconnect, reconnect, and selected-source credential refresh within its binding. Service unavailability SHALL produce bounded reconnect progress and safe connection status while core gateway operations remain available. Shutdown SHALL revoke intake and close supervised resources.

#### Scenario: CCCC Is Unavailable at Gateway Startup

- **WHEN** the configured CCCC endpoint cannot be reached
- **THEN** core gateway health and operator control become available independently
- **AND THEN** plugin status reports reconnecting or degraded state and bounded retry timing

#### Scenario: Gateway Shuts Down During Delivery

- **WHEN** a gateway stops with a CCCC attempt in flight
- **THEN** its receiver lease and workers retire and the attempt receives failure or becomes uncertain
- **AND THEN** no payload survives locally for a replacement process

### Requirement: Binding State Contains No Retry Inbox

Private state SHALL remain scoped to owner, runtime, plugin instance, and CCCC binding. It SHALL retain only non-message connection or observation metadata. Credential rotation SHALL preserve compatible state; Actor or endpoint replacement SHALL reject old targeting references and cursors.

#### Scenario: Instance Name Is Reused for Another Actor

- **WHEN** operator configuration selects another Actor under an existing plugin instance name
- **THEN** the replacement receives a different binding state scope
- **AND THEN** old references cannot read, reply, or mutate through the replacement

#### Scenario: Rejected Event Is Followed by Gateway Restart

- **WHEN** an event was refused and the gateway later restarts with the same binding
- **THEN** local state contains no event body or deferred dispatch job

### Requirement: Operational Projections Are Safe and Independent

Host status SHALL remain readable without provider calls. Plugin binding and capability projections SHALL separate configuration presence, connection health, protocol compatibility, and receiver readiness. Default diagnostics SHALL exclude credentials, credential paths, message bodies, and raw provider exceptions.

#### Scenario: Provider Error Contains Private Material

- **WHEN** a provider failure includes a token or message in its error text
- **THEN** status and logs expose a sanitized code and safe operational metadata only

#### Scenario: Plugin Connection Fails

- **WHEN** CCCC disconnects while offline or online email remains available
- **THEN** CCCC reports its own failure without hiding email status or failing core gateway health

### Requirement: Gateway Exposure Retains Existing Listener Policy

CCCC SHALL operate through the gateway's existing loopback-only plugin policy. A remote CCCC connection SHALL be initiated outbound by the plugin and SHALL NOT require a remotely reachable gateway, public plugin callback, or ordinary peer lifecycle authority.

#### Scenario: Remote Service Is Used From a Local Gateway

- **WHEN** a loopback gateway connects to an authenticated remote CCCC receiver
- **THEN** chat operations and incoming offers use that outbound connection without exposing gateway routes remotely

#### Scenario: Gateway Uses an Unsupported Broad Listener

- **WHEN** the gateway listener policy disables plugins for a broad bind address
- **THEN** CCCC credentials, workers, and intake remain inactive under the host policy
