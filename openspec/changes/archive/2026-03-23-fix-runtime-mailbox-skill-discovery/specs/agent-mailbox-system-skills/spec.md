## MODIFIED Requirements

### Requirement: Runtime-owned mailbox system skills are available to launched agents
The system SHALL provide implemented mailbox access to agents through runtime-owned mailbox system skills projected from platform-owned templates rather than requiring role-authored mailbox skill content.

These mailbox system skills SHALL be projected into mailbox-enabled sessions in a discoverable non-hidden mailbox subtree under the active skill destination using the same active skill-destination contract as other projected skills.

For the current tool adapters whose active skill destination is `skills`, the primary projected mailbox skill surface SHALL be `skills/mailbox/...`.

The runtime MAY also mirror the same mailbox system skill content into a reserved hidden namespace such as `skills/.system/mailbox/...` for compatibility or bootstrap reasons, but that hidden mirror SHALL NOT be the only normative mailbox skill surface for ordinary mailbox-skill discovery or prompting.

The projected mailbox skill set MAY vary by the selected mailbox transport, including filesystem-backed and real-mail-backed transports.

#### Scenario: Filesystem mailbox-enabled agent receives projected mailbox system skills
- **WHEN** the runtime starts an agent session with filesystem mailbox support enabled
- **THEN** the runtime projects the mailbox system skill set for that session from platform-owned templates into the active skill destination
- **AND THEN** the primary filesystem mailbox skill is available through the discoverable mailbox subtree rather than only through hidden `.system` entries
- **AND THEN** those mailbox system skills are available to the agent without requiring the role or recipe to select or author a mailbox-specific skill manually

#### Scenario: Stalwart mailbox-enabled agent receives projected mailbox system skills
- **WHEN** the runtime starts an agent session with `stalwart` mailbox support enabled
- **THEN** the runtime projects the mailbox system skill set for that session from platform-owned templates into the active skill destination
- **AND THEN** the primary Stalwart mailbox skill is available through the discoverable mailbox subtree rather than only through hidden `.system` entries
- **AND THEN** those mailbox system skills are available to the agent without requiring the role or recipe to select or author a mailbox-specific skill manually

#### Scenario: Runtime-owned mailbox skills stay separate from role-authored skills
- **WHEN** an agent session includes both role-authored skills and runtime-owned mailbox system skills
- **THEN** the mailbox system skills use a reserved runtime-owned mailbox subtree under the active skill destination
- **AND THEN** the agent can use those mailbox system skills without overriding or depending on role-authored skill content

#### Scenario: Compatibility mirror does not replace the discoverable mailbox subtree
- **WHEN** the runtime also projects a hidden compatibility mirror for mailbox system skills
- **THEN** the primary discoverable mailbox subtree remains present in the active skill destination
- **AND THEN** runtime-owned prompting does not need the hidden mirror to be the sole mailbox skill reference
