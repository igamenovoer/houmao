## MODIFIED Requirements

### Requirement: Runtime-owned mailbox system skills are available to launched agents
The system SHALL provide implemented mailbox access to agents through runtime-owned mailbox system skills projected from platform-owned templates rather than requiring role-authored mailbox skill content.

These mailbox system skills SHALL be projected into mailbox-enabled sessions in a discoverable non-hidden tool-native location under the active skill destination using the same active skill-destination contract as other projected skills.

For Claude sessions whose active skill destination root is `skills` under `CLAUDE_CONFIG_DIR`, the mailbox system skill surface SHALL use top-level Houmao-owned skill directories rather than `skills/mailbox/...`.

For current non-Claude adapters whose active skill destination is `skills` or `.gemini/skills`, the mailbox system skill surface MAY continue to use the reserved visible mailbox subtree.

The projected mailbox skill set MAY vary by the selected mailbox transport, including filesystem-backed and real-mail-backed transports.

#### Scenario: Filesystem mailbox-enabled Claude agent receives native mailbox system skills
- **WHEN** the runtime starts a Claude session with filesystem mailbox support enabled
- **THEN** the runtime projects the mailbox system skill set for that session from platform-owned templates into the Claude active skill destination
- **AND THEN** the filesystem mailbox skill is available through top-level Houmao-owned skill directories discoverable by Claude native skill lookup
- **AND THEN** those mailbox system skills are available to the agent without requiring the role or recipe to select or author a mailbox-specific skill manually

#### Scenario: Stalwart mailbox-enabled Claude agent receives native mailbox system skills
- **WHEN** the runtime starts a Claude session with `stalwart` mailbox support enabled
- **THEN** the runtime projects the mailbox system skill set for that session from platform-owned templates into the Claude active skill destination
- **AND THEN** the Stalwart mailbox skill is available through top-level Houmao-owned skill directories discoverable by Claude native skill lookup
- **AND THEN** those mailbox system skills are available to the agent without requiring the role or recipe to select or author a mailbox-specific skill manually

#### Scenario: Non-Claude mailbox-enabled agent retains discoverable mailbox subtree
- **WHEN** the runtime starts a non-Claude agent session with mailbox support enabled
- **THEN** the runtime projects the mailbox system skill set for that session from platform-owned templates into the active skill destination
- **AND THEN** the mailbox skills remain available through the discoverable mailbox subtree rather than through hidden `.system` entries
- **AND THEN** those mailbox system skills are available to the agent without requiring the role or recipe to select or author a mailbox-specific skill manually

#### Scenario: Runtime-owned mailbox skills stay separate from role-authored skills
- **WHEN** an agent session includes both role-authored skills and runtime-owned mailbox system skills
- **THEN** runtime-owned mailbox skills remain distinguishable through reserved Houmao-owned skill names and tool-native projected paths
- **AND THEN** the agent can use those mailbox system skills without overriding or depending on role-authored skill content

#### Scenario: Hidden mailbox compatibility mirror is not projected
- **WHEN** the runtime projects mailbox system skills for a mailbox-enabled session
- **THEN** the runtime does not create a parallel hidden `.system/mailbox/...` mailbox skill tree for that session
- **AND THEN** Claude sessions do not rely on a parallel `skills/mailbox/...` compatibility mirror for ordinary mailbox-skill discovery
- **AND THEN** ordinary mailbox-skill discovery and prompting depend only on the visible tool-native mailbox skill surface

### Requirement: Runtime-owned mailbox skill projection separates gateway operations from transport-specific guidance and uses Houmao-owned skill naming
The system SHALL project a round-oriented runtime-owned mailbox workflow skill for gateway-notified email processing into every mailbox-enabled session in addition to the lower-level common gateway mailbox skill and the active transport-specific mailbox skill.

Projected Houmao-owned mailbox skills SHALL use a `houmao-<skillname>` naming convention under the visible tool-native mailbox skill surface so runtime-owned Houmao skills are distinguishable from role-authored or third-party skill names.

That `houmao-<skillname>` convention SHALL also define the activation boundary for Houmao-owned skills: the instruction text must include the keyword `houmao` when it intends to trigger a Houmao-owned skill.

