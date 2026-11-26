# agent-mailbox-stalwart-transport Specification

## Purpose
Define the real email-backed `stalwart` mailbox transport contract, including provisioning, shared mailbox operations, and the JMAP automation surface.
## Requirements
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

### Requirement: Stalwart-backed mailbox transport delegates shared mailbox state and integrity to the mail server

For the `stalwart` transport, the system SHALL treat the Stalwart server as the authority for:

- delivered message storage and the provider's Inbox delivery rules,
- unread state used by shared mailbox `check` behavior,
- reply ancestry and transport-level threading metadata used by shared mailbox `reply` behavior,
- transport-level delivery integrity.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

The `stalwart` transport SHALL NOT require Houmao to materialize a filesystem mailbox root with `rules/`, mailbox projection symlinks, mailbox lock files, or mailbox-local SQLite state in order to maintain mailbox correctness.

#### Scenario: Stalwart-backed mailbox operation does not require filesystem mailbox artifacts

- **WHEN** a mailbox-enabled session uses the `stalwart` transport
- **THEN** mailbox correctness comes from the Stalwart server rather than from a Houmao-managed mailbox root
- **AND THEN** the transport does not require `rules/`, projection symlinks, or mailbox-local SQLite artifacts to maintain read or unread or delivery integrity

#### Scenario: Stalwart applies its own rules before depositing online mail

- **WHEN** Stalwart receives mail for an agent through an external client or Houmao submission
- **THEN** the provider controls Inbox placement under its active native rules
- **AND THEN** any supported Houmao-managed rule is applied through the independent trusted management path and remains effective while the gateway is unavailable

### Requirement: Stalwart-backed mailbox transport uses JMAP as the primary automation surface for shared mailbox operations

The `stalwart` transport SHALL use JMAP as the primary automation surface for mailbox operations initiated by Houmao mailbox workflows.

At minimum, the `stalwart` transport SHALL support:

- discovering mailbox messages for `mail list`,
- composing and submitting a new message for `mail send`,
- replying to an existing message for `mail reply`.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

SMTP submission and IMAP access MAY be supported for compatibility or debugging, but they SHALL NOT be the normative mailbox automation contract for Houmao mailbox operations in this change.

#### Scenario: Mail send uses JMAP-backed Stalwart delivery

- **WHEN** a mailbox-enabled session uses `mail send` through the `stalwart` transport
- **THEN** the mailbox workflow submits that message through JMAP-backed Stalwart mailbox operations
- **AND THEN** the operator-visible result records provider-confirmed submission, refusal, or uncertainty without filesystem delivery helpers
- **AND THEN** a confirmed submission supplies no evidence of recipient Inbox placement, notification, or processing

#### Scenario: Mail reply uses Stalwart mailbox metadata to preserve reply ancestry

- **WHEN** a mailbox-enabled session uses `mail reply` through the `stalwart` transport
- **THEN** the mailbox workflow resolves the target message through Stalwart-backed mailbox metadata
- **AND THEN** the resulting reply preserves reply ancestry through real email reply headers rather than through filesystem-only thread reconstruction

### Requirement: Stalwart-backed mailbox transport supports shared lifecycle operations

The Stalwart transport SHALL expose status, list, peek, read, send, reply, manual mark, move, and archive through the shared mailbox facade and direct mailbox workflows within the caller's scope. The transport SHALL preserve protected placement by restricting move, archive, and archived-state updates to the independent trusted authority.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

The transport SHALL map shared read to server-backed seen state, answered to server-backed answered state or equivalent durable metadata, and archive and move to server-backed mailbox membership.

#### Scenario: Stalwart read maps to server seen state

- **WHEN** a caller reads a Stalwart-backed mailbox message through the shared operation contract
- **THEN** the operation returns the selected message body
- **AND THEN** the transport updates the server-backed seen state for that mailbox account

#### Scenario: Stalwart reply maps to answered state

- **WHEN** a caller replies to a Stalwart-backed mailbox message
- **THEN** the transport preserves reply ancestry through email-compatible metadata
- **AND THEN** the transport records answered state through server-backed state or equivalent durable metadata

#### Scenario: Stalwart archive moves to the archive mailbox

- **WHEN** a caller with placement authority archives selected Stalwart-backed messages
- **THEN** the transport moves those messages out of the open Inbox into the Stalwart Archive or equivalent configured archive target
- **AND THEN** the response reports them as archived and no longer open Inbox work

