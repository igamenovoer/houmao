# gateway-web-entry Specification

## Purpose

Let an enrolled operator or signed client open an already-running managed Web agent through a shared gateway entry URL backed by the provider's native authentication.

## Requirements

### Requirement: Gateway issues a browser entry ticket for one live Web execution

`POST /v1/web/entry-ticket` SHALL authorize `web.enter` for the current owned Web binding and return an owner-local `url` and `expires_at_utc` for a ticket valid for 60 seconds. Discovery SHALL keep publishing the clean native origin and session identity. The gateway protocol reference and command help SHALL describe the entry routes.

#### Scenario: An enrolled administrator requests entry

- **WHEN** an enrolled administrator with current SSHSIG proof and `web.enter` permission submits the request to the owner-local gateway of a live supported Web host
- **THEN** the gateway returns a fresh URL for `GET /v1/web/enter` and its expiry
- **AND THEN** the result omits the native sign-in parameters and API credentials

#### Scenario: The gateway has no verified live Web host

- **WHEN** a caller selects a stopped, replaced, unavailable, or unsupported native surface
- **THEN** the gateway refuses issuance with a safe diagnostic
- **AND THEN** the request creates no host, session, or replacement binding

#### Scenario: The native agent is busy

- **WHEN** an authorized caller requests entry to a verified live Web execution that is busy or awaiting human input
- **THEN** the gateway can issue an entry ticket for that execution independently of prompt admission

#### Scenario: An unsigned client requests entry on an open gateway

- **WHEN** a direct owner-local request selects a verified live Web execution and the valid empty administrator roster supplies open gateway-admin permission for `web.enter`
- **THEN** the gateway returns the same one-time URL and 60-second expiry as signed issuance
- **AND THEN** the result omits native sign-in data

#### Scenario: A caller has scoped Web entry permission

- **WHEN** a verified caller holds `web.enter` permission for the bound Web execution but holds no administrator enrollment
- **THEN** issuance authorizes the scoped caller and returns one owner-local ticket

#### Scenario: A verified caller lacks Web entry permission

- **WHEN** a caller presents valid proof for a keyed target and its current policy denies `web.enter`
- **THEN** issuance returns HTTP 403 before resolving a native sign-in destination

### Requirement: Browser redemption consumes a ticket once

A bare `GET /v1/web/enter` SHALL redirect with HTTP 302 for a verified live Web execution when the valid empty administrator roster supplies open `web.enter` authority. With enrolled administrators it SHALL show the login page. Ticket redemption SHALL require exactly one ticket parameter, consume it at most once, and check current `web.enter` permission and the live binding before redirecting.

#### Scenario: An operator opens the shared URL without a ticket

- **WHEN** a browser opens the owner-local Web entry URL with an empty query while the roster has keys
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

#### Scenario: A browser opens the shared URL with an empty roster

- **WHEN** a browser opens the owner-local Web entry URL with an empty query and the valid empty administrator roster supplies open `web.enter` authority
- **THEN** it receives HTTP 302 directly to the verified native application
- **AND THEN** the handoff requires no Houmao login page, signing challenge, or ticket

#### Scenario: The roster becomes keyed during open browser entry

- **WHEN** the first key is enrolled before the gateway finishes verifying the anonymous handoff
- **THEN** that request receives no native sign-in location
- **AND THEN** a fresh navigation uses the keyed login flow

#### Scenario: The Web entry policy cannot be read

- **WHEN** a browser opens the shared URL and the selected gateway's required policy is unavailable
- **THEN** the gateway returns a safe policy error without a native location

### Requirement: The login page generates a local signing command

The page SHALL offer a copyable command that signs locally with `ssh-keygen` and submits proof with `curl`. It SHALL trim leading and trailing whitespace from the optional key path before choosing a signer and interpreting the path. A nonempty result SHALL select the local file with literal interior characters. An empty result SHALL select supported keys from the local SSH agent. The path SHALL remain local.

#### Scenario: An administrator chooses the local key file

- **WHEN** an administrator enters a private key file path in the login page
- **THEN** the generated command uses the normalized path on the administrator's machine and quotes spaces within the path and shell metacharacters literally
- **AND THEN** the callback carries the proof without carrying the path, key file, or passphrase

#### Scenario: The path is blank and the SSH agent holds multiple keys