For Claude sessions whose active skill destination root is `skills`, the round-oriented workflow skill SHALL be available at `skills/houmao-process-emails-via-gateway/`.

For Claude sessions whose active skill destination root is `skills`, the lower-level common gateway mailbox skill SHALL be available at `skills/houmao-email-via-agent-gateway/`.

For current non-Claude adapters whose active skill destination root remains namespaced, the round-oriented workflow skill and lower-level common gateway mailbox skill MAY continue to be available under the visible mailbox subtree.

The round-oriented workflow skill SHALL:
- act as the default installed runtime-owned procedure for notifier-triggered shared mailbox processing rounds when a live gateway facade is available,
- define metadata-first triage, relevant-message selection, selective inspection, work execution, and post-success mark-read behavior for the current round,
- tell the agent to stop after the current round and wait for the next notification rather than proactively polling for more mail.

The common gateway skill SHALL:
- remain a lower-level protocol and reference skill for live discovery, check, read, send, reply, and mark-read behavior,
- continue to publish explicit resolver and endpoint guidance for the shared `/v1/mail/*` surface,
- support the round-oriented workflow skill rather than replacing it as the notifier-facing entrypoint.

Transport-specific mailbox skills such as `houmao-email-via-filesystem` and `houmao-email-via-stalwart` SHALL remain projected and SHALL narrow their ordinary guidance to transport validation, transport-specific context, and fallback behavior when the gateway facade is unavailable.

#### Scenario: Claude mailbox-enabled session receives processing, gateway, and transport runtime-owned skills
- **WHEN** the runtime starts a mailbox-enabled Claude session
- **THEN** it projects `skills/houmao-process-emails-via-gateway/` into the active skill destination
- **AND THEN** it also projects `skills/houmao-email-via-agent-gateway/` and the runtime-owned mailbox skill for the active transport
- **AND THEN** Claude can discover all of those skills through native skill discovery without relying on a mailbox namespace subtree

#### Scenario: Non-Claude mailbox-enabled session receives processing, gateway, and transport runtime-owned skills
- **WHEN** the runtime starts a mailbox-enabled non-Claude session
- **THEN** it projects the processing, gateway, and transport mailbox skills into the active skill destination under the visible mailbox subtree
- **AND THEN** the agent can discover all of those skills from that visible mailbox subtree without relying on hidden `.system` entries

#### Scenario: Houmao-owned mailbox skill naming requires explicit `houmao` invocation
- **WHEN** a runtime-owned mailbox skill is intended to be triggered through agent instructions
- **THEN** that skill uses a `houmao-<skillname>` name
- **AND THEN** the instruction text includes the keyword `houmao` when it intends to trigger that Houmao-owned skill
- **AND THEN** ordinary non-Houmao wording does not rely on implicit activation of the Houmao-owned skill

#### Scenario: Processing skill is treated as installed operational guidance for notifier rounds
- **WHEN** a mailbox-enabled session has the shared gateway mailbox facade available
- **THEN** the runtime-owned `houmao-process-emails-via-gateway` skill is already projected into that session through the tool-native visible mailbox skill surface
- **AND THEN** notifier prompts may instruct the agent to use that installed skill directly for the current mailbox round

#### Scenario: Gateway mailbox skill remains the lower-level protocol reference
- **WHEN** an agent opens the installed `houmao-email-via-agent-gateway` skill document from the visible mailbox skill surface for its tool
- **THEN** that entry document continues to point the agent at lower-level action-specific subdocuments for resolver and `/v1/mail/*` operations
- **AND THEN** it does not replace the round-oriented processing workflow skill as the notifier-facing entrypoint

#### Scenario: Transport-specific mailbox skill narrows to transport context and fallback
- **WHEN** an agent opens the installed transport-specific `houmao-email-via-filesystem` skill or `houmao-email-via-stalwart` skill document from the visible mailbox skill surface for its tool
- **THEN** that transport skill explains transport-specific constraints, references, and no-gateway fallback behavior
- **AND THEN** it points the agent at the installed `houmao-email-via-agent-gateway` and `houmao-process-emails-via-gateway` skills for shared gateway mailbox workflow and operation guidance instead of duplicating both layers
