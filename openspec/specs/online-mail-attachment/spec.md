# online-mail-attachment Specification

## Purpose

Define live owner-bound attachment and reconfiguration of externally provisioned online mailboxes without restarting agent bodies or altering offline mail.

## Requirements

### Requirement: Existing agents can attach externally provisioned online mail

Supported CLI and API controls SHALL attach an online account using provider endpoint, address, login identity, and a protected credential reference. Attachment SHALL work with a keyed or open gateway. Stalwart attachment SHALL require mailbox-level access only and SHALL not provision domains/accounts, require management credentials, inspect provider delivery filters, or replace a password supplied by the account owner.

#### Scenario: Hub account attaches to a mailbox-disabled body

- **WHEN** an authorized caller supplies valid Stalwart mailbox credentials for a running agent
- **THEN** its online binding becomes usable for read and send
- **AND THEN** its agent ID, body process, and conversation remain unchanged

#### Scenario: Agent retains offline mail

- **WHEN** an offline member attaches online mail
- **THEN** its offline binding, address ownership, and messages remain unchanged
- **AND THEN** its canonical mail identity becomes the online address

#### Scenario: Stalwart is attached after first-key enrollment

- **WHEN** an authorized administrator attaches a ready Stalwart account to a keyed running agent
- **THEN** the binding becomes available with ordinary mailbox credentials
- **AND THEN** gateway and direct operations retain their individual caller and owner authorization checks

#### Scenario: First-key enrollment occurs after Stalwart attachment

- **WHEN** first-key enrollment succeeds for an open gateway with an online binding
- **THEN** it becomes keyed without retiring, replacing, or degrading that binding
- **AND THEN** authorized callers can continue to inspect, read, send, refresh, and reconnect under the keyed policy
- **AND THEN** enabled online notification uses the provider's current Inbox and ordinary admission

#### Scenario: A keyed gateway starts with an existing binding

- **WHEN** a keyed agent starts or reattaches its gateway with a ready configured online binding
- **THEN** the gateway can use that binding under its current owner, credential, origin, account, and revision checks

### Requirement: Candidate validation precedes online binding activation
Attachment SHALL validate credentials, selected provider account, requested address/sending identity, and required capabilities before committing the expected revision. A Stalwart candidate SHALL also pass the provider readiness checks for Inbox, Sent, and Archive. Ambiguous account selection SHALL fail rather than choosing an arbitrary account. Failed validation SHALL preserve current bindings and exclude secret material from returned errors.

#### Scenario: Invalid key leaves existing bindings intact
- **WHEN** candidate authentication fails
- **THEN** the operation reports a sanitized authentication failure
- **AND THEN** previous online and offline binding snapshots remain unchanged

#### Scenario: Endpoint is unavailable
- **WHEN** candidate discovery or validation exceeds its finite deadline
- **THEN** attachment fails with an explicit connectivity outcome
- **AND THEN** the candidate is not reported as active

#### Scenario: Account does not match the requested address
- **WHEN** credentials authenticate but the selected account does not authorize the requested sending address
- **THEN** attachment fails before publishing that account as the agent's online identity

#### Scenario: A normal account lacks an Archive role or another required resource
- **WHEN** candidate validation identifies a missing sending identity, missing required role, or insufficient mailbox rights
- **THEN** the control reports the relevant readiness failure and directs the operator to prepare the account
- **AND THEN** the control preserves the prior binding and issues only mailbox validation requests

#### Scenario: A previously validated account loses a required role
- **WHEN** refresh or reconnect revalidates a Stalwart binding and its provider no longer supplies a required role or right
- **THEN** the operation reports the readiness failure and preserves the configured binding and canonical identity

### Requirement: Live online controls are owned and revision-checked
Online status, attach/replace, refresh, reconnect, and detach SHALL target the resolved agent owner and explicit online slot. Mutations SHALL validate expected revision and reject stale updates. Replacing a different existing account SHALL require explicit replacement intent. Ordinary mail clients and offline member credentials SHALL not authorize these management controls.

#### Scenario: Concurrent management updates conflict
- **WHEN** two callers attempt replacement from the same expected revision
- **THEN** at most one commits and the other receives a conflict

#### Scenario: Address change is not an implicit replacement
- **WHEN** attach targets a different account while one is already configured without replacement intent
- **THEN** it fails without discarding the existing online binding

### Requirement: Credential refresh preserves account identity and private material
Refresh SHALL re-resolve the explicitly selected credential source, validate the same bound account/address, and publish a new binding revision without changing binding ID. Provider passwords SHALL not be rotated implicitly. Secrets SHALL remain in private local credential storage and SHALL be absent from tracked files, manifests, registry projections, status, and ordinary diagnostics.

#### Scenario: Hub rotates a mailbox credential
- **WHEN** the operator updates its private source and requests refresh for the same account
- **THEN** new requests use the validated credential revision
- **AND THEN** offline mail, stable agent identity, sync checkpoints, and canonical online address remain associated with the same owner

#### Scenario: Refresh resolves another account
- **WHEN** a credential source now authenticates as a different account
- **THEN** refresh fails as an identity mismatch
- **AND THEN** switching accounts requires explicit replacement with a new binding scope

### Requirement: Superseded online operations cannot target replacement accounts
Every online request and worker SHALL remain pinned to its admitted binding/revision. Replacement or detach SHALL close old admission, cancel unstarted work, and quiesce or explicitly fail outstanding operations within a deadline. Old callbacks SHALL not publish new state or dispatch wakeups into the replacement binding. Send/reply uncertainty SHALL not cause automatic resend.

