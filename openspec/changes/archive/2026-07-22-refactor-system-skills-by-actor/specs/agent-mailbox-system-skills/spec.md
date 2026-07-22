## ADDED Requirements

### Requirement: Runtime mailbox prompts enter through the managed-agent entrypoint
Runtime-owned notifier, mailbox, and gateway prompts that require Houmao system-skill behavior SHALL invoke or direct the managed agent to `houmao-agent-entrypoint` with the mailbox operation and notifier context.

The public entrypoint SHALL verify managed self identity before routing to the protected `houmao-process-emails-via-gateway` or `houmao-agent-email-comms` routine. Runtime prompts SHALL NOT instruct the agent to invoke either protected logical id as a top-level skill.

#### Scenario: Notifier starts an unread-mail round
- **WHEN** the runtime wakes a managed agent for gateway-notified unread mail
- **THEN** the prompt enters through `houmao-agent-entrypoint` with the current gateway context
- **AND THEN** the entrypoint verifies self identity before routing to the protected processing routine

## MODIFIED Requirements

### Requirement: Joined-session adoption installs Houmao-owned mailbox skills by default
When `houmao-mgr agents join` adopts a mailbox-enabled session with default system-skill installation enabled, the join workflow SHALL install the complete agent pack into the authoritative adopted tool home.

The installation SHALL use the shared pack installer, copy projection, and a pack receipt. The agent entrypoint's protected composition SHALL include the notifier-round processing routine and ordinary mailbox routine, while unrelated user-authored skills remain untouched.

If the agent pack cannot be staged, validated, or committed safely, join SHALL fail before publishing a managed session whose runtime prompts assume the entrypoint exists. An explicit system-skill opt-out MAY continue without the pack, but later prompts SHALL NOT assume mailbox routines are available.

#### Scenario: Joined mailbox session receives agent pack
- **WHEN** an operator adopts a mailbox-enabled session without opting out of system skills
- **THEN** join installs `houmao-agent-entrypoint` into the adopted home
- **AND THEN** its protected composition contains the ordinary mailbox and notified-round routines

#### Scenario: Joined installation fails closed
- **WHEN** the agent pack cannot be installed safely into the adopted home
- **THEN** join fails before publishing the managed session
- **AND THEN** it reports the pack installation failure without partially projecting mailbox routines

#### Scenario: Join opt-out removes the prompt assumption
- **WHEN** the operator explicitly opts out of default system-skill installation
- **THEN** join may continue without the agent pack
- **AND THEN** later mailbox prompts do not claim that the entrypoint or protected mailbox routines are installed

#### Scenario: Joined mailbox-enabled session receives the managed-join mailbox skill set by default
- **WHEN** an operator uses `houmao-mgr agents join` to adopt a mailbox-enabled session without opting out of Houmao skill installation
- **THEN** the join workflow installs the current Houmao-owned system-skill selection resolved from the managed-join auto-install set list into the adopted tool home
- **AND THEN** that resolved selection includes the current Houmao-owned mailbox skills needed for later runtime-owned mailbox prompts

#### Scenario: Join preserves unrelated user-authored skills
- **WHEN** `houmao-mgr agents join` installs the current Houmao-owned system-skill selection resolved from the managed-join auto-install set list into an adopted tool home
- **THEN** it writes only to reserved Houmao-owned skill paths for the current skill set
- **AND THEN** it does not delete or overwrite unrelated user-authored non-Houmao skill directories in that same skill destination

#### Scenario: Join fails closed when required default Houmao-owned skill installation cannot complete
- **WHEN** `houmao-mgr agents join` is using default Houmao-owned current-skill installation
- **AND WHEN** the adopted tool home or skill destination cannot be resolved or updated safely
- **THEN** the join command fails explicitly
- **AND THEN** it does not publish a managed session whose later runtime prompts would assume missing Houmao-owned mailbox skills

#### Scenario: Explicit join opt-out disables the installed-mailbox-skill assumption
- **WHEN** an operator uses the explicit opt-out for default Houmao-owned skill installation during `houmao-mgr agents join`
- **THEN** the join workflow may continue without projecting the current Houmao-owned mailbox skills
- **AND THEN** later runtime-owned mailbox prompts for that joined session do not assume the current Houmao-owned mailbox skills are installed

### Requirement: Runtime-owned mailbox system skills are available to launched agents through a unified Houmao mailbox surface
Mailbox-enabled managed homes SHALL receive the agent pack rather than separate top-level mailbox skills.

The one public mailbox-capable surface SHALL be `houmao-agent-entrypoint`. Its protected `houmao-shared-routines` composition SHALL include `houmao-agent-email-comms` for ordinary mailbox work and `houmao-process-emails-via-gateway` for notified unread-mail rounds. Transport-specific ordinary guidance SHALL remain private to the ordinary mailbox routine.

The runtime SHALL NOT project the protected mailbox logical ids as top-level skill directories, SHALL NOT require role-authored mailbox skill content, and SHALL NOT create a parallel hidden mailbox compatibility tree.

#### Scenario: Mailbox-enabled Codex agent receives unified nested surface
- **WHEN** Houmao launches a mailbox-enabled Codex managed agent with default system skills
- **THEN** the Codex skill root contains top-level `houmao-agent-entrypoint`
- **AND THEN** both protected mailbox routines are available beneath its shared-routines mount
- **AND THEN** neither mailbox routine appears as a top-level peer

#### Scenario: Role-authored skills remain independent
- **WHEN** a managed home includes role-authored skills and the agent pack
- **THEN** mailbox behavior remains owned by the protected Houmao routines
- **AND THEN** installation preserves unrelated role-authored skill paths

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
The agent pack's protected composition SHALL include two distinct mailbox logical routines.

`houmao-process-emails-via-gateway` SHALL own notifier-triggered, bounded unread-mail rounds, assume the notifier supplies the exact gateway base URL, perform metadata-first triage, inspect selected messages, complete work, archive successfully processed mail, and stop for the next notifier wake-up.

`houmao-agent-email-comms` SHALL own ordinary discovery, status, list, peek, read, send, post, reply, mark, move, and archive behavior. It SHALL prefer a gateway base URL already present in prompt or route context and SHALL use the manager-owned live resolver only when current context lacks that URL. Filesystem and Stalwart guidance SHALL remain internal to this protected routine.

The public agent entrypoint SHALL route to the correct protected routine from operation and notifier context. It SHALL NOT project transport-specific or old compatibility mailbox skills as top-level directories.

#### Scenario: Notified round chooses processing routine
- **WHEN** verified agent context contains a notifier-triggered unread-mail round and gateway URL
- **THEN** the agent entrypoint routes to protected `houmao-process-emails-via-gateway`
- **AND THEN** the round stops after processing and archiving the selected successful work

#### Scenario: Ordinary send chooses email-comms routine
- **WHEN** a verified managed agent asks to send or reply outside a notifier round
- **THEN** the agent entrypoint routes to protected `houmao-agent-email-comms`
- **AND THEN** the routine applies the ordinary mailbox discovery and transport guidance

#### Scenario: Top-level mailbox compatibility paths stay absent
- **WHEN** the agent pack is installed
- **THEN** the tool-native skill root does not contain top-level `houmao-process-emails-via-gateway`, `houmao-agent-email-comms`, or transport-specific mailbox compatibility skills

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
