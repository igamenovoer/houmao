## REMOVED Requirements

### Requirement: Runtime-owned mailbox system skills are available to launched agents
**Reason**: The mailbox skill surface no longer projects separate top-level ordinary-mailbox skills per transport.
**Migration**: Project `houmao-agent-email-comms` plus `houmao-process-emails-via-gateway`, and move transport-specific ordinary mailbox guidance into internal pages of the unified skill.

### Requirement: Runtime-owned mailbox skill projection separates gateway operations from transport-specific guidance and uses Houmao-owned skill naming
**Reason**: Ordinary mailbox guidance is now unified under one installed skill instead of three separate top-level skills.
**Migration**: Replace `houmao-email-via-agent-gateway`, `houmao-email-via-filesystem`, and `houmao-email-via-stalwart` with `houmao-agent-email-comms`, while keeping `houmao-process-emails-via-gateway` as the separate workflow skill.

### Requirement: Runtime-owned mailbox skills use the manager-owned live resolver as the ordinary gateway discovery contract
**Reason**: Gateway discovery is still required, but the discovery contract now belongs to the unified `houmao-agent-email-comms` skill rather than to a dedicated top-level gateway mailbox skill.
**Migration**: Route ordinary shared-mailbox discovery through `houmao-agent-email-comms`, which uses prompt-provided `gateway.base_url` first and `houmao-mgr agents mail resolve-live` as fallback.

## ADDED Requirements

### Requirement: Runtime-owned mailbox system skills are available to launched agents through a unified Houmao mailbox surface
The system SHALL provide implemented mailbox access to agents through runtime-owned mailbox system skills projected from platform-owned templates rather than requiring role-authored mailbox skill content.

These mailbox system skills SHALL be projected into mailbox-enabled sessions in a discoverable non-hidden tool-native location under the active skill destination using the same active skill-destination contract as other projected skills.

For Claude sessions whose active skill destination root is `skills` under `CLAUDE_CONFIG_DIR`, the mailbox system skill surface SHALL use top-level Houmao-owned skill directories rather than `skills/mailbox/...`.

For Codex sessions whose active skill destination root remains `skills`, the mailbox system skill surface SHALL use top-level Houmao-owned skill directories rather than `skills/mailbox/...`.

For Gemini sessions whose active skill destination root is `.gemini/skills`, the mailbox system skill surface SHALL use top-level Houmao-owned skill directories rather than `.gemini/skills/mailbox/...`.

For every mailbox-enabled session, the top-level visible Houmao mailbox skill surface SHALL include:

- `houmao-process-emails-via-gateway`
- `houmao-agent-email-comms`

The top-level installed mailbox skill names SHALL remain the same across supported mailbox transports, and transport-specific ordinary mailbox guidance SHALL be discovered inside `houmao-agent-email-comms` rather than through separate installed top-level skill directories.

Runtime-owned mailbox skills SHALL remain distinguishable from role-authored skills through reserved Houmao-owned skill names and tool-native projected paths.

The runtime SHALL NOT create a parallel hidden `.system/mailbox/...` mailbox skill tree for ordinary mailbox-skill discovery.

#### Scenario: Filesystem mailbox-enabled Claude agent receives the unified mailbox surface
- **WHEN** the runtime starts a Claude session with filesystem mailbox support enabled
- **THEN** the runtime projects the mailbox system skill set for that session from platform-owned templates into the active skill destination
- **AND THEN** `houmao-process-emails-via-gateway` and `houmao-agent-email-comms` are available through top-level Houmao-owned skill directories discoverable by Claude native skill lookup
- **AND THEN** filesystem-specific ordinary mailbox guidance is available through the unified skill rather than through a separate top-level filesystem mailbox skill

#### Scenario: Stalwart mailbox-enabled Claude agent receives the unified mailbox surface
- **WHEN** the runtime starts a Claude session with `stalwart` mailbox support enabled
- **THEN** the runtime projects the mailbox system skill set for that session from platform-owned templates into the active skill destination
- **AND THEN** `houmao-process-emails-via-gateway` and `houmao-agent-email-comms` are available through top-level Houmao-owned skill directories discoverable by Claude native skill lookup
- **AND THEN** Stalwart-specific ordinary mailbox guidance is available through the unified skill rather than through a separate top-level Stalwart mailbox skill