#### Scenario: Old poll completes after replacement
- **WHEN** an old account's metadata request returns after another binding becomes current
- **THEN** its result is discarded for current-state and notifier purposes
- **AND THEN** its checkpoint is not written into the replacement account's scope

#### Scenario: Send result is uncertain during retirement
- **WHEN** retirement cannot confirm whether an already-started send completed
- **THEN** the caller receives an explicit uncertain outcome pinned to the old binding
- **AND THEN** the system does not retry that send on the new account

### Requirement: Detach and reconnect preserve lifecycle boundaries
Detach SHALL remove only the online binding, stop its workers, and leave provider mail and externally owned credential sources intact. Reconnect SHALL rebuild the selected connection without restarting the body or changing the account. Automatic connection recovery SHALL not choose another account, channel, or canonical identity.

#### Scenario: Online detach restores offline canonical identity
- **WHEN** an agent with both bindings detaches online mail
- **THEN** online workers stop and its canonical mail identity becomes the offline address
- **AND THEN** its body and offline mail remain usable

#### Scenario: Provider outage is recoverable without identity change
- **WHEN** an attached account disconnects and later becomes reachable
- **THEN** status reports degradation and recovery for the same binding
- **AND THEN** its canonical identity does not oscillate with connectivity

### Requirement: Gateway facade and notifier become usable without body relaunch
Successful attachment SHALL make the online channel available through current runtime discovery and a live gateway's mail facade. Configured online notifier work SHALL use that same binding. Missing native skill availability SHALL use supported API guidance. Enabling notifier behavior SHALL require an available gateway but SHALL not require restarting the body.

#### Scenario: Gateway companion is attached after body launch
- **WHEN** an operator uses the supported companion attachment path for an already-running agent and then attaches online mail
- **THEN** the facade and configured online notifier use the new binding without body replacement

#### Scenario: No native mailbox skill route is available
- **WHEN** a newly online-enabled body cannot discover native mailbox skills
- **THEN** its notifier prompt provides the online channel and exact mailbox API context
- **AND THEN** attachment does not depend on native skill hot-reload

### Requirement: Online attachment persists operator-approved JMAP origins
The attach controls SHALL accept an optional list of exact JMAP origins and persist the normalized list with the activated online binding revision. Provisioned bindings SHALL persist the policy selected for their launch. Gateway, notifier, and direct mail clients SHALL use the persisted policy, including on refresh and reconnect. Earlier bindings without the list SHALL use the default connection policy.

#### Scenario: An approved intranet origin survives a new connection
- **WHEN** an authorized operator attaches an account with an explicit origin approval and the binding reconnects, refreshes credentials, or is loaded in a new process
- **THEN** the new connection uses the same approval and validates the same account
- **AND THEN** a following gateway, notifier, or direct mail operation can use the approved endpoint

#### Scenario: Origin approval belongs to the online slot
- **WHEN** the operator reattaches the same account at the same discovery and API origins with a different valid approval list
- **THEN** the new policy commits under the expected slot revision with the same binding ID
- **AND THEN** operations admitted under the previous revision continue to use their captured policy until retirement

### Requirement: Owner status describes the binding's JMAP origin policy
Owner-scoped online status SHALL show the configured discovery and verified API origins, the explicit approvals, and a warning when an approval permits non-loopback plaintext HTTP. Shared registry projections SHALL continue to expose only safe binding identity and availability metadata.

#### Scenario: The operator inspects a plaintext approval
- **WHEN** the operator queries online status for a binding with an explicit non-loopback HTTP approval
- **THEN** status shows the approved origin and warns that HTTP exposes the mailbox credential in transit
- **AND THEN** status omits credentials, credential sources, and full advertised URLs

### Requirement: Online account scope includes the verified JMAP method origin
A Stalwart binding SHALL pin its verified API origin with the selected provider account and sending identity. Refresh, reconnect, and background client reconstruction SHALL enforce the pin before sending method requests. An explicit attach that changes the pinned API origin SHALL require replacement and a fresh binding ID.

#### Scenario: An advertised API origin changes after attachment
- **WHEN** discovery on reconnect reports a different API origin, including another origin on the approval list
- **THEN** reconnect reports the changed origin and preserves the current binding scope
- **AND THEN** the client sends no method request to the changed origin
- **AND THEN** explicit replacement is required to activate the new origin
### Requirement: Online attachment keeps protected policy authority separate

Online attachment SHALL keep the mailbox binding and the optional protected mail-policy authority separate. Ordinary attachment SHALL use mailbox-level credentials. Protected operation SHALL require a qualified provider-native control path that files matching new arrivals directly in Archive for the exact bound account. That path SHALL stay isolated from the gateway runtime.

#### Scenario: An ordinary account lacks a protected control path

- **WHEN** an authorized operator attaches a ready provider account without an independent trusted management path
- **THEN** ordinary mailbox attachment and use remain available
- **AND THEN** a later request to apply protected policy reports unsupported operation

#### Scenario: A gateway uses a protected online binding

- **WHEN** a gateway attaches or reconnects its ordinary runtime client to a qualified protected binding
- **THEN** the runtime receives only its authorized mailbox capabilities
- **AND THEN** the independent control path retains the credentials and authority for protected rule and placement changes
