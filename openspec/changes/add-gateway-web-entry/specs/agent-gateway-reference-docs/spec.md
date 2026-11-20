# Spec Delta

## ADDED Requirements

### Requirement: Gateway reference documents owner-local Web browser entry

The gateway reference SHALL document the shared entry URL, terminal-assisted login, signed ticket issuance, and the scoped CLI. It SHALL explain enrolled signer selection, bearer handling, expiry, owner-loopback reachability, and the native provider's responsibility for authenticated browser sessions.

#### Scenario: An operator follows the Web entry instructions

- **WHEN** a reader needs to open a live managed Web agent
- **THEN** the reference shows how to open the bare entry URL, optionally select a local key file, and run the generated command with `ssh-keygen` and `curl`
- **AND THEN** it describes trusted endpoint review, blank-path SSH agent selection, automatic browser continuation, and starting again after expiry

#### Scenario: A script requests a Web entry ticket

- **WHEN** a reader follows the signed API or scoped CLI workflow
- **THEN** the reference shows how to obtain a one-time link that skips the login page
- **AND THEN** it tells the operator to keep the link private and explains native session selection after redemption

#### Scenario: The browser runs outside the execution context

- **WHEN** a reader configures access from another machine or network namespace
- **THEN** the reference explains the required gateway and native loopback forwards with exact addresses and ports, including the terminal callback's gateway address
- **AND THEN** it distinguishes this workflow from the advertised HTTPS gateway and explains that native session lifetime follows provider policy
