# Spec Delta

## ADDED Requirements

### Requirement: Browser entry issuance requires direct enrolled admin proof

Signed API ticket issuance SHALL require a direct, request-bound signature from a currently enrolled admin even when ordinary admin access is open. The gateway SHALL check proof and role before processing the request or reading native sign-in data. Browser redemption SHALL require the issued bearer and SHALL confer authority only to obtain the bound native redirect.

#### Scenario: The admin roster is empty

- **WHEN** a caller attempts issuance without proof or with an invalid signature
- **THEN** the gateway returns HTTP 401 with applicable challenge information
- **AND THEN** open admin access grants no ticket

#### Scenario: The current agent or a backing service requests issuance

- **WHEN** issuance presents valid self proof, a relay, or backing authority without direct enrolled admin proof
- **THEN** the gateway returns HTTP 403 before looking up the native destination

#### Scenario: A signed gateway client requests a ticket for the browser

- **WHEN** the client completes signed issuance
- **THEN** it receives the ticket result without a redirect
- **AND THEN** only the browser follows the redemption redirect, independently of public prompt enablement

### Requirement: Interactive Web login proof authorizes only its pending entry

The terminal callback SHALL verify a short-lived, purpose-specific challenge against a currently enrolled admin public key. The challenge SHALL bind browser attempt, gateway issuer, current execution, and approval operation. A valid proof SHALL authorize one browser claim for that attempt. The callback SHALL return only an outcome.

#### Scenario: A valid signature is mixed with unenrolled candidates

- **WHEN** one bounded callback submits multiple signatures for the exact challenge
- **THEN** the gateway approves the login if any signature verifies against a current admin enrollment
- **AND THEN** earlier unenrolled or invalid signatures do not consume the challenge before a valid candidate is checked

#### Scenario: A proof is replayed or used outside its purpose

- **WHEN** a caller reuses a successful proof or supplies it for another gateway, attempt, agent, or signed operation
- **THEN** the request grants no additional approval or ticket

#### Scenario: An unenrolled identity attempts approval

- **WHEN** only self, unknown-key, invalid, or delegated proof is available
- **THEN** the terminal receives a safe refusal without the admin roster or any browser or native credential
