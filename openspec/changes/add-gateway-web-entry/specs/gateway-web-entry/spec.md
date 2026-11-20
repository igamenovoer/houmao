# Spec Delta

## Purpose

Let an enrolled operator or signed client open an already-running managed Web agent through a shared gateway entry URL backed by the provider's native authentication.

## ADDED Requirements

### Requirement: Gateway issues a browser entry ticket for one live Web execution

`POST /v1/web/entry-ticket` SHALL verify the current owned Web binding and return an owner-local `url` and `expires_at_utc` for a ticket valid for 60 seconds. Discovery SHALL keep publishing the clean native origin and session identity. The entry routes SHALL be discoverable through the gateway protocol reference and command help.

#### Scenario: An enrolled administrator requests entry

- **WHEN** a verified admin submits the request to the owner-local gateway of a live supported Web host
- **THEN** the gateway returns a fresh URL for `GET /v1/web/enter` and its expiry
- **AND THEN** the result omits the native sign-in parameters and API credentials

#### Scenario: The gateway has no verified live Web host

- **WHEN** a caller selects a stopped, replaced, unavailable, or unsupported native surface
- **THEN** the gateway refuses issuance with a safe diagnostic
- **AND THEN** the request creates no host, session, or replacement binding

#### Scenario: The native agent is busy

- **WHEN** a verified live Web execution is busy or awaiting human input
- **THEN** the gateway can issue an entry ticket for that execution independently of prompt admission

### Requirement: Browser redemption consumes a ticket once

`GET /v1/web/enter` SHALL show the interactive login page when the query is empty. Redemption SHALL require exactly one ticket parameter and at most one concurrent request SHALL consume it. After consumption and live verification, the gateway SHALL return HTTP 302 to the verified native authentication destination. The browser SHALL redeem with the ticket alone.

#### Scenario: An operator opens the shared URL without a ticket

- **WHEN** a browser opens the owner-local Web entry URL with an empty query
- **THEN** the gateway serves a page that can start interactive login for the bound agent
- **AND THEN** visiting the page grants no native access

#### Scenario: A browser redeems an unused ticket

- **WHEN** a browser submits the valid ticket on the issuer's owner-local endpoint
- **THEN** the gateway redirects it to the selected provider's verified native sign-in destination
- **AND THEN** the native application handles browser authentication through its existing protocol

#### Scenario: Two redemptions race

- **WHEN** two GET requests present the same valid ticket concurrently
- **THEN** at most one receives a redirect
- **AND THEN** the other receives a safe refusal without a `Location` header

#### Scenario: A ticket is expired, used, or sent to the wrong gateway

- **WHEN** redemption receives a ticket with no current unused grant at this gateway
- **THEN** the response refuses with HTTP 410 and links to the ticket-free entry page to start again
- **AND THEN** it omits the ticket, native credentials, and destination

### Requirement: The login page generates a local signing command

The page SHALL offer a copyable command for its pending challenge. The command SHALL use `ssh-keygen` to sign locally and `curl` to submit the proof. A supplied key path SHALL select that local file and remain local. An omitted path SHALL select the supported keys offered by the local SSH agent.

#### Scenario: An administrator chooses the local key file

- **WHEN** an admin enters a private key file path in the login page
- **THEN** the generated command uses that exact path on the admin's machine, including paths with spaces or shell metacharacters
- **AND THEN** the callback carries the proof without carrying the path, key file, or passphrase

#### Scenario: The path is blank and the SSH agent holds multiple keys

- **WHEN** the command can sign with several supported keys offered by the local SSH agent
- **THEN** it submits candidate signatures for the same challenge
- **AND THEN** one currently enrolled valid signer can approve the login even if earlier candidates are unenrolled

#### Scenario: No available signer can complete the challenge

- **WHEN** the terminal has no supported SSH agent key or none of its submitted signatures verifies against a current admin enrollment
- **THEN** the operator gets a safe failure and can select a local key path or start again
- **AND THEN** the browser receives no entry ticket

### Requirement: The initiating browser claims the approved login once

A pending login SHALL expire and stay bound to the initiating browser attempt, gateway instance, and live native execution. A terminal approval SHALL expose only its outcome to the terminal. The waiting browser SHALL claim the approval once, receive a normal entry ticket, and navigate to the shared entry URL automatically.