### Requirement: Stalwart-backed mailbox transport uses JMAP for lifecycle state

The Stalwart transport SHALL use JMAP as the primary automation surface for shared lifecycle operations whenever the needed state is expressible through JMAP. SMTP submission and IMAP access MAY remain compatibility or debugging surfaces. The independent trusted management path SHALL use the provider-native controls required for protected placement.

#### Scenario: JMAP move updates mailbox membership

- **WHEN** an authorized shared mailbox move targets a Stalwart-backed message and is expressible through JMAP
- **THEN** the transport performs the membership update through JMAP-backed Stalwart mailbox operations
- **AND THEN** the caller can use the shared operation without supplying provider-native object shapes or mailbox IDs

### Requirement: Stalwart discovery distinguishes session and request endpoints
The backend SHALL accept an explicit JMAP session-discovery URL and use the returned API URL for method calls. Base-URL convenience input SHALL derive `/.well-known/jmap` in live attach and administrative launch. An explicit discovery URL SHALL be used as supplied. Required capability or discovery failures SHALL remain explicit.

#### Scenario: Discovery advertises a different API path
- **WHEN** session discovery returns a usable API URL different from its own path
- **THEN** subsequent method calls use that advertised API URL within the configured connection policy

#### Scenario: Provisioning uses the standard discovery endpoint
- **WHEN** an administrative launch supplies a base URL without an explicit JMAP URL
- **THEN** the provisioner discovers the session at `/.well-known/jmap` and uses the advertised API URL for readiness checks

### Requirement: Stalwart account and sending identity match the binding
The backend SHALL pin the validated provider account and authorized sending identity to the online binding. It SHALL not select an arbitrary first account or sender identity when the requested identity is missing or ambiguous. Account-scope changes SHALL require explicit replacement rather than ordinary credential refresh.

#### Scenario: Login name differs from the sending address
- **WHEN** the validated account authorizes the requested address but its login identity is a different string
- **THEN** send uses the explicitly matched sending identity for that address
- **AND THEN** it does not choose an unrelated first identity

#### Scenario: Multiple accounts have no unambiguous selection
- **WHEN** discovery presents multiple accounts without a valid explicit or unambiguous primary selection
- **THEN** attachment reports the ambiguity before activating a binding

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

A ready account SHALL support writable JMAP submission, authorize the sending identity, and identify an unambiguous Inbox, Sent, and Archive. Credentials SHALL support the claimed mode's operations. For a protected mode, readiness SHALL verify ordinary mailbox rights separately from the independent management authority's placement rights.

#### Scenario: The account has a usable role map

- **WHEN** validation resolves the sending identity and role map
- **THEN** ordinary readiness verifies Inbox read, seen and keyword updates, and Sent add rights
- **AND THEN** Inbox removal and Archive add rights qualify placement operations separately
- **AND THEN** protected readiness requires the runtime rights needed for submission and authorized reads and updates and verifies placement rights through the trusted authority

#### Scenario: A mailbox with the name Archive lacks the role

- **WHEN** validation finds a folder named Archive without the provider's `archive` role
- **THEN** readiness reports the missing role and asks the operator to repair it

#### Scenario: A permission prevents normal mailbox operations

- **WHEN** a permission required for the selected mode is missing or denied
- **THEN** readiness identifies the relevant role and right before declaring the account ready for that mode

### Requirement: Protected Stalwart placement requires independent provider control

Stalwart SHALL support protected blocklists only when an independent trusted management path can verify owner-signed rule changes and configure native delivery directly to Archive for matches. Management credentials SHALL stay outside the gateway and ordinary mail runtime. Runtime credentials SHALL lack provider rights to change rules or override protected placement.

#### Scenario: Stalwart accepts an owner-authorized mail policy

- **WHEN** the independent management authority verifies an owner-signed update scoped to the exact provider account and binding
- **THEN** it commits the supported rules through provider-native controls
- **AND THEN** the provider files matching new arrivals directly in Archive, skipping Inbox even while the gateway is unavailable
- **AND THEN** prior messages retain their current folders when the provider accepts the update

#### Scenario: Provider authority falls short of protected placement

- **WHEN** the provider cannot match the configured sender and file directly in Archive on delivery, or the runtime credentials can change rules or override protected placement through any provider access path
- **THEN** the management path reports protected operation as unsupported
- **AND THEN** ordinary mailbox attachment and use remain available under their existing checks
- **AND THEN** the request leaves the provider's active rules and existing folder placement intact
