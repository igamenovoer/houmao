# cccc-gateway-binding Specification

## Purpose

Define how an independently installed CCCC gateway integration binds a provisioned service Actor to one Houmao owner without changing the agent body or its email identities.

## Requirements

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

The integration SHALL read credentials only from its selected private reference and validate their owner and Actor scope. It SHALL reject unsafe files, ambient-auth fallback, credential-bearing URLs, and request-supplied secrets. Refresh SHALL reread the same selected source without changing binding identity. Direct `houmao-cccc` operation SHALL use the same explicit owner-bound Actor profile format and validate its selection before provider access.

#### Scenario: Credential Source Is Missing

- **WHEN** the selected file is absent while unrelated credentials exist in the environment or home
- **THEN** gateway attachment or direct CLI selection fails without using those other credentials

#### Scenario: Rotated File Refers to Another Actor

- **WHEN** a credential refresh finds a different owner, endpoint, Group, Actor, or registration generation
- **THEN** refresh fails without switching binding or reusing another Actor's state

#### Scenario: Same Binding Receives a New Token

- **WHEN** the selected private source contains a valid rotated token for the same owner and Actor
- **THEN** reconnect uses the new credential while preserving binding identity and compatible observation state

#### Scenario: The Direct CLI Selects an Explicit Actor Profile

- **WHEN** the agent invokes direct `houmao-cccc` with a selected private Actor profile
- **THEN** the CLI validates its owner, endpoint, and Actor registration and uses that profile's authority for CCCC
- **AND THEN** CLI output and diagnostics exclude the credential and its private source path

### Requirement: Connection Lifecycle Is Supervised and Bounded

A configured instance SHALL support connect, disconnect, reconnect, and selected-source credential refresh within its binding. Service unavailability SHALL produce bounded reconnect progress and safe connection status while core gateway operations remain available. Shutdown SHALL revoke intake and close supervised resources, return unstarted chat to CCCC, and preserve confirmed or uncertain outcomes for started work.

#### Scenario: CCCC Is Unavailable at Gateway Startup

- **WHEN** the configured CCCC endpoint cannot be reached
- **THEN** core gateway health and operator control become available independently
- **AND THEN** plugin status reports reconnecting or degraded state and bounded retry timing

#### Scenario: Gateway Shuts Down During Delivery

- **WHEN** a gateway stops with pending chat and a started attempt
- **THEN** its receiver lease and workers retire and CCCC preserves the started outcome or records uncertainty when handoff cannot be established
- **AND THEN** unstarted chat remains eligible at CCCC and no payload survives locally for a replacement process

### Requirement: Binding State Contains No Retry Inbox

Private durable state SHALL remain scoped to owner, runtime, plugin instance, and CCCC binding and retain only non-message connection or observation metadata. A receiver SHALL stage only a bounded working set in memory under its active generation. Credential rotation SHALL preserve compatible durable state. Actor or endpoint replacement SHALL reject old targeting references and cursors.

#### Scenario: Instance Name Is Reused for Another Actor

- **WHEN** operator configuration selects another Actor under an existing plugin instance name
- **THEN** the replacement receives a different binding state scope
- **AND THEN** old references cannot read, reply, or mutate through the replacement

#### Scenario: Rejected Event Is Followed by Gateway Restart

- **WHEN** an event was refused and the gateway later restarts with the same binding
- **THEN** local state contains no event body or deferred dispatch job

#### Scenario: The Gateway Reaches Its Staging Budget

- **WHEN** staged deliveries reach the selected instance's count or byte budget
- **THEN** the receiver limits intake and CCCC retains excess unstarted chat for later delivery
- **AND THEN** a replacement gateway reconciles work through CCCC's authoritative attempt state

### Requirement: Operational Projections Are Safe and Independent

Host status SHALL remain readable without provider calls. Plugin binding and capability projections SHALL separate configuration presence, connection health, protocol compatibility, and receiver readiness. Default diagnostics SHALL exclude credentials, credential paths, message bodies, and raw provider exceptions.

#### Scenario: Provider Error Contains Private Material

- **WHEN** a provider failure includes a token or message in its error text
- **THEN** status and logs expose a sanitized code and safe operational metadata only

#### Scenario: Plugin Connection Fails

- **WHEN** CCCC disconnects while offline or online email remains available
- **THEN** CCCC reports its own failure without hiding email status or failing core gateway health

### Requirement: Gateway Exposure Retains Existing Listener Policy

