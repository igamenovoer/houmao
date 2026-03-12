## Purpose
Define the runtime-owned mailbox system-skill contract, including env bindings, projection behavior, and shared-mailbox guidance for filesystem mailbox sessions.

## Requirements
### Requirement: Runtime-owned filesystem mailbox system skills are available to launched agents
The system SHALL provide implemented mailbox access to agents through runtime-owned filesystem mailbox skills projected from platform-owned templates rather than requiring role-authored mailbox skill content.

These filesystem mailbox system skills SHALL be projected into mailbox-enabled sessions in a reserved runtime-owned skill namespace using the same active skill-destination contract as other projected skills.

#### Scenario: Mailbox-enabled agent receives projected mailbox system skills
- **WHEN** the runtime starts an agent session with filesystem mailbox support enabled
- **THEN** the runtime projects the mailbox system skill set for that session from platform-owned templates into the active skill destination
- **AND THEN** those mailbox system skills are available to the agent without requiring the role or recipe to select or author a mailbox-specific skill manually

#### Scenario: Runtime-owned mailbox skills stay separate from role-authored skills
- **WHEN** an agent session includes both role-authored skills and runtime-owned mailbox system skills
- **THEN** the mailbox system skills use the reserved runtime-owned skill namespace
- **AND THEN** the agent can use those mailbox system skills without overriding or depending on role-authored skill content

### Requirement: Mailbox system skills use a stable env-var binding contract
The system SHALL require runtime-owned mailbox system skills to resolve mailbox bindings through runtime-managed env vars rather than through literal paths, URLs, or mailbox addresses embedded in the projected skill text.

At minimum, the runtime SHALL provide the following common mailbox binding env vars for started sessions:

- `AGENTSYS_MAILBOX_TRANSPORT`
- `AGENTSYS_MAILBOX_PRINCIPAL_ID`
- `AGENTSYS_MAILBOX_ADDRESS`
- `AGENTSYS_MAILBOX_BINDINGS_VERSION`

The runtime SHALL additionally provide filesystem-specific mailbox binding env vars required by the implemented filesystem transport.

Filesystem-specific mailbox binding env vars SHALL use the `AGENTSYS_MAILBOX_FS_` prefix.

Reserved future mail-system-compatible mailbox binding env vars SHALL use the `AGENTSYS_MAILBOX_EMAIL_` prefix when a true-email adapter is added in a follow-up change.

#### Scenario: Filesystem mailbox skill resolves bindings from env vars
- **WHEN** the runtime starts an agent session with the filesystem mailbox transport
- **THEN** the projected mailbox system skill refers to the filesystem mailbox through runtime-managed env vars
- **AND THEN** the started session environment includes the filesystem mailbox binding env vars needed by that skill, including the transport kind and filesystem mailbox locations
- **AND THEN** those filesystem-specific binding env vars use the `AGENTSYS_MAILBOX_FS_` prefix
- **AND THEN** the filesystem mailbox content root is provided through `AGENTSYS_MAILBOX_FS_ROOT` rather than being inferred from a fixed run-directory location

#### Scenario: Reserved future mail-system prefix stays distinct
- **WHEN** the system documents mailbox bindings for a future true-email-compatible adapter
- **THEN** those future mail-system-compatible binding env vars use the `AGENTSYS_MAILBOX_EMAIL_` prefix
- **AND THEN** they remain distinct from the implemented filesystem mailbox binding env vars

### Requirement: Filesystem mailbox binding env vars are refreshable on demand
The system SHALL support on-demand refresh of runtime-managed filesystem mailbox binding env vars for active agent sessions without requiring regeneration of the mailbox system skill templates themselves.

Refreshed mailbox bindings SHALL apply to subsequent runtime-controlled work for that session.

#### Scenario: Filesystem mailbox binding refresh updates subsequent work
- **WHEN** the runtime changes the effective filesystem mailbox binding for an active session
- **THEN** the runtime refreshes the mailbox binding env vars for that session
- **AND THEN** subsequent mailbox-related work in that session observes the refreshed filesystem mailbox bindings without requiring a new mailbox system skill template

### Requirement: Runtime-owned mailbox commands rely on projected mailbox system skills
The system SHALL allow runtime-owned mailbox command surfaces to rely on the projected mailbox system skills plus runtime-managed mailbox bindings, without requiring mailbox-specific instructions to be authored in the role or recipe.

#### Scenario: Runtime mail request uses projected mailbox system skills
- **WHEN** the runtime delivers a mailbox-operation prompt such as `check`, `send`, or `reply` to a mailbox-enabled session
- **THEN** the launched agent can satisfy that request through the projected runtime-owned mailbox system skills and mailbox env bindings
- **AND THEN** the runtime request can explicitly name the projected mailbox system skill the agent should use while appending mailbox-operation metadata in the same prompt
- **AND THEN** that mailbox operation does not depend on mailbox-specific behavior being restated inside the role or recipe

### Requirement: Filesystem mailbox system skills instruct agents to consult shared mailbox rules first
The system SHALL require the projected filesystem mailbox system skill to instruct agents to inspect the shared mailbox `rules/` directory under the effective filesystem mailbox root before interacting with shared mailbox state.

This requirement is instructional rather than hard-enforced in v1.

#### Scenario: Filesystem mailbox skill points agent to mailbox-local rules
- **WHEN** an agent uses the projected filesystem mailbox system skill for mailbox reads or writes
- **THEN** that skill instructs the agent to inspect the shared mailbox `rules/` directory before proceeding with mailbox interaction
- **AND THEN** the agent treats those mailbox-local rules as more specific guidance for that shared mailbox when they refine the generic filesystem mailbox skill

### Requirement: Filesystem mailbox system skills direct sensitive operations to shared scripts
The system SHALL require the projected filesystem mailbox system skill to direct agents to use shared helper scripts from `rules/scripts/` for mailbox operations that touch `index.sqlite` or `locks/`.

#### Scenario: Filesystem mailbox skill points sensitive work to rules/scripts
- **WHEN** an agent uses the projected filesystem mailbox system skill for a mailbox operation that touches `index.sqlite` or `locks/`
- **THEN** that skill instructs the agent to use the corresponding shared helper script from `rules/scripts/`
- **AND THEN** the agent is not instructed to improvise raw SQLite or lock-file manipulation for that sensitive portion of the work

### Requirement: Filesystem mailbox system skills surface Python helper dependencies
The system SHALL require the projected filesystem mailbox system skill to tell agents to inspect `rules/scripts/requirements.txt` before invoking a shared Python helper script from `rules/scripts/`.

#### Scenario: Filesystem mailbox skill points agent to Python helper dependencies
- **WHEN** an agent is about to invoke a Python-based shared helper script from `rules/scripts/`
- **THEN** the projected filesystem mailbox system skill instructs the agent to inspect the shared mailbox `rules/scripts/requirements.txt`
- **AND THEN** the agent can determine which Python dependencies need to be installed or otherwise available before invoking that helper

### Requirement: Filesystem mailbox system skills may suggest optional header helper scripts
The system SHALL allow the projected filesystem mailbox system skill to suggest optional helper scripts from `rules/scripts/` for standardized header insertion or normalization during message composition.

#### Scenario: Filesystem mailbox skill suggests optional header helper
- **WHEN** an agent composes a filesystem mailbox message and the shared mailbox provides a header-helper script under `rules/scripts/`
- **THEN** the projected filesystem mailbox system skill may suggest using that helper script for standardized header insertion or normalization
- **AND THEN** the skill does not require that helper script as a mandatory transport step when the operation does not touch `index.sqlite` or `locks/`
