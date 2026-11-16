# Spec Delta

## MODIFIED Requirements

### Requirement: Stalwart-backed mailbox transport provisions mailbox principals through server-owned management surfaces
The online Stalwart backend SHALL support attachment of an existing account with mailbox-level credentials. This path SHALL NOT call management APIs, create a domain/account, require a management URL or administrative credential, or rotate an externally supplied password.

When an operator explicitly selects account provisioning, the separate provisioning workflow SHALL create or confirm its domain, individual account, access credential reference, and idempotent re-entry through management surfaces. Provisioning SHALL not be an implicit side effect of normal attachment, reconnect, resume, or gateway adapter construction.

Persisted bindings SHALL contain only selected protected credential references; actual credentials SHALL remain private and outside manifest/discovery payloads. Private runtime materialization SHALL be scoped to its owner and binding revision. Stalwart SHALL not require filesystem registration or force/stash/deactivate/purge workflows.

#### Scenario: Starting a Stalwart-backed session provisions a missing mailbox account
- **WHEN** an operator explicitly selects provisioning for a missing Stalwart account
- **THEN** that workflow creates or confirms the domain and account through management surfaces
- **AND THEN** it produces a usable online binding without filesystem registration

#### Scenario: Restarting the same Stalwart-backed mailbox principal is idempotent
- **WHEN** an explicitly selected provisioning workflow re-enters for an existing account
- **THEN** it confirms or reuses that account without creating a conflicting duplicate

#### Scenario: Restarting the same Stalwart-backed mailbox principal reuses credential references without unnecessary rotation
- **WHEN** an existing online binding is resumed or reconstructed for gateway use
- **THEN** its selected credential reference is reused
- **AND THEN** no provisioning or password rotation occurs implicitly

#### Scenario: Hub-managed account attaches without management credentials
- **WHEN** a caller supplies only the discovery endpoint, account identity, address, and valid mailbox credential reference
- **THEN** attachment succeeds without any management request
- **AND THEN** the hub-supplied password remains unchanged

## ADDED Requirements

### Requirement: Stalwart discovery distinguishes session and request endpoints
The backend SHALL accept an explicit JMAP session-discovery URL and use the returned API URL for method calls. Base-URL convenience input SHALL derive the standard discovery endpoint rather than assume that the API POST path supports session GET. Required capability or discovery failures SHALL remain explicit.

#### Scenario: Discovery advertises a different API path
- **WHEN** session discovery returns a usable API URL different from its own path
- **THEN** subsequent method calls use that advertised API URL within the configured connection policy

### Requirement: Stalwart account and sending identity match the binding
The backend SHALL pin the validated provider account and authorized sending identity to the online binding. It SHALL not select an arbitrary first account or sender identity when the requested identity is missing or ambiguous. Account-scope changes SHALL require explicit replacement rather than ordinary credential refresh.

#### Scenario: Login name differs from the sending address
- **WHEN** the validated account authorizes the requested address but its login identity is a different string
- **THEN** send uses the explicitly matched sending identity for that address
- **AND THEN** it does not choose an unrelated first identity

#### Scenario: Multiple accounts have no unambiguous selection
- **WHEN** discovery presents multiple accounts without a valid explicit or unambiguous primary selection
- **THEN** attachment reports the ambiguity before activating a binding
