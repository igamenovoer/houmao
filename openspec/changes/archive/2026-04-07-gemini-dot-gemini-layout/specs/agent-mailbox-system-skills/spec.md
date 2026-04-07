## MODIFIED Requirements

### Requirement: Runtime-owned mailbox system skills are available to launched agents
The system SHALL provide implemented mailbox access to agents through runtime-owned mailbox system skills projected from platform-owned templates rather than requiring role-authored mailbox skill content.

These mailbox system skills SHALL be projected into mailbox-enabled sessions in a discoverable non-hidden tool-native location under the active skill destination using the same active skill-destination contract as other projected skills.

For Claude sessions whose active skill destination root is `skills` under `CLAUDE_CONFIG_DIR`, the mailbox system skill surface SHALL use top-level Houmao-owned skill directories rather than `skills/mailbox/...`.

For Codex sessions whose active skill destination root remains `skills`, the mailbox system skill surface SHALL use top-level Houmao-owned skill directories rather than `skills/mailbox/...`.

For Gemini sessions whose active skill destination root is `.gemini/skills`, the mailbox system skill surface SHALL use top-level Houmao-owned skill directories rather than `.gemini/skills/mailbox/...`.

The projected mailbox skill set MAY vary by the selected mailbox transport, including filesystem-backed and real-mail-backed transports.

#### Scenario: Filesystem mailbox-enabled Claude agent receives native mailbox system skills
- **WHEN** the runtime starts a Claude session with filesystem mailbox support enabled
- **THEN** the runtime projects the mailbox system skill set for that session from platform-owned templates into the active skill destination
- **AND THEN** the filesystem mailbox skill is available through top-level Houmao-owned skill directories discoverable by Claude native skill lookup
- **AND THEN** those mailbox system skills are available to the agent without requiring the role or recipe to select or author a mailbox-specific skill manually

#### Scenario: Stalwart mailbox-enabled Claude agent receives native mailbox system skills
- **WHEN** the runtime starts a Claude session with `stalwart` mailbox support enabled
- **THEN** the runtime projects the mailbox system skill set for that session from platform-owned templates into the active skill destination
- **AND THEN** the Stalwart mailbox skill is available through top-level Houmao-owned skill directories discoverable by Claude native skill lookup
- **AND THEN** those mailbox system skills are available to the agent without requiring the role or recipe to select or author a mailbox-specific skill manually

#### Scenario: Codex mailbox-enabled agent receives top-level Houmao-owned skills
- **WHEN** the runtime starts a Codex mailbox-enabled session
- **THEN** the runtime projects the mailbox system skill set for that session from platform-owned templates into the active skill destination
- **AND THEN** the mailbox skills are available through top-level Houmao-owned skill directories discoverable by Codex native skill lookup
- **AND THEN** those mailbox system skills are available to the agent without requiring the role or recipe to select or author a mailbox-specific skill manually

#### Scenario: Gemini mailbox-enabled agent receives top-level Houmao-owned skills
- **WHEN** the runtime starts a Gemini mailbox-enabled session
- **THEN** the runtime projects the mailbox system skill set for that session from platform-owned templates into `.gemini/skills/`
- **AND THEN** the mailbox skills are available through top-level Houmao-owned Gemini skill directories rather than through `.gemini/skills/mailbox/...`
- **AND THEN** those mailbox system skills are available to the agent without requiring the role or recipe to select or author a mailbox-specific skill manually

#### Scenario: Runtime-owned mailbox skills stay separate from role-authored skills
- **WHEN** an agent session includes both role-authored skills and runtime-owned mailbox system skills
- **THEN** runtime-owned mailbox skills remain distinguishable through reserved Houmao-owned skill names and tool-native projected paths
- **AND THEN** the agent can use those mailbox system skills without overriding or depending on role-authored skill content