#### Scenario: The terminal approves a waiting browser

- **WHEN** the terminal submits a valid admin signature for the pending login
- **THEN** the browser uses its own claim proof to obtain one ticket and continues through normal redemption
- **AND THEN** the admin needs no signature copy or upload into the page

#### Scenario: A different browser tries to claim an approved login

- **WHEN** a second browser has the attempt identifier or the terminal command but lacks the initiating tab's claim proof
- **THEN** its request receives no ticket
- **AND THEN** it does not consume the original tab's approval

#### Scenario: A pending login expires or changes owner before claim

- **WHEN** the login expires, its gateway or native execution changes, or its approving admin is revoked
- **THEN** the browser receives safe fresh-login guidance and no ticket
- **AND THEN** the gateway never retargets the pending login

### Requirement: A ticket applies to its current gateway and native execution

Tickets SHALL be bound to one live gateway instance, execution owner, managed agent and generation, runtime session, native Web host, and native session incarnation. Redemption SHALL verify the binding and the issuing admin's current authority before redirecting. The gateway SHALL discard its tickets when it exits.

#### Scenario: Gateway restarts while the host remains live

- **WHEN** an operator redeems a ticket on a replacement gateway attached to the same agent
- **THEN** the new gateway refuses it and allows the operator to request a fresh ticket

#### Scenario: Exact continuation restores the same conversation

- **WHEN** the agent relaunches or a replacement host or native agent appears with the same exposed port or native session ID
- **THEN** the old ticket receives no redirect because its full execution binding has changed
- **AND THEN** redemption does not resume or retarget either conversation

#### Scenario: The issuing administrator is revoked

- **WHEN** a ticket was issued by an admin whose enrollment is no longer current
- **THEN** the gateway refuses redemption without releasing a native destination

### Requirement: The native backend supplies a trusted browser destination

The owner-side gateway SHALL use the live backend's verified origin, provider-owned path, and encoded query or fragment parameters. It SHALL accept only the native origin of the verified execution and preserve native host and browser authentication rules. Ticket callers SHALL have no control over the redirect target.

#### Scenario: A caller supplies a destination or native credential

- **WHEN** issuance or redemption includes a caller-supplied destination or extra authentication parameter
- **THEN** the gateway rejects the request without looking up or redirecting to that destination

#### Scenario: The listener has changed

- **WHEN** the recorded native browser destination no longer belongs to the expected owned host or session
- **THEN** redemption fails without releasing credentials or trying another destination

### Requirement: Entry uses the owner-local gateway and native addresses

The login page, terminal callback, browser claim, ticket issuance, and redemption SHALL require the configured owner-local HTTP origin on a loopback connection. The browser SHALL reach both listeners directly or through a private TCP tunnel preserving both loopback host and port pairs. The terminal SHALL reach the same gateway origin.

#### Scenario: A request arrives through an advertised HTTP proxy

- **WHEN** a caller tries interactive login, ticket issuance, or redemption through the advertised gateway address, passive proxy, or another origin
- **THEN** the entry operation refuses the request
- **AND THEN** the response provides owner-local guidance without emitting a ticket or native credential

#### Scenario: A browser uses the two private TCP forwards

- **WHEN** an operator deliberately forwards the exact gateway and verified native loopback addresses over a private tunnel
- **THEN** the browser can redeem at the gateway and complete provider authentication at the native address

### Requirement: Tickets and native credentials remain outside ordinary gateway output

The gateway SHALL send `Cache-Control: no-store` and `Referrer-Policy: no-referrer` on Web entry and login responses. Tickets SHALL appear only in signed issuance or approved browser claim results. Native sign-in parameters SHALL appear only in the redeeming browser's redirect. Public state, usage, errors, and logs SHALL omit proof, claim secrets, tickets, and native credentials.

#### Scenario: A caller submits an invalid ticket or native entry fails

- **WHEN** an invalid proof or bearer, or a provider error, reaches a Web entry or login route
- **THEN** the gateway returns fixed sanitized error details
- **AND THEN** route diagnostics carry neither raw query strings nor redirect locations

#### Scenario: The browser has already signed in

- **WHEN** the gateway ticket expires or the gateway restarts after native browser authentication
- **THEN** the native provider's own session and credential lifetime govern the existing browser connection