CCCC SHALL operate through the validated gateway plugin deployment policy. The plugin SHALL initiate connections to CCCC outbound, including the authenticated Actor push stream. Gateway exposure and privileged lifecycle operations SHALL remain governed by gateway access policy.

#### Scenario: Remote Service Is Used From a Local Gateway

- **WHEN** a loopback gateway connects to an authenticated remote CCCC receiver in pull or push mode
- **THEN** chat operations and incoming offers use that outbound connection without requiring a remotely reachable gateway or a public callback

#### Scenario: Gateway Uses an Unsupported Broad Listener

- **WHEN** a broader gateway deployment lacks the settings required for plugin activation
- **THEN** CCCC credentials, workers, and intake remain inactive under the host policy

#### Scenario: Gateway Uses a Validated Broader Listener

- **WHEN** a broader gateway deployment meets the host's validated plugin access policy
- **THEN** CCCC uses its configured service authority and the same readiness and exact-handoff checks as a local deployment

### Requirement: Delivery Settings Apply Per CCCC Instance

`houmao-mgr` launch arguments SHALL set delivery settings per selected CCCC plugin instance. The gateway SHALL expose authorized `GET` and `PUT /v1/plugins/{instance}/delivery` operations to inspect or update the same settings for the current gateway run. The gateway SHALL validate updates against the current settings revision, selected binding, and qualified provider capabilities.

#### Scenario: An Operator Starts Two CCCC Instances

- **WHEN** an operator launches a gateway and supplies delivery options for one of its two CCCC instances
- **THEN** the selected instance uses its launch settings and the other uses its own configured settings
- **AND THEN** an instance with no transport selection defaults to scheduled pull

#### Scenario: An Operator Inspects the Effective Settings

- **WHEN** an authorized caller reads the delivery settings for a selected instance
- **THEN** the gateway reports desired and effective settings, the settings revision, and transition status

#### Scenario: An Operator Configures Pull or Push

- **WHEN** an authorized caller sets the instance to `pull` or `push` using its current settings revision
- **THEN** pull uses a positive finite scheduled interval and push selects `asap` or `batch`
- **AND THEN** push `batch` accepts a positive finite quiet interval and maximum wait with the quiet interval at most the maximum wait
- **AND THEN** the resulting live settings apply only to that instance under its current binding

#### Scenario: A Settings Update Is Invalid or Unauthorized

- **WHEN** a caller supplies a stale revision, a transport unsupported by the provider, invalid timing, or lacks the management action on the selected instance
- **THEN** the gateway returns the applicable conflict, compatibility, validation, or authorization error and preserves the prior settings

#### Scenario: An Operator Changes Delivery Transport

- **WHEN** an authorized update changes an active instance between pull and push
- **THEN** the gateway reports the transition, stops old intake, and finishes or classifies the in-flight handoff within a finite bound
- **AND THEN** it retires the previous intake generation before the new transport can claim deliveries
- **AND THEN** CCCC retains unstarted work for the active receiver and preserves or reconciles started outcomes

#### Scenario: An Operator Edits a Live Push Policy

- **WHEN** an authorized caller changes the push policy or its timing while a batch is open
- **THEN** the gateway closes that batch under the previous settings and applies the new policy to subsequent offers

### Requirement: Authorized Discovery Identifies the Selected CCCC Actor

The gateway and `houmao-cccc` in direct mode SHALL expose an authorized discovery operation for the selected Actor. Discovery SHALL return the normalized CCCC origin, Group, Actor, registration generation, and advertised capabilities for direct calls. CCCC SHALL enforce the caller's provisioned Actor authority on each advanced operation.

#### Scenario: The Agent Discovers Its CCCC Identity for a Direct Call

- **WHEN** an authorized agent requests CCCC discovery through the gateway or its selected direct profile
- **THEN** it receives the routing descriptors for that exact Actor and the relevant qualified provider capabilities
- **AND THEN** an advanced operation runs directly against CCCC under explicitly provisioned Actor authority and its operation-specific scope

#### Scenario: A Caller Requests Discovery Without Permission

- **WHEN** a gateway caller lacks discovery permission for the selected instance or a direct caller cannot establish the selected profile's owner and Actor scope
- **THEN** the request fails before returning the selected Actor's discovery result

#### Scenario: A Discovered API Requires Broader Authority

- **WHEN** a direct caller selects a CCCC operation outside its provisioned Actor authority
- **THEN** CCCC denies that operation before exposing its data or changing state
- **AND THEN** discovery provides no credential values, secret paths, or administrative authority