#### Scenario: Hidden mailbox compatibility mirror is not projected
- **WHEN** the runtime projects mailbox system skills for a mailbox-enabled session
- **THEN** the runtime does not create a parallel hidden `.system/mailbox/...` mailbox skill tree for that session
- **AND THEN** Claude and Codex sessions do not rely on a parallel `skills/mailbox/...` compatibility mirror for ordinary mailbox-skill discovery
- **AND THEN** Gemini sessions do not rely on a parallel `.gemini/skills/mailbox/...` compatibility mirror for ordinary mailbox-skill discovery
- **AND THEN** ordinary mailbox-skill discovery and prompting depend only on the visible tool-native mailbox skill surface

### Requirement: Runtime-owned mailbox skill projection separates gateway operations from transport-specific guidance and uses Houmao-owned skill naming
The system SHALL project a round-oriented runtime-owned mailbox workflow skill for gateway-notified email processing into every mailbox-enabled session in addition to the lower-level common gateway mailbox skill and the active transport-specific mailbox skill.

Projected Houmao-owned mailbox skills SHALL use a `houmao-<skillname>` naming convention under the visible tool-native mailbox skill surface so runtime-owned Houmao skills are distinguishable from role-authored or third-party skill names.

That `houmao-<skillname>` convention SHALL also define the activation boundary for Houmao-owned skills: the instruction text must include the keyword `houmao` when it intends to trigger a Houmao-owned skill.

For Claude sessions whose active skill destination root is `skills`, the round-oriented workflow skill SHALL be available at `skills/houmao-process-emails-via-gateway/`.

For Claude sessions whose active skill destination root is `skills`, the lower-level common gateway mailbox skill SHALL be available at `skills/houmao-email-via-agent-gateway/`.

For Codex sessions whose active skill destination root remains `skills`, the round-oriented workflow skill SHALL be available at `skills/houmao-process-emails-via-gateway/`.

For Codex sessions whose active skill destination root remains `skills`, the lower-level common gateway mailbox skill SHALL be available at `skills/houmao-email-via-agent-gateway/`.

For Gemini sessions whose active skill destination root is `.gemini/skills`, the round-oriented workflow skill SHALL be available at `.gemini/skills/houmao-process-emails-via-gateway/`.

For Gemini sessions whose active skill destination root is `.gemini/skills`, the lower-level common gateway mailbox skill SHALL be available at `.gemini/skills/houmao-email-via-agent-gateway/`.

For Gemini sessions, ordinary runtime-owned mailbox prompts SHALL invoke installed Houmao mailbox skills by skill name and SHALL NOT require the agent to open `.gemini/skills/.../SKILL.md` paths for ordinary mailbox rounds when those skills are already installed.

The round-oriented workflow skill SHALL:
- act as the default installed runtime-owned procedure for notifier-triggered shared mailbox processing rounds when a live gateway facade is available,
- assume the notifier round already provides the exact current gateway base URL,
- define gateway-API-first metadata triage, unread-listing, relevant-message selection, selective inspection, work execution, and post-success mark-read behavior for the current round,
- tell the agent to stop after the current round and wait for the next notification rather than proactively polling for more mail.

The common gateway skill SHALL:
- remain a lower-level protocol and reference skill for live discovery, status, check, send, reply, and mark-read behavior,
- use a gateway base URL already present in prompt/context when that URL is available,
- fall back to `houmao-mgr agents mail resolve-live` only when the current gateway base URL cannot be determined from prompt/context,
- support the round-oriented workflow skill rather than replacing it as the notifier-facing entrypoint.

Transport-specific mailbox skills such as `houmao-email-via-filesystem` and `houmao-email-via-stalwart` SHALL remain projected and SHALL narrow their ordinary guidance to transport validation, transport-specific context, and fallback behavior when the gateway facade is unavailable.

#### Scenario: Claude mailbox-enabled session receives processing, gateway, and transport runtime-owned skills
- **WHEN** the runtime starts a mailbox-enabled Claude session
- **THEN** it projects `skills/houmao-process-emails-via-gateway/` into the active skill destination
- **AND THEN** it also projects `skills/houmao-email-via-agent-gateway/` and the runtime-owned mailbox skill for the active transport
- **AND THEN** Claude can discover all of those skills through native skill discovery without relying on a mailbox namespace subtree

