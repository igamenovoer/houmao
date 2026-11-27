# Spec Delta

## ADDED Requirements

### Requirement: Managed mailbox skills are discoverable through the public agent entrypoint
Mailbox-enabled managed homes SHALL use the installed agent pack for mailbox skill routing. The public `houmao-agent-entrypoint` SHALL delegate to `houmao-shared-routines`. Only that sibling SHALL load its protected mailbox children. Transport-specific guidance SHALL remain inside the ordinary mailbox routine.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

The runtime SHALL NOT project the protected mailbox logical ids as top-level skill directories, SHALL NOT require role-authored mailbox skill content, and SHALL NOT create a parallel hidden mailbox compatibility tree.

#### Scenario: Mailbox-enabled Codex agent receives unified nested surface
- **WHEN** Houmao launches a mailbox-enabled Codex managed agent with default system skills
- **THEN** the Codex skill root contains top-level `houmao-agent-entrypoint`
- **AND THEN** both protected mailbox routines are available beneath the `houmao-shared-routines` sibling
- **AND THEN** neither mailbox routine appears as a top-level peer

#### Scenario: Role-authored skills remain independent
- **WHEN** a managed home includes role-authored skills and the agent pack
- **THEN** mailbox behavior remains owned by the protected Houmao routines
- **AND THEN** installation preserves unrelated role-authored skill paths

#### Scenario: Filesystem mailbox-enabled Claude agent receives the unified mailbox surface
- **WHEN** the runtime starts a Claude session with filesystem mailbox support enabled
- **THEN** the runtime projects the mailbox system skill set for that session from platform-owned templates into the active skill destination
- **AND THEN** Claude native skill lookup finds the public siblings, and the shared sibling loads the selected protected mailbox routine
- **AND THEN** filesystem-specific ordinary mailbox guidance is available through the unified skill rather than through a separate top-level filesystem mailbox skill

#### Scenario: Stalwart mailbox-enabled Claude agent receives the unified mailbox surface
- **WHEN** the runtime starts a Claude session with `stalwart` mailbox support enabled
- **THEN** the runtime projects the mailbox system skill set for that session from platform-owned templates into the active skill destination
- **AND THEN** Claude native skill lookup finds the public siblings, and the shared sibling loads the selected protected mailbox routine
- **AND THEN** Stalwart-specific ordinary mailbox guidance is available through the unified skill rather than through a separate top-level Stalwart mailbox skill

#### Scenario: Codex mailbox-enabled agent receives the unified mailbox surface
- **WHEN** the runtime starts a Codex mailbox-enabled session
- **THEN** the runtime projects the mailbox system skill set for that session from platform-owned templates into the active skill destination
- **AND THEN** Codex native skill lookup finds the public siblings, which route the agent to the selected protected mailbox routine
- **AND THEN** those mailbox system skills are available to the agent without requiring the role or recipe to select or author a mailbox-specific skill manually

#### Scenario: A mailbox-enabled Hermes agent discovers only the public routing siblings
- **WHEN** a mailbox-enabled managed Hermes home receives the agent pack
- **THEN** Hermes native skill lookup can open `houmao-agent-entrypoint` and `houmao-shared-routines`
- **AND THEN** the mailbox routines are available as protected children beneath `houmao-shared-routines`

#### Scenario: Runtime-owned mailbox skills stay separate from role-authored skills
- **WHEN** an agent session includes both role-authored skills and runtime-owned mailbox system skills
- **THEN** runtime-owned mailbox skills remain distinguishable through reserved Houmao-owned skill names and tool-native projected paths
- **AND THEN** the agent can use those mailbox system skills without overriding or depending on role-authored skill content

#### Scenario: Hidden mailbox compatibility mirror is not projected
- **WHEN** the runtime projects mailbox system skills for a mailbox-enabled session
- **THEN** the runtime does not create a parallel hidden `.system/mailbox/...` mailbox skill tree for that session
- **AND THEN** Claude and Codex sessions do not rely on a parallel `skills/mailbox/...` compatibility mirror for ordinary mailbox-skill discovery

### Requirement: Protected mailbox routines handle ordinary mail and notified rounds separately
The agent pack's protected composition SHALL include two distinct mailbox logical routines.

`houmao-process-emails-via-gateway` SHALL own notifier-triggered, bounded Inbox work rounds. Its `process-round` workflow SHALL use prompt-supplied gateway coordinates, perform metadata-first triage, inspect selected messages, finish work and any required replies, follow the binding's authorized completion path, and stop for the next notifier wake-up.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

`houmao-agent-email-comms` SHALL own ordinary discovery, status, list, peek, read, send, post, reply, mark, move, and archive behavior where the selected binding supports each operation. It SHALL prefer a gateway base URL already present in prompt or route context and SHALL use the manager-owned live resolver only when current context lacks that URL. Filesystem and Stalwart guidance SHALL remain internal to this protected routine.

The public agent entrypoint SHALL route to the correct protected routine from operation and notifier context. It SHALL NOT project transport-specific or old compatibility mailbox skills as top-level directories.

#### Scenario: Notified round chooses processing routine
- **WHEN** verified agent context contains a notifier-triggered unread-mail round and gateway URL
- **THEN** the agent entrypoint routes to protected `houmao-process-emails-via-gateway`
- **AND THEN** the round stops after processing the selected work and performing any ordinary archive the binding supports

