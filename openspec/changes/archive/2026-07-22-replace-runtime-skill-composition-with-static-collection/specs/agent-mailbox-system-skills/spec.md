## ADDED Requirements

### Requirement: Generated mailbox prompts require both static routing siblings
Mailbox command prompts and gateway notifier prompts SHALL use the `$houmao-agent-entrypoint` route only when the target tool-native skill root contains both `houmao-agent-entrypoint/SKILL.md` and `houmao-shared-routines/SKILL.md`.

Presence of only one sibling SHALL be treated as an incomplete skill route. The generated prompt SHALL use the maintained API fallback and SHALL NOT claim that entrypoint routing is installed.

#### Scenario: Agent entrypoint exists without shared routines
- **WHEN** prompt generation finds `houmao-agent-entrypoint/SKILL.md` but not `houmao-shared-routines/SKILL.md`
- **THEN** the prompt uses the API-oriented fallback
- **AND THEN** it does not instruct the agent to invoke a missing shared mailbox route

#### Scenario: Both static siblings exist
- **WHEN** prompt generation finds both required standalone entrypoints
- **THEN** the prompt invokes `$houmao-agent-entrypoint` with the appropriate mailbox route
- **AND THEN** it describes delegation to the shared-routines sibling rather than protected traversal below the entrypoint

### Requirement: Static shared routines preserve distinct mailbox owners
The static `houmao-shared-routines` skill SHALL own separate parent-scoped children for ordinary email communication and notifier-driven gateway email rounds.

`houmao-agent-email-comms` SHALL preserve ordinary resolver, status, list, peek, read, send, post, reply, mark, move, archive, and transport fallback behavior. `houmao-process-emails-via-gateway` SHALL preserve one prompt-bootstrapped, metadata-first, stop-after-round workflow.

#### Scenario: Verified agent receives notifier prompt
- **WHEN** the agent entrypoint receives a notifier-driven round with the exact gateway base URL
- **THEN** it delegates through static shared routines to `houmao-process-emails-via-gateway`
- **AND THEN** the selected child stops after the bounded round

#### Scenario: Verified agent sends ordinary mail
- **WHEN** the agent entrypoint receives an ordinary send or reply request
- **THEN** it delegates through static shared routines to `houmao-agent-email-comms`
- **AND THEN** it does not use the notifier-round child

### Requirement: Managed mailbox installation uses top-level static siblings
A default mailbox-capable managed home SHALL receive the complete agent pack as four top-level static skill roots. Mailbox children SHALL remain parent-scoped beneath `houmao-shared-routines` and SHALL NOT be copied beneath `houmao-agent-entrypoint`.

#### Scenario: Codex managed home is prepared for mailbox work
- **WHEN** Houmao installs default system skills for a mailbox-capable Codex agent
- **THEN** `houmao-agent-entrypoint` and `houmao-shared-routines` are top-level siblings
- **AND THEN** ordinary and notifier mailbox children exist only inside shared routines