#### Scenario: Codex mailbox-enabled session receives processing, gateway, and transport runtime-owned skills
- **WHEN** the runtime starts a mailbox-enabled Codex session
- **THEN** it projects `skills/houmao-process-emails-via-gateway/`, `skills/houmao-email-via-agent-gateway/`, and the runtime-owned mailbox skill for the active transport into the active skill destination
- **AND THEN** the agent can discover all of those skills through native skill discovery without relying on a mailbox namespace subtree or hidden `.system` entries

#### Scenario: Gemini mailbox-enabled session receives native top-level runtime-owned skills
- **WHEN** the runtime starts a mailbox-enabled Gemini session
- **THEN** it projects `.gemini/skills/houmao-process-emails-via-gateway/`, `.gemini/skills/houmao-email-via-agent-gateway/`, and the runtime-owned mailbox skill for the active transport into the active skill destination
- **AND THEN** Gemini can discover all of those skills through native skill discovery without relying on a `mailbox/` namespace subtree

#### Scenario: Houmao-owned mailbox skill naming requires explicit `houmao` invocation
- **WHEN** a runtime-owned mailbox skill is intended to be triggered through agent instructions
- **THEN** that skill uses a `houmao-<skillname>` name
- **AND THEN** the instruction text includes the keyword `houmao` when it intends to trigger that Houmao-owned skill
- **AND THEN** ordinary non-Houmao wording does not rely on implicit activation of the Houmao-owned skill

#### Scenario: Processing skill is treated as installed operational guidance for notifier rounds
- **WHEN** a mailbox-enabled session has the shared gateway mailbox facade available
- **THEN** the runtime-owned `houmao-process-emails-via-gateway` skill is already projected into that session through the tool-native visible mailbox skill surface
- **AND THEN** notifier prompts may instruct the agent to use that installed skill directly for the current mailbox round

#### Scenario: Gemini notifier prompt invokes the installed skill by name
- **WHEN** a mailbox-enabled Gemini session has the shared gateway mailbox facade available
- **AND WHEN** the runtime submits a notifier-driven mailbox round prompt
- **THEN** that prompt tells Gemini to use the installed `houmao-process-emails-via-gateway` skill by name
- **AND THEN** the prompt does not require Gemini to open `.gemini/skills/.../SKILL.md` for that ordinary mailbox round

#### Scenario: Gateway mailbox skill remains the lower-level protocol reference
- **WHEN** an agent opens the installed `houmao-email-via-agent-gateway` skill document from the visible mailbox skill surface for its tool
- **THEN** that entry document continues to point the agent at lower-level action-specific subdocuments for resolver and `/v1/mail/*` operations
- **AND THEN** it does not replace the round-oriented processing workflow skill as the notifier-facing entrypoint

#### Scenario: Gateway mailbox skill reuses context-provided base URL before falling back to manager discovery
- **WHEN** an agent opens the installed `houmao-email-via-agent-gateway` skill document from the visible mailbox skill surface for its tool
- **AND WHEN** the current prompt or recent mailbox context already provides the exact gateway base URL
- **THEN** that skill tells the agent to use the context-provided gateway URL directly
- **AND THEN** it does not require the agent to rerun manager discovery first

#### Scenario: Transport-specific mailbox skill narrows to transport context and fallback
- **WHEN** an agent opens the installed transport-specific `houmao-email-via-filesystem` skill or `houmao-email-via-stalwart` skill document from the visible mailbox skill surface for its tool
- **THEN** that transport skill explains transport-specific constraints, references, and no-gateway fallback behavior
- **AND THEN** it points the agent at the installed `houmao-email-via-agent-gateway` and `houmao-process-emails-via-gateway` skills for shared gateway mailbox workflow and operation guidance instead of duplicating both layers
