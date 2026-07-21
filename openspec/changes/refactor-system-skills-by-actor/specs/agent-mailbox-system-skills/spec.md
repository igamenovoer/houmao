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
