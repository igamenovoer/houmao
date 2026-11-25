# Spec Delta

## ADDED Requirements

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

## MODIFIED Requirements

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
