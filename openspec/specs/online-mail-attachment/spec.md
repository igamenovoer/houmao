# online-mail-attachment Specification

## Purpose

Define live owner-bound attachment and reconfiguration of externally provisioned online mailboxes without restarting agent bodies or altering offline mail.

## Requirements

### Requirement: Existing agents can attach externally provisioned online mail
Supported CLI and API controls SHALL attach an online account using provider endpoint, address, login identity, and a protected credential reference. Stalwart attachment SHALL require mailbox-level access only and SHALL not provision domains/accounts, require management credentials, or replace a password supplied by the account owner.

#### Scenario: Hub account attaches to a mailbox-disabled body
- **WHEN** an authorized caller supplies valid Stalwart mailbox credentials for a running agent
- **THEN** its online binding becomes usable for read and send
- **AND THEN** its agent ID, body process, and conversation remain unchanged

#### Scenario: Agent retains offline mail
- **WHEN** an offline member attaches online mail
- **THEN** its offline binding, address ownership, and messages remain unchanged
- **AND THEN** its canonical mail identity becomes the online address

### Requirement: Candidate validation precedes online binding activation
Attachment SHALL validate credentials, selected provider account, requested address/sending identity, and required capabilities before committing the expected revision. Ambiguous account selection SHALL fail rather than choosing an arbitrary account. Failed validation SHALL preserve current bindings and exclude secret material from returned errors.

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