- **WHEN** the command can sign with several supported keys offered by the local SSH agent
- **THEN** it submits candidate signatures for the same challenge
- **AND THEN** one currently verified signer with `web.enter` permission can approve the login even if earlier candidates have no such authority

#### Scenario: No available signer can complete the challenge

- **WHEN** the terminal has no supported SSH agent key or none of its submitted signatures establishes a current caller with `web.enter` permission
- **THEN** the operator gets a safe failure and can select a local key path or start again
- **AND THEN** the browser receives no entry ticket

#### Scenario: An administrator pastes surrounding whitespace with an absolute path

- **WHEN** the administrator enters an absolute path padded with whitespace
- **THEN** the command passes the trimmed absolute path to `ssh-keygen` without a relative prefix

#### Scenario: The key path field contains only whitespace

- **WHEN** trimming the field leaves an empty string
- **THEN** the generated command uses the local SSH-agent signing path

### Requirement: The initiating browser claims the approved login once

A pending login SHALL expire and stay bound to the initiating browser attempt, gateway instance, and live native execution. Approval SHALL verify SSHSIG and current `web.enter` permission and expose only its outcome to the terminal. The initiating browser SHALL recheck that permission when claiming one entry ticket and navigate to the shared entry URL.

#### Scenario: The terminal approves a waiting browser

- **WHEN** the terminal submits a valid signature from a current caller with `web.enter` permission for the pending login
- **THEN** the browser uses its own claim proof to obtain one ticket and continues through normal redemption
- **AND THEN** the operator needs no signature copy or upload into the page

#### Scenario: A different browser tries to claim an approved login

- **WHEN** a second browser has the attempt identifier or the terminal command but lacks the initiating tab's claim proof
- **THEN** its request receives no ticket
- **AND THEN** it does not consume the original tab's approval

#### Scenario: A pending login expires or changes owner before claim

- **WHEN** the login expires, its gateway or native execution changes, or its approving caller loses current proof authority or `web.enter` permission
- **THEN** the browser receives safe fresh-login guidance and no ticket
- **AND THEN** the gateway never retargets the pending login

### Requirement: A ticket applies to its current gateway and native execution

Tickets SHALL be bound to one live gateway instance, execution owner, agent generation, runtime session, native Web host, and native session incarnation. Redemption SHALL verify the binding and current `web.enter` permission with the original authority, including the exact admin enrollment or open epoch when applicable. The gateway SHALL discard its tickets when it exits.

#### Scenario: Gateway restarts while the host remains live

- **WHEN** an operator redeems a ticket on a replacement gateway attached to the same agent
- **THEN** the new gateway refuses it and allows the operator to request a fresh ticket

#### Scenario: Exact continuation restores the same conversation

- **WHEN** the agent relaunches or a replacement host or native agent appears with the same exposed port or native session ID
- **THEN** the old ticket receives no redirect because its full execution binding has changed
- **AND THEN** redemption does not resume or retarget either conversation

#### Scenario: The issuing administrator is revoked

- **WHEN** a ticket issued under named-admin authority reaches redemption after the signing credential or its admin enrollment is removed
- **THEN** the gateway refuses redemption without releasing a native destination

#### Scenario: Membership changes before anonymous ticket redemption

- **WHEN** an anonymous ticket is redeemed after the roster revision changes
- **THEN** the gateway refuses redemption, even if the roster has since become empty again

#### Scenario: A signed caller's open ticket outlives its authority

- **WHEN** a caller signs an entry request that relies on open admin authority and the open epoch changes before redemption
- **THEN** the gateway refuses the ticket even if the caller's key is still valid

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

The gateway SHALL send `Cache-Control: no-store` and `Referrer-Policy: no-referrer` on Web entry and login responses. Tickets SHALL appear only in authorized issuance or approved browser claim results. Native sign-in parameters SHALL appear only in the verified browser redirect. Public state, usage, errors, and logs SHALL omit proof, claim secrets, tickets, and native credentials.

#### Scenario: A caller submits an invalid ticket or native entry fails

- **WHEN** an invalid proof or bearer, or a provider error, reaches a Web entry or login route
- **THEN** the gateway returns fixed sanitized error details
- **AND THEN** route diagnostics carry neither raw query strings nor redirect locations

#### Scenario: The browser has already signed in

- **WHEN** the gateway ticket expires, the gateway restarts, or gateway entry permission is revoked after native browser authentication
- **THEN** the native provider's own session and credential lifetime govern the existing browser connection