#### Scenario: Codex mailbox-enabled agent receives the unified mailbox surface
- **WHEN** the runtime starts a Codex mailbox-enabled session
- **THEN** the runtime projects the mailbox system skill set for that session from platform-owned templates into the active skill destination
- **AND THEN** the mailbox skills are available through top-level Houmao-owned skill directories discoverable by Codex native skill lookup
- **AND THEN** those mailbox system skills are available to the agent without requiring the role or recipe to select or author a mailbox-specific skill manually

#### Scenario: Gemini mailbox-enabled agent receives the unified mailbox surface
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

### Requirement: Runtime-owned mailbox skill projection pairs a unified ordinary mailbox skill with the separate processing workflow
The system SHALL project a round-oriented runtime-owned mailbox workflow skill for gateway-notified email processing into every mailbox-enabled session in addition to a unified runtime-owned ordinary-mailbox skill.

Projected Houmao-owned mailbox skills SHALL use a `houmao-<skillname>` naming convention under the visible tool-native mailbox skill surface so runtime-owned Houmao skills are distinguishable from role-authored or third-party skill names.

That `houmao-<skillname>` convention SHALL also define the activation boundary for Houmao-owned skills: the instruction text must include the keyword `houmao` when it intends to trigger a Houmao-owned skill.

For Claude sessions whose active skill destination root is `skills`, the round-oriented workflow skill SHALL be available at `skills/houmao-process-emails-via-gateway/`.

For Claude sessions whose active skill destination root is `skills`, the unified ordinary-mailbox skill SHALL be available at `skills/houmao-agent-email-comms/`.

For Codex sessions whose active skill destination root remains `skills`, the round-oriented workflow skill SHALL be available at `skills/houmao-process-emails-via-gateway/`.

For Codex sessions whose active skill destination root remains `skills`, the unified ordinary-mailbox skill SHALL be available at `skills/houmao-agent-email-comms/`.

For Gemini sessions whose active skill destination root is `.gemini/skills`, the round-oriented workflow skill SHALL be available at `.gemini/skills/houmao-process-emails-via-gateway/`.

For Gemini sessions whose active skill destination root is `.gemini/skills`, the unified ordinary-mailbox skill SHALL be available at `.gemini/skills/houmao-agent-email-comms/`.

The round-oriented workflow skill SHALL:

- act as the default installed runtime-owned procedure for notifier-triggered shared mailbox processing rounds when a live gateway facade is available,
- assume the notifier round already provides the exact current gateway base URL,
- define gateway-API-first metadata triage, unread-listing, relevant-message selection, selective inspection, work execution, and post-success mark-read behavior for the current round,
- tell the agent to stop after the current round and wait for the next notification rather than proactively polling for more mail.

The unified ordinary-mailbox skill SHALL:

- remain the lower-level operational skill for live discovery, status, check, read, send, reply, and mark-read behavior,
- use a gateway base URL already present in prompt or context when that URL is available,
- fall back to `houmao-mgr agents mail resolve-live` only when the current gateway base URL cannot be determined from prompt or context,
- keep filesystem-specific and Stalwart-specific ordinary mailbox guidance as internal pages or references within the same skill package,
- support the round-oriented workflow skill rather than replacing it as the notifier-facing entrypoint.

The runtime SHALL NOT project separate top-level installed skill directories for `houmao-email-via-agent-gateway`, `houmao-email-via-filesystem`, or `houmao-email-via-stalwart` once the unified ordinary-mailbox skill is in use.

#### Scenario: Claude mailbox-enabled session receives the processing skill and unified ordinary-mailbox skill
- **WHEN** the runtime starts a mailbox-enabled Claude session
- **THEN** it projects `skills/houmao-process-emails-via-gateway/` and `skills/houmao-agent-email-comms/` into the active skill destination
- **AND THEN** Claude can discover both skills through native skill discovery without relying on a mailbox namespace subtree
- **AND THEN** the runtime does not also project separate top-level gateway, filesystem, or Stalwart ordinary-mailbox skills

#### Scenario: Codex mailbox-enabled session receives the processing skill and unified ordinary-mailbox skill
- **WHEN** the runtime starts a mailbox-enabled Codex session
- **THEN** it projects `skills/houmao-process-emails-via-gateway/` and `skills/houmao-agent-email-comms/` into the active skill destination
- **AND THEN** the agent can discover both skills through native skill discovery without relying on a mailbox namespace subtree or hidden `.system` entries
- **AND THEN** the runtime does not also project separate top-level gateway, filesystem, or Stalwart ordinary-mailbox skills

