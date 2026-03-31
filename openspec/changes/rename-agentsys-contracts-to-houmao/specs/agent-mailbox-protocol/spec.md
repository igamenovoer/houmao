## MODIFIED Requirements

### Requirement: Principal-based mailbox addressing
The system SHALL address mailbox participants by mailbox principal rather than by a transient session handle.

Each mailbox principal SHALL include:
- a stable `principal_id`, and
- an email-like address suitable for the selected transport.

For agent participants, the system SHALL use the canonical `HOUMAO-...` agent identity as the default `principal_id` unless an explicit mailbox binding overrides it.

#### Scenario: Agent mailbox uses canonical agent identity
- **WHEN** an agent participant with canonical identity `HOUMAO-research` is registered for mailbox delivery
- **THEN** the system addresses that participant using `principal_id=HOUMAO-research`
- **AND THEN** outbound mailbox messages preserve the participant's configured email-like address separately from any live session manifest path

#### Scenario: Human mailbox uses the same principal model
- **WHEN** a human participant is registered for mailbox delivery
- **THEN** the system assigns that participant a stable mailbox principal
- **AND THEN** messages to or from that participant use the same canonical sender and recipient fields as agent participants

