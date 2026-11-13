# Spec Delta

## MODIFIED Requirements

### Requirement: Principal-based mailbox addressing
The system SHALL address participants through durable mailbox principals rather than transient sessions. Each principal SHALL include a stable principal ID and an address appropriate to the selected channel. For Houmao agents, the owner principal ID SHALL be the persisted `agent_id`, not a friendly name, preferred mail address, or provider login.

Human principals SHALL retain their own stable principal identities. Email participants that have no verified Houmao identity SHALL remain email participants; the system SHALL NOT synthesize an agent ID by hashing an incoming sender address or trusting an unverified sender-supplied ID.

#### Scenario: Agent mailbox uses canonical agent identity
- **WHEN** an agent named `HOUMAO-research` registers for mail using its persisted agent ID
- **THEN** its mailbox owner principal is that agent ID
- **AND THEN** its name, channel address, and runtime locator remain separate fields

#### Scenario: Human mailbox uses the same principal model
- **WHEN** a human participant is registered for delivery
- **THEN** the system preserves a stable human mailbox principal
- **AND THEN** its messages use the shared sender and recipient representation without claiming a Houmao agent identity

## ADDED Requirements

### Requirement: Mail operations select an explicit isolated channel
Mail operations SHALL select `offline` or `online` and identify the expected binding ID. Offline recipients SHALL resolve only in the selected registry; online recipients SHALL resolve through the online provider. The canonical mail identity SHALL NOT choose transport implicitly. A missing or mismatched channel or binding SHALL fail without fallback, bridging, forwarding, or address translation.

#### Scenario: Online-first identity does not redirect offline mail
- **WHEN** an agent with both bindings sends through `offline`
- **THEN** its sender address is its offline address and recipients are resolved in its registry
- **AND THEN** its preferred online address does not redirect that delivery

#### Scenario: Online recipient has only an offline binding
- **WHEN** an online send targets a known agent that has only an offline address
- **THEN** resolution fails explicitly
- **AND THEN** no offline send is attempted

#### Scenario: Cross-channel batch is rejected before side effects
- **WHEN** one send request mixes offline-scoped and online-scoped recipient references
- **THEN** validation rejects the whole request before delivery

### Requirement: Replies and lifecycle operations preserve message scope
Reply, read, mark, move, and archive SHALL validate the message's owner/channel/binding scope. Replies SHALL remain on the originating binding and preserve channel-local ancestry. Changes to canonical mail identity SHALL not retarget existing references or rewrite immutable delivered address snapshots.

#### Scenario: Preferred address changes during an offline conversation
- **WHEN** an offline participant later attaches online mail and replies to an existing offline message
- **THEN** the reply stays in offline mail with the offline sender address
- **AND THEN** the original thread and historical address snapshots remain intact

#### Scenario: Reference belongs to another binding
- **WHEN** a lifecycle request presents a reference from another agent or replaced account
- **THEN** it fails before modifying the selected mailbox
