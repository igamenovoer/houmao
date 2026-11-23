# gateway-web-entry Delta

## MODIFIED Requirements

### Requirement: Gateway issues a browser entry ticket for one live Web execution

`POST /v1/web/entry-ticket` SHALL verify the current owned Web binding and return an owner-local `url` and `expires_at_utc` for a ticket valid for 60 seconds. Discovery SHALL keep publishing the clean native origin and session identity. The gateway protocol reference and command help SHALL describe the entry routes.

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

#### Scenario: An unsigned client requests entry on an open gateway

- **WHEN** a direct owner-local request selects a verified live Web execution with a valid empty roster
- **THEN** the gateway returns the same one-time URL and 60-second expiry as signed issuance
- **AND THEN** the result omits native sign-in data

### Requirement: Browser redemption consumes a ticket once

A bare `GET /v1/web/enter` SHALL redirect immediately with HTTP 302 for a live verified Web execution and valid empty roster. With enrolled keys it SHALL show the login page. Ticket redemption SHALL require exactly one ticket parameter, allow at most one consumption, and redirect only after live verification.

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

- **WHEN** a browser opens the owner-local Web entry URL with an empty query and the live roster is valid and empty
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

- **WHEN** an admin enters a private key file path in the login page
- **THEN** the generated command uses the normalized path on the admin's machine and quotes spaces within the path and shell metacharacters literally
- **AND THEN** the callback carries the proof without carrying the path, key file, or passphrase

#### Scenario: The path is blank and the SSH agent holds multiple keys

- **WHEN** the command can sign with several supported keys offered by the local SSH agent
- **THEN** it submits candidate signatures for the same challenge
- **AND THEN** one currently enrolled valid signer can approve the login even if earlier candidates are unenrolled

#### Scenario: No available signer can complete the challenge

- **WHEN** the terminal has no supported SSH agent key or none of its submitted signatures verifies against a current admin enrollment
- **THEN** the operator gets a safe failure and can select a local key path or start again
- **AND THEN** the browser receives no entry ticket

#### Scenario: An administrator pastes surrounding whitespace with an absolute path

- **WHEN** the admin enters an absolute path padded with whitespace
- **THEN** the command passes the trimmed absolute path to `ssh-keygen` without a relative prefix

#### Scenario: The key path field contains only whitespace

- **WHEN** trimming the field leaves an empty string
- **THEN** the generated command uses the local SSH-agent signing path

### Requirement: A ticket applies to its current gateway and native execution

Tickets SHALL be bound to one live gateway instance, execution owner, managed agent and generation, runtime session, native Web host, and native session incarnation. Redemption SHALL verify the binding and current issuing authority before redirecting. An anonymous ticket SHALL also require its original empty roster revision. The gateway SHALL discard its tickets when it exits.

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

#### Scenario: Membership changes before anonymous ticket redemption

- **WHEN** an anonymous ticket is redeemed after the roster revision changes
- **THEN** the gateway refuses redemption, even if the roster has since become empty again

### Requirement: Tickets and native credentials remain outside ordinary gateway output

The gateway SHALL send `Cache-Control: no-store` and `Referrer-Policy: no-referrer` on Web entry and login responses. Tickets SHALL appear only in authorized issuance or approved browser claim results. Native sign-in parameters SHALL appear only in the verified browser redirect. Public state, usage, errors, and logs SHALL omit proof, claim secrets, tickets, and native credentials.

#### Scenario: A caller submits an invalid ticket or native entry fails

- **WHEN** an invalid proof or bearer, or a provider error, reaches a Web entry or login route
- **THEN** the gateway returns fixed sanitized error details
- **AND THEN** route diagnostics carry neither raw query strings nor redirect locations

#### Scenario: The browser has already signed in

- **WHEN** the gateway ticket expires or the gateway restarts after native browser authentication
- **THEN** the native provider's own session and credential lifetime govern the existing browser connection
