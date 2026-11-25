# Spec Delta

## ADDED Requirements

### Requirement: Stalwart JMAP requests use only approved credential destinations
The default policy SHALL allow HTTPS or loopback HTTP discovery. A non-loopback HTTP discovery origin and every advertised API or upload origin distinct from discovery SHALL require explicit approval. Approval SHALL match the scheme, hostname, and effective port. HTTPS requests SHALL verify the server certificate.

#### Scenario: Explicitly selected intranet HTTP discovery
- **WHEN** an operator selects non-loopback HTTP discovery and explicitly approves its exact origin
- **THEN** JMAP discovery and same-origin API calls can authenticate there
- **AND THEN** an alternative scheme, host, or port requires independent approval

#### Scenario: Advertised API or upload origin is unapproved
- **WHEN** discovery reports a method or upload endpoint on an unapproved origin, including an unapproved HTTPS-to-HTTP change
- **THEN** the respective credential-bearing request is rejected before it reaches that endpoint
- **AND THEN** the error identifies the rejected origin using sanitized connection information

#### Scenario: An approval is malformed
- **WHEN** an origin approval contains a wildcard, embedded user information, a query, a fragment, a non-root path, or an invalid scheme, host, or port
- **THEN** the client rejects the policy before starting JMAP discovery

### Requirement: Stalwart redirects preserve the authorized request boundary
Discovery GET SHALL follow only same-origin redirects within a finite limit and SHALL apply the selected connection policy to each redirect target. JMAP POST requests SHALL reject redirects.

#### Scenario: Standard discovery redirects within an approved intranet origin
- **WHEN** an approved HTTP origin redirects `/.well-known/jmap` to its session path on the same origin
- **THEN** discovery follows the redirect and validates the session's API origin

#### Scenario: A redirect changes origin or would replay a POST
- **WHEN** a discovery redirect changes scheme, host, or port, or a JMAP POST receives a redirect
- **THEN** the client rejects the redirect before issuing a request to its target

### Requirement: Stalwart readiness validates the mailbox resources used by Houmao
A ready account SHALL support writable JMAP mail submission and authorize the requested sending identity. Its role map SHALL identify an unambiguous Inbox, Sent, and Archive. Inbox rights SHALL permit ordinary read, reply, and archive handling. Sent and Archive SHALL permit adding messages.

#### Scenario: The account has a usable role map
- **WHEN** validation resolves the requested sending identity and the selected account's role map
- **THEN** readiness verifies Inbox read, seen and keyword updates, and removal rights plus Sent and Archive add rights

#### Scenario: A mailbox with the name Archive lacks the role
- **WHEN** validation finds a folder named Archive without the provider's `archive` role
- **THEN** readiness reports the missing role and asks the operator to repair it

#### Scenario: A permission prevents normal mailbox operations
- **WHEN** a required Inbox, Sent, or Archive right is missing or denied
- **THEN** readiness identifies the relevant role and right before declaring the account ready

## MODIFIED Requirements

### Requirement: Stalwart-backed mailbox transport provisions mailbox principals through server-owned management surfaces
The online Stalwart backend SHALL support attachment of an existing account with mailbox-level credentials. This path SHALL NOT call management APIs, create a domain/account, require a management URL or administrative credential, or rotate an externally supplied password.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

When an operator explicitly selects account provisioning, the separate provisioning workflow SHALL create or confirm its domain, individual account, access credential reference, and idempotent re-entry through management surfaces. Provisioning SHALL not be an implicit side effect of normal attachment, reconnect, resume, or gateway adapter construction.

Explicit provisioning SHALL use normal mailbox credentials to ensure the selected sending identity and Archive role if they are missing. It SHALL verify provider readiness and return the resolved account ID, identity ID, and mailbox-role IDs before reporting success. A partial failure SHALL preserve the selected account's retryable private credential and report the stage that failed.

Persisted bindings SHALL contain only selected protected credential references; actual credentials SHALL remain private and outside manifest/discovery payloads. Private runtime materialization SHALL be scoped to its owner and binding revision. Stalwart SHALL not require filesystem registration or force/stash/deactivate/purge workflows.

#### Scenario: Starting a Stalwart-backed session provisions a missing mailbox account
- **WHEN** an operator explicitly selects provisioning for a missing Stalwart account
- **THEN** that workflow creates or confirms the domain and account through management surfaces
- **AND THEN** it produces a usable online binding without filesystem registration

#### Scenario: Restarting the same Stalwart-backed mailbox principal is idempotent
- **WHEN** an explicitly selected provisioning workflow re-enters for an existing account
- **THEN** it reuses the account, existing credential, matching identity, and Archive role without creating conflicting duplicates

#### Scenario: Restarting the same Stalwart-backed mailbox principal reuses credential references without unnecessary rotation
- **WHEN** an existing online binding is resumed or reconstructed for gateway use
- **THEN** its selected credential reference is reused
- **AND THEN** no provisioning or password rotation occurs implicitly

#### Scenario: Hub-managed account attaches without management credentials
- **WHEN** a caller supplies only the discovery endpoint, account identity, address, and valid mailbox credential reference
- **THEN** attachment succeeds without any management request
- **AND THEN** the hub-supplied password remains unchanged

#### Scenario: Provisioning fills missing JMAP resources
- **WHEN** an explicitly selected principal lacks an identity for its configured address or an Archive role and the provider permits creation
- **THEN** the workflow uses the normal account to create the missing resource and verifies its provider ID and readiness
- **AND THEN** it returns the validated account and the resolved identity and role IDs

#### Scenario: The address domain cannot supply a JMAP sending identity
- **WHEN** the operator selects a `.localhost` or `.test` address for send-capable provisioning on the pinned Stalwart release
- **THEN** provisioning fails before mutating the provider and identifies the domain requirement

#### Scenario: The provider rejects a required identity or role
- **WHEN** the provider refuses to create a required resource during explicit provisioning
- **THEN** the workflow reports a readiness failure and gives the operator the relevant remediation

#### Scenario: An interrupted run is retried
- **WHEN** the selected principal exists from an earlier provisioning attempt that stopped before readiness
- **THEN** provisioning reuses its owned credential and existing resources and ensures only the missing resources

#### Scenario: Existing resources conflict with the selected account
- **WHEN** provisioning finds a conflicting principal, ambiguous identity, or folder collision
- **THEN** it reports the conflict and preserves the other accounts, identities, and folders

### Requirement: Stalwart discovery distinguishes session and request endpoints
The backend SHALL accept an explicit JMAP session-discovery URL and use the returned API URL for method calls. Base-URL convenience input SHALL derive `/.well-known/jmap` in live attach and administrative launch. An explicit discovery URL SHALL be used as supplied. Required capability or discovery failures SHALL remain explicit.

#### Scenario: Discovery advertises a different API path
- **WHEN** session discovery returns a usable API URL different from its own path
- **THEN** subsequent method calls use that advertised API URL within the configured connection policy

#### Scenario: Provisioning uses the standard discovery endpoint
- **WHEN** an administrative launch supplies a base URL without an explicit JMAP URL
- **THEN** the provisioner discovers the session at `/.well-known/jmap` and uses the advertised API URL for readiness checks
