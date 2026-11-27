# Spec Delta

## ADDED Requirements

### Requirement: Anonymous callers can view the owner-local terminal

The gateway SHALL supply the public read effect `terminal.view` on `native:terminal` to anonymous callers at the direct owner-local terminal routes. A verified live tmux binding and the terminal transport checks SHALL determine viewer eligibility independently of roster mode, default permissions, or administrator proof.

#### Scenario: An unsigned caller views on a keyed gateway

- **WHEN** an anonymous browser uses the direct owner-local viewer for a verified live tmux session on a keyed gateway
- **THEN** the browser can watch without a login, signer, or default permission grant
- **AND THEN** the browser receives no interactive authority

### Requirement: Terminal interaction requires current per-key administrator proof

The gateway SHALL require `admin.terminal.interact` on `native:terminal` and caller proof from an exact currently enrolled administrator key for the admin terminal route. This is an operation-specific prerequisite. Open, default, peer, managed-self, relay, and native Web entry authority SHALL NOT substitute for enrolled administrator proof.

#### Scenario: A caller tries interactive entry under open or default authority

- **WHEN** an unsigned caller uses a verified empty roster, or a caller without an enrolled administrator key draws authority from an `agent-admin` default or scoped grant
- **THEN** the gateway refuses interactive issuance, claim, and stream admission before starting a PTY
- **AND THEN** first-key enrollment retains its existing proof requirements and owner-local viewer access remains anonymous

#### Scenario: An enrolled administrator authorizes interaction

- **WHEN** an operator proves possession of a key with a current administrator qualification for the selected gateway target
- **THEN** the gateway may issue an interactive grant for that exact target and administrator enrollment

#### Scenario: An SSH agent offers several signing keys

- **WHEN** interactive sign-in receives valid candidate signatures from a nonadministrator and a current enrolled administrator
- **THEN** the gateway selects a candidate that satisfies the actual interactive authority requirement

### Requirement: Terminal entry grants are purpose-bound and single use

Terminal login and one-time connection grants SHALL bind the mode, gateway instance, agent incarnation, verified tmux session, and original authorization basis. The initiating browser SHALL claim login once. The gateway SHALL require the exact owner-local transport and check the browser Origin for the WebSocket. Terminal grants and native Web redirect tickets SHALL authorize only their respective operations.

#### Scenario: A browser tries to replay or change the purpose of a grant

- **WHEN** a browser presents an expired, already consumed, wrong-mode, wrong-listener, or native Web grant to a terminal stream
- **THEN** the gateway refuses it without starting a PTY or disclosing output

#### Scenario: A terminal request arrives through an unapproved transport

- **WHEN** an issuance request or WebSocket arrives through advertised HTTP proxy ingress, a passive relay, an executor route, or with a mismatched origin
- **THEN** the gateway refuses terminal admission and provides owner-local connection guidance where the protocol permits it

### Requirement: Continuing terminal access remains subject to current authority

The gateway SHALL revalidate the current target before attaching and while each stream is active. For interactive streams it SHALL also revalidate the original administrator grant. After the original grant or target becomes invalid, the gateway SHALL stop forwarding terminal bytes and close the attachment. Terminal data, credentials, proofs, and link secrets SHALL be excluded from general logs and discovery.

#### Scenario: An administrator loses qualification while attached

- **WHEN** the key that authorized an interactive attachment loses its administrator qualification or is revoked
- **THEN** the gateway closes the attachment without continuing it under open, default, or view-only authority

#### Scenario: The roster changes during an anonymous view

- **WHEN** the roster or default permissions change during an anonymous view and the verified tmux binding remains live
- **THEN** the read-only stream remains available with its original session binding
