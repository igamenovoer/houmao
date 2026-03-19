## MODIFIED Requirements

### Requirement: Shared mailbox operations map cleanly to standard email semantics
The shared mailbox operation contract SHALL preserve semantics that can be mapped onto standard email surfaces, and the `stalwart` transport SHALL implement that mapping through real email-backed mailbox behavior for the mailbox functions shared with the filesystem transport.

At minimum, the implemented mapping SHALL preserve:

- sender and recipient identities,
- `subject`,
- reply ancestry through standard email reply headers,
- opaque message references suitable for later `reply` targeting,
- body semantics needed for `check`, `send`, and `reply`,
- attachment metadata needed to compose and retrieve delivered attachments.

#### Scenario: Mail check maps onto a real email-backed transport
- **WHEN** a mailbox-enabled session performs `check` through the `stalwart` transport
- **THEN** the transport returns normalized mailbox message metadata derived from real email-backed Stalwart mailbox behavior
- **AND THEN** the resulting check preserves sender, recipient, subject, body-preview, and reply-target meaning without requiring a filesystem canonical-message corpus

#### Scenario: Reply ancestry maps onto standard email reply headers
- **WHEN** a sender replies to an existing mailbox message through the `stalwart` transport
- **THEN** the transport preserves reply ancestry through standard email-compatible reply headers such as `Message-ID`, `In-Reply-To`, and `References`
- **AND THEN** the mailbox workflow keeps the same logical conversation meaning without relying on subject-only heuristics

## REMOVED Requirements

### Requirement: True-email transport implementation is out of scope for this change
**Reason**: This change introduces an implemented Stalwart-backed true-email transport instead of reserving that work for a follow-up change.

**Migration**: Use the Stalwart-backed mailbox transport requirements and runtime bindings defined by this change when selecting a real email-backed mailbox transport.
