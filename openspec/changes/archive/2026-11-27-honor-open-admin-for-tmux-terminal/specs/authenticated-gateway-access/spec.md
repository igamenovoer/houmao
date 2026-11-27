# Spec Delta

## RENAMED Requirements

- FROM: `### Requirement: Terminal interaction requires current per-key administrator proof`
- TO: `### Requirement: Terminal interaction accepts open or enrolled administrator authority`

## MODIFIED Requirements

### Requirement: Terminal interaction accepts open or enrolled administrator authority

The gateway SHALL require `admin.terminal.interact` on `native:terminal`. A verified empty roster SHALL provide open admin authority and permit unsigned entry. A keyed roster SHALL require caller proof from a current enrolled administrator key. The gateway SHALL verify any supplied proof and deny interaction when policy is unavailable. Default, scoped, managed-self, relay, and native Web entry authority SHALL NOT authorize interaction on a keyed roster.

#### Scenario: A caller tries interactive entry under open or default authority

- **WHEN** an unsigned caller requests interaction on a verified open gateway or a caller relies on default or scoped authority on a keyed gateway
- **THEN** the verified open gateway issues a one-time interactive ticket under its open admin authority
- **AND THEN** the keyed gateway refuses interactive issuance, claim, and stream admission from a caller relying on default or scoped authority
- **AND THEN** first-key enrollment retains its existing proof requirements and owner-local viewer access remains anonymous

#### Scenario: An enrolled administrator authorizes interaction

- **WHEN** an operator proves possession of a key with a current administrator qualification for the selected gateway target
- **THEN** the keyed gateway issues an interactive grant for that exact target and administrator enrollment

#### Scenario: An SSH agent offers several signing keys

- **WHEN** interactive sign-in receives valid candidate signatures from a nonadministrator and a current enrolled administrator
- **THEN** the gateway selects a candidate that satisfies the actual interactive authority requirement

#### Scenario: A caller supplies invalid proof to an open gateway

- **WHEN** a caller sends invalid proof with a terminal interaction request while the verified roster is empty
- **THEN** the gateway rejects the request without issuing an anonymous ticket

#### Scenario: Gateway policy is unavailable

- **WHEN** the gateway cannot verify its admin policy
- **THEN** the gateway refuses interactive entry and continues to allow an eligible anonymous viewer

### Requirement: Continuing terminal access remains subject to current authority

The gateway SHALL revalidate the current target before attaching and while each stream is active. Interactive access SHALL retain and revalidate the original open epoch or exact enrolled administrator qualification. After the original grant or target becomes invalid, the gateway SHALL stop forwarding terminal bytes and close the attachment. Terminal data, credentials, proofs, and link secrets SHALL be excluded from general logs and discovery.

#### Scenario: An administrator loses qualification while attached

- **WHEN** the key that authorized an interactive attachment loses its administrator qualification or is revoked, including removal of the final administrator
- **THEN** the gateway closes the attachment without continuing it under open, default, or view-only authority

#### Scenario: The roster changes during an anonymous view

- **WHEN** the roster or default permissions change during an anonymous view and the verified tmux binding remains live
- **THEN** the read-only stream remains available with its original session binding

#### Scenario: The first administrator enrolls after open issuance

- **WHEN** the first administrator enrolls after an open interactive ticket is issued
- **THEN** the earlier ticket cannot start a PTY
- **AND THEN** an interactive stream already admitted under the previous open epoch closes when that authority is lost

#### Scenario: A formerly open roster becomes empty again

- **WHEN** a gateway returns to an empty roster after a period with enrolled administrators
- **THEN** it accepts fresh open interactive requests and refuses tickets from any previous open epoch