#### Scenario: Ordinary send chooses email-comms routine
- **WHEN** a verified managed agent asks to send or reply outside a notifier round
- **THEN** the agent entrypoint routes to protected `houmao-agent-email-comms`
- **AND THEN** the routine applies the ordinary mailbox discovery and transport guidance

#### Scenario: Top-level mailbox compatibility paths stay absent
- **WHEN** the agent pack is installed
- **THEN** the tool-native skill root does not contain top-level `houmao-process-emails-via-gateway`, `houmao-agent-email-comms`, or transport-specific mailbox compatibility skills

#### Scenario: Claude mailbox-enabled session receives the processing skill and unified ordinary-mailbox skill
- **WHEN** the runtime starts a mailbox-enabled Claude session
- **THEN** it projects the public routing siblings into the active skill destination with both mailbox routines beneath `houmao-shared-routines`
- **AND THEN** Claude can discover the public routing siblings through native skill discovery
- **AND THEN** the runtime does not also project separate top-level gateway, filesystem, or Stalwart ordinary-mailbox skills

#### Scenario: Codex mailbox-enabled session receives the processing skill and unified ordinary-mailbox skill
- **WHEN** the runtime starts a mailbox-enabled Codex session
- **THEN** it projects the public routing siblings into the active skill destination with both mailbox routines beneath `houmao-shared-routines`
- **AND THEN** the agent can discover the public routing siblings through native skill discovery
- **AND THEN** the runtime does not also project separate top-level gateway, filesystem, or Stalwart ordinary-mailbox skills

#### Scenario: The public notifier route delegates to the processing routine
- **WHEN** a mailbox-enabled session has the shared gateway mailbox facade available
- **THEN** the notifier prompt selects `process-emails-via-gateway` through the public entrypoint when the required siblings are installed
- **AND THEN** the verified route delegates to the protected `houmao-process-emails-via-gateway` routine through the shared sibling
- **AND THEN** ordinary mailbox actions within that round may rely on `houmao-agent-email-comms` as supporting material

#### Scenario: Unified ordinary-mailbox skill remains the operational reference
- **WHEN** the shared sibling loads the protected `houmao-agent-email-comms` routine for ordinary mail
- **THEN** that entry document points the agent at internal action-specific or transport-specific subdocuments for resolver and mailbox-operation behavior
- **AND THEN** the notifier-round route continues to delegate to the separate processing routine
- **AND THEN** it does not require a separate installed top-level transport skill for filesystem or Stalwart guidance

## MODIFIED Requirements

### Requirement: Runtime mailbox prompts enter through the managed-agent entrypoint
Runtime-owned notifier, mailbox, and gateway prompts that require Houmao system-skill behavior SHALL invoke or direct the managed agent to `houmao-agent-entrypoint` with the mailbox operation and notifier context.

The public entrypoint SHALL verify managed self identity before routing to the protected `houmao-process-emails-via-gateway` or `houmao-agent-email-comms` routine. Runtime prompts SHALL NOT instruct the agent to invoke either protected logical id as a top-level skill.

#### Scenario: Notifier starts an unread-mail round
- **WHEN** the runtime wakes a managed agent for gateway-notified unread mail
- **THEN** the prompt enters through `houmao-agent-entrypoint` with the current gateway context
- **AND THEN** the entrypoint verifies self identity before routing to the protected processing routine

#### Scenario: Hermes uses the public route for ordinary mail

- **WHEN** Houmao generates ordinary mailbox guidance for a managed Hermes session with both public siblings
- **THEN** the guidance selects `agent-email-comms` on `houmao-agent-entrypoint` through the native skill loader
- **AND THEN** the verified route delegates through `houmao-shared-routines` to the ordinary mailbox routine

### Requirement: Generated mailbox prompts require both static routing siblings
Mailbox command prompts and gateway notifier prompts SHALL use the tool-native invocation of `houmao-agent-entrypoint` only when the target tool-native skill root contains both `houmao-agent-entrypoint/SKILL.md` and `houmao-shared-routines/SKILL.md`.

Presence of only one sibling SHALL be treated as an incomplete skill route. The generated prompt SHALL use the maintained API fallback and SHALL NOT claim that entrypoint routing is installed.

#### Scenario: Agent entrypoint exists without shared routines
- **WHEN** prompt generation finds `houmao-agent-entrypoint/SKILL.md` but not `houmao-shared-routines/SKILL.md`
- **THEN** the prompt uses the API-oriented fallback
- **AND THEN** it does not instruct the agent to invoke a missing shared mailbox route

#### Scenario: Both static siblings exist
- **WHEN** prompt generation finds both required standalone entrypoints
- **THEN** the prompt invokes `houmao-agent-entrypoint` through the appropriate native loader with the selected mailbox route
- **AND THEN** it describes delegation to the shared-routines sibling rather than protected traversal below the entrypoint

## REMOVED Requirements

### Requirement: Runtime-owned mailbox system skills are available to launched agents through a unified Houmao mailbox surface

**Reason**: The older scenarios prescribed direct child discovery and a retired Gemini projection.

**Migration**: Discover the installed public siblings through the provider's native skill loader and use the appropriate mailbox route.

### Requirement: Runtime-owned mailbox skill projection pairs a unified ordinary mailbox skill with the separate processing workflow

**Reason**: The older scenarios treated protected mailbox children as independent native entrypoints and included unsupported Gemini projection.

**Migration**: Use the public agent entrypoint. Its shared sibling loads the selected protected routine.