#### Scenario: Gemini mailbox-enabled session receives native top-level unified mailbox skills
- **WHEN** the runtime starts a mailbox-enabled Gemini session
- **THEN** it projects `.gemini/skills/houmao-process-emails-via-gateway/` and `.gemini/skills/houmao-agent-email-comms/` into the active skill destination
- **AND THEN** Gemini can discover both skills through native skill discovery without relying on a `mailbox/` namespace subtree
- **AND THEN** the runtime does not also project separate top-level gateway, filesystem, or Stalwart ordinary-mailbox skills

#### Scenario: Processing skill remains the notifier-round workflow entrypoint
- **WHEN** a mailbox-enabled session has the shared gateway mailbox facade available
- **THEN** the runtime-owned `houmao-process-emails-via-gateway` skill is already projected into that session through the tool-native visible mailbox skill surface
- **AND THEN** notifier prompts may instruct the agent to use that installed skill directly for the current mailbox round
- **AND THEN** ordinary mailbox actions within that round may rely on `houmao-agent-email-comms` as supporting material

#### Scenario: Unified ordinary-mailbox skill remains the operational reference
- **WHEN** an agent opens the installed `houmao-agent-email-comms` skill document from the visible mailbox skill surface for its tool
- **THEN** that entry document points the agent at internal action-specific or transport-specific subdocuments for resolver and mailbox-operation behavior
- **AND THEN** it does not replace `houmao-process-emails-via-gateway` as the notifier-facing entrypoint
- **AND THEN** it does not require a separate installed top-level transport skill for filesystem or Stalwart guidance

### Requirement: Unified ordinary-mailbox skill uses the manager-owned live resolver as the ordinary gateway discovery contract
Projected runtime-owned mailbox skills SHALL direct agents to the manager-owned live resolver `houmao-mgr agents mail resolve-live` only when current prompt or context does not already provide the exact current gateway base URL needed for shared `/v1/mail/*` mailbox operations.

When current prompt or context already provides the exact current gateway base URL, runtime-owned mailbox skills SHALL treat that URL as the authoritative endpoint prefix for the current mailbox work and SHALL NOT require redundant manager-based rediscovery.

When the manager-owned live resolver returns a `gateway` object, runtime-owned mailbox skills SHALL treat `gateway.base_url` as the exact current endpoint prefix for shared `/v1/mail/*` mailbox operations.

Projected runtime-owned mailbox skills SHALL NOT present `pixi run houmao-mgr agents mail resolve-live` as part of ordinary mailbox operation workflow.

Projected runtime-owned mailbox skills SHALL NOT present `python -m houmao.agents.mailbox_runtime_support resolve-live` as part of the ordinary mailbox operation workflow.

#### Scenario: Unified ordinary-mailbox skill obtains the current endpoint from prompt context when available
- **WHEN** an agent follows the runtime-owned unified ordinary-mailbox skill for shared mailbox work
- **AND WHEN** the current prompt or recent mailbox context already provides the exact current gateway base URL
- **THEN** the skill uses that context-provided base URL as the endpoint prefix for `/v1/mail/*`
- **AND THEN** the agent does not need to rerun manager-based discovery first

#### Scenario: Unified ordinary-mailbox skill falls back to `houmao-mgr agents mail resolve-live`
- **WHEN** an agent follows the runtime-owned unified ordinary-mailbox skill for attached shared mailbox work
- **AND WHEN** the current prompt or recent mailbox context does not provide the exact current gateway base URL
- **THEN** the skill directs the agent to run `houmao-mgr agents mail resolve-live`
- **AND THEN** the agent obtains the exact live mailbox endpoint from the returned `gateway.base_url`

#### Scenario: Unified ordinary-mailbox skill avoids `pixi` and direct Python-module resolver guidance
- **WHEN** an agent follows the projected mailbox skills for ordinary mailbox work
- **THEN** those skills do not instruct the agent to use `pixi run houmao-mgr agents mail resolve-live`
- **AND THEN** they do not instruct the agent to invoke `python -m houmao.agents.mailbox_runtime_support resolve-live` directly
