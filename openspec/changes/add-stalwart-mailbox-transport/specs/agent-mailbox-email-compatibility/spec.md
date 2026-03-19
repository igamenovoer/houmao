## MODIFIED Requirements

### Requirement: Canonical mailbox protocol maps cleanly to standard email semantics
The canonical mailbox protocol SHALL preserve semantics that can be mapped onto standard email surfaces, and the `stalwart` transport SHALL implement that mapping through real email-backed mailbox behavior.

At minimum, the implemented mapping SHALL preserve:

- sender and recipient identities,
- `subject`,
- reply ancestry through standard email reply headers,
- transport-safe thread correlation metadata,
- Markdown-authored message body semantics,
- attachment metadata needed to compose and retrieve delivered attachments.

#### Scenario: New message maps onto a real email-backed transport
- **WHEN** a sender delivers a mailbox message through the `stalwart` transport
- **THEN** the mailbox protocol fields are mapped onto real email-backed Stalwart mailbox behavior
- **AND THEN** the resulting delivery preserves sender, recipient, subject, body, and attachment meaning without requiring a filesystem canonical-message corpus

#### Scenario: Reply ancestry maps onto standard email reply headers
- **WHEN** a sender replies to an existing mailbox message through the `stalwart` transport
- **THEN** the transport preserves reply ancestry through standard email-compatible reply headers such as `Message-ID`, `In-Reply-To`, and `References`
- **AND THEN** the mailbox workflow keeps the same logical conversation meaning without relying on subject-only heuristics

## REMOVED Requirements

### Requirement: True-email transport implementation is out of scope for this change
**Reason**: This change introduces an implemented Stalwart-backed true-email transport instead of reserving that work for a follow-up change.

**Migration**: Use the Stalwart-backed mailbox transport requirements and runtime bindings defined by this change when selecting a real email-backed mailbox transport.
