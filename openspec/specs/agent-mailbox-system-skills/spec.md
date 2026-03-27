## Purpose
Define the runtime-owned mailbox system-skill contract, including env bindings, projection behavior, and shared-mailbox guidance across mailbox transports.
## Requirements
### Requirement: Runtime-owned mailbox system skills are available to launched agents
The system SHALL provide implemented mailbox access to agents through runtime-owned mailbox system skills projected from platform-owned templates rather than requiring role-authored mailbox skill content.

These mailbox system skills SHALL be projected into mailbox-enabled sessions in a discoverable non-hidden mailbox subtree under the active skill destination using the same active skill-destination contract as other projected skills.

For the current tool adapters whose active skill destination is `skills`, the mailbox system skill surface SHALL be `skills/mailbox/...`.

The projected mailbox skill set MAY vary by the selected mailbox transport, including filesystem-backed and real-mail-backed transports.

#### Scenario: Filesystem mailbox-enabled agent receives projected mailbox system skills
- **WHEN** the runtime starts an agent session with filesystem mailbox support enabled
- **THEN** the runtime projects the mailbox system skill set for that session from platform-owned templates into the active skill destination
- **AND THEN** the filesystem mailbox skill is available through the discoverable mailbox subtree rather than through hidden `.system` entries
- **AND THEN** those mailbox system skills are available to the agent without requiring the role or recipe to select or author a mailbox-specific skill manually

#### Scenario: Stalwart mailbox-enabled agent receives projected mailbox system skills
- **WHEN** the runtime starts an agent session with `stalwart` mailbox support enabled
- **THEN** the runtime projects the mailbox system skill set for that session from platform-owned templates into the active skill destination
- **AND THEN** the Stalwart mailbox skill is available through the discoverable mailbox subtree rather than through hidden `.system` entries
- **AND THEN** those mailbox system skills are available to the agent without requiring the role or recipe to select or author a mailbox-specific skill manually

#### Scenario: Runtime-owned mailbox skills stay separate from role-authored skills
- **WHEN** an agent session includes both role-authored skills and runtime-owned mailbox system skills
- **THEN** the mailbox system skills use a reserved runtime-owned mailbox subtree under the active skill destination
- **AND THEN** the agent can use those mailbox system skills without overriding or depending on role-authored skill content

#### Scenario: Hidden mailbox compatibility mirror is not projected
- **WHEN** the runtime projects mailbox system skills for a mailbox-enabled session
- **THEN** the runtime does not create a parallel `skills/.system/mailbox/...` mailbox skill tree for that session
- **AND THEN** ordinary mailbox-skill discovery and prompting depend only on the visible `skills/mailbox/...` mailbox subtree

### Requirement: Mailbox system skills use a stable env-var binding contract
The system SHALL require runtime-owned mailbox system skills to resolve mailbox bindings through runtime-managed env vars rather than through literal filesystem paths, URLs, or mailbox addresses embedded in projected skill text.

At minimum, the runtime SHALL provide the following common mailbox binding env vars for started sessions:

- `AGENTSYS_MAILBOX_TRANSPORT`,
- `AGENTSYS_MAILBOX_PRINCIPAL_ID`,
- `AGENTSYS_MAILBOX_ADDRESS`,
- `AGENTSYS_MAILBOX_BINDINGS_VERSION`.

The runtime SHALL additionally provide transport-specific mailbox binding env vars required by the selected transport, and it MAY expose live gateway discovery bindings through the existing gateway env contract when a live gateway is attached.

Filesystem-specific mailbox binding env vars SHALL continue to use the `AGENTSYS_MAILBOX_FS_` prefix.

Email-backed mailbox binding env vars for real-mail transports SHALL use the `AGENTSYS_MAILBOX_EMAIL_` prefix.

For filesystem mailbox sessions, those runtime-managed bindings SHALL include at minimum:

- `AGENTSYS_MAILBOX_FS_ROOT` for the shared mailbox root,
- `AGENTSYS_MAILBOX_FS_SQLITE_PATH` for the shared mailbox-root catalog SQLite path,
- `AGENTSYS_MAILBOX_FS_INBOX_DIR` for the resolved mailbox inbox directory,
- `AGENTSYS_MAILBOX_FS_MAILBOX_DIR` for the resolved mailbox directory,
- `AGENTSYS_MAILBOX_FS_LOCAL_SQLITE_PATH` for the mailbox-local SQLite path.

For `stalwart` mailbox sessions, those runtime-managed bindings SHALL include at minimum:

- a JMAP endpoint or JMAP base URL for mailbox operations,
- the mailbox login identity needed for mailbox access,
- a runtime-managed authentication reference suitable for mailbox access without persisting secrets in the manifest payload.

That runtime-managed authentication reference SHALL be secret-free in the persisted mailbox binding and MAY resolve to a session-owned credential file path in v1.

#### Scenario: Filesystem mailbox skill resolves filesystem bindings from env vars
- **WHEN** the runtime starts an agent session with the filesystem mailbox transport
- **THEN** the projected mailbox system skill refers to the filesystem mailbox through runtime-managed env vars
- **AND THEN** the started session environment includes the filesystem mailbox binding env vars needed by that skill, including the transport kind, the shared mailbox locations, and the resolved mailbox-local state locations
- **AND THEN** those filesystem-specific binding env vars use the `AGENTSYS_MAILBOX_FS_` prefix
- **AND THEN** the filesystem mailbox content root is provided through `AGENTSYS_MAILBOX_FS_ROOT` rather than being inferred from a fixed run-directory location

#### Scenario: Stalwart mailbox skill resolves real-mail bindings from env vars
- **WHEN** the runtime starts an agent session with the `stalwart` mailbox transport
- **THEN** the projected mailbox system skill refers to that mailbox through runtime-managed email transport env vars
- **AND THEN** those transport-specific binding env vars use the `AGENTSYS_MAILBOX_EMAIL_` prefix instead of inheriting filesystem path bindings

#### Scenario: Filesystem mailbox skill receives explicit local mailbox-state bindings
- **WHEN** the runtime starts or refreshes a filesystem mailbox-enabled session
- **THEN** the runtime publishes explicit env bindings for the resolved mailbox directory and mailbox-local SQLite path
- **AND THEN** the agent does not need to reconstruct mailbox-local state paths heuristically from the inbox path

#### Scenario: Real-mail binding prefix stays distinct from filesystem bindings
- **WHEN** the runtime publishes email-backed mailbox bindings for a real-mail transport
- **THEN** those transport-specific binding env vars use the `AGENTSYS_MAILBOX_EMAIL_` prefix
- **AND THEN** they remain distinct from the implemented filesystem mailbox binding env vars

### Requirement: Filesystem mailbox binding env vars are refreshable on demand
The system SHALL support on-demand refresh of runtime-managed filesystem mailbox binding env vars for active agent sessions without requiring regeneration of the mailbox system skill templates themselves.

Refreshed mailbox bindings SHALL apply to subsequent runtime-controlled work for that session.

#### Scenario: Filesystem mailbox binding refresh updates subsequent work
- **WHEN** the runtime changes the effective filesystem mailbox binding for an active session
- **THEN** the runtime refreshes the mailbox binding env vars for that session
- **AND THEN** subsequent mailbox-related work in that session observes the refreshed filesystem mailbox bindings without requiring a new mailbox system skill template

### Requirement: Tmux-backed mailbox system skills resolve current mailbox bindings through a runtime-owned live resolver
For tmux-backed managed sessions, runtime-owned mailbox system skills and runtime-owned mailbox prompts SHALL resolve current mailbox bindings through a runtime-owned live mailbox binding resolver rather than relying only on the provider process's inherited mailbox env snapshot.

That live resolver SHALL:

- use the owning tmux session as the live mailbox binding source for active tmux-contained sessions,
- read only the targeted common and transport-specific mailbox binding keys needed for mailbox work,
- surface the current `AGENTSYS_MAILBOX_BINDINGS_VERSION` for mailbox refresh detection,
- avoid requiring the agent to parse raw manifest JSON or enumerate unrelated tmux env vars manually.

The existing mailbox env naming contract remains unchanged, but for tmux-backed sessions those bindings SHALL be treated as live mailbox projection data resolved through the runtime-owned resolver rather than as launch-time process env that is assumed immutable.

#### Scenario: Filesystem mailbox skill observes late-registered binding without provider relaunch
- **WHEN** a tmux-backed filesystem mailbox session receives a mailbox task after late registration updated the owning tmux session environment
- **THEN** the projected mailbox system skill resolves the current mailbox binding through the runtime-owned live resolver
- **AND THEN** the skill observes the refreshed filesystem mailbox root, mailbox directory, and mailbox-local SQLite path without requiring provider relaunch solely to refresh inherited process env
- **AND THEN** the agent does not need to reconstruct mailbox paths heuristically from stale launch-time bindings

#### Scenario: Subsequent mailbox work re-resolves after bindings-version change
- **WHEN** a tmux-backed managed session's mailbox binding changes and `AGENTSYS_MAILBOX_BINDINGS_VERSION` advances in the owning tmux session environment
- **THEN** the next mailbox-related action resolves mailbox bindings through the runtime-owned live resolver again
- **AND THEN** the mailbox skill discards cached mailbox assumptions tied to the previous bindings version

#### Scenario: Stalwart direct fallback uses the live resolver rather than stale process env
- **WHEN** a tmux-backed `stalwart` mailbox session performs direct mailbox work without a live gateway mailbox facade
- **THEN** the projected mailbox system skill resolves the current `AGENTSYS_MAILBOX_EMAIL_*` binding set through the runtime-owned live resolver
- **AND THEN** the skill uses the current session-local credential file pointer from that live binding set rather than assuming the provider process inherited a still-valid credential path at launch

### Requirement: Runtime-owned mailbox skill guidance keeps tmux integration behind the runtime-owned helper boundary
Projected mailbox system skills for tmux-backed sessions SHALL keep raw tmux integration details behind the runtime-owned live mailbox binding resolver.

The skill guidance SHALL NOT require the agent to:

- list all tmux session environment variables,
- guess which tmux session to inspect,
- parse raw `show-environment` output structure,
- or parse mailbox binding state directly from the session manifest when the runtime-owned resolver is available.

#### Scenario: Filesystem mailbox skill does not ask the agent to scrape tmux state ad hoc
- **WHEN** a tmux-backed filesystem mailbox session uses the projected mailbox system skill for mailbox work
- **THEN** that skill points the agent at the runtime-owned live mailbox binding resolver
- **AND THEN** the skill does not instruct the agent to enumerate unrelated tmux environment state or manually parse raw tmux command output

### Requirement: Runtime-owned mailbox commands rely on projected mailbox system skills
The system SHALL allow runtime-owned mailbox command surfaces to rely on projected, transport-specific mailbox system skills plus runtime-managed mailbox bindings, without requiring mailbox-specific instructions to be authored in the role or recipe.

When a live gateway exposes the shared `/v1/mail/*` mailbox surface for the session, the projected mailbox system skill SHALL prefer that gateway surface for the shared mailbox operations in this change: `check`, `send`, `reply`, and explicit read-state update after successful processing.

When no live gateway mailbox facade is available, the projected mailbox system skill MAY fall back to direct transport-specific mailbox behavior appropriate to the selected transport.

#### Scenario: Gateway-aware mailbox skill uses the shared gateway mail surface
- **WHEN** a mailbox-enabled session has a live attached gateway that exposes `/v1/mail/*`
- **AND WHEN** the runtime delivers a mailbox-operation prompt such as `check`, `send`, or `reply`
- **THEN** the projected mailbox system skill prefers the gateway mailbox surface for that shared mailbox operation
- **AND THEN** the agent does not need to reason about filesystem versus Stalwart transport details to perform that shared operation

#### Scenario: Filesystem mailbox skill falls back to direct filesystem behavior when no gateway is attached
- **WHEN** the runtime delivers a mailbox-operation prompt to a filesystem mailbox-enabled session with no live gateway mailbox surface
- **THEN** the launched agent can satisfy that request through the projected filesystem mailbox system skills and filesystem mailbox env bindings
- **AND THEN** that mailbox operation does not depend on mailbox-specific behavior being restated inside the role or recipe

#### Scenario: Stalwart mailbox skill falls back to direct real-mail behavior when no gateway is attached
- **WHEN** the runtime delivers a mailbox-operation prompt to a `stalwart` mailbox-enabled session with no live gateway mailbox surface
- **THEN** the launched agent can satisfy that request through the projected Stalwart mailbox system skills and runtime-managed email mailbox bindings
- **AND THEN** that mailbox operation does not require the role or recipe to define transport-specific Stalwart instructions

### Requirement: Projected mailbox system skills keep routine attached-session actions on the shared gateway facade
When a live loopback gateway exposes the shared `/v1/mail/*` mailbox surface for a mailbox-enabled session, the projected mailbox system skills SHALL treat that shared gateway facade as the default routine action surface for ordinary mailbox work.

Projected mailbox system skills for both filesystem and Stalwart transports SHALL present that default structurally: a gateway-first routine-actions section first, followed by transport-local fallback guidance for no-gateway or transport-specific work.

For this change, ordinary mailbox work includes:

- checking unread mail,
- sending one new message,
- replying to one existing message, and
- marking one processed message read.

For attached filesystem sessions, the projected mailbox system skills SHALL present direct managed-script flows such as `deliver_message.py` or `update_mailbox_state.py` as fallback guidance for no-gateway sessions or transport-specific work outside the shared facade rather than as the first-choice path for ordinary attached-session turns.

For attached Stalwart sessions, the projected mailbox system skills SHALL present direct env-backed transport access as fallback guidance rather than as the first-choice path for ordinary attached-session turns.

#### Scenario: Attached filesystem session replies without reconstructing transport-local delivery
- **WHEN** an attached filesystem mailbox session needs to perform one routine reply in a bounded turn
- **THEN** the projected mailbox system skill directs the agent toward the shared gateway mailbox operations for `check`, `reply`, and read-state update
- **AND THEN** the agent does not need to reconstruct `deliver_message.py` payload fields or raw threading metadata to complete that routine action

#### Scenario: Filesystem session without gateway still has a direct fallback path
- **WHEN** a filesystem mailbox-enabled session has no live shared gateway mailbox facade
- **THEN** the projected mailbox system skill may fall back to direct managed-script guidance for the mailbox action
- **AND THEN** that fallback remains transport-specific rather than being restated inside the role or recipe

### Requirement: Filesystem mailbox system skills instruct agents to consult shared mailbox rules first
The system SHALL require the projected filesystem mailbox system skill to instruct agents to inspect the shared mailbox `rules/` directory under the effective filesystem mailbox root before interacting with shared mailbox state.

This requirement is instructional rather than hard-enforced in v1.

#### Scenario: Filesystem mailbox skill points agent to mailbox-local rules
- **WHEN** an agent uses the projected filesystem mailbox system skill for mailbox reads or writes
- **THEN** that skill instructs the agent to inspect the shared mailbox `rules/` directory before proceeding with mailbox interaction
- **AND THEN** the agent treats those mailbox-local rules as more specific guidance for that shared mailbox when they refine the generic filesystem mailbox skill

### Requirement: Filesystem mailbox system skills direct sensitive operations to shared scripts
The system SHALL require the projected filesystem mailbox system skill to direct agents to use shared helper scripts from `rules/scripts/` for mailbox operations that touch shared-root SQLite, mailbox-local SQLite, or `locks/`.

#### Scenario: Filesystem mailbox skill points sensitive work to rules/scripts
- **WHEN** an agent uses the projected filesystem mailbox system skill for a mailbox operation that touches shared-root `index.sqlite`, mailbox-local `mailbox.sqlite`, or `locks/`
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

### Requirement: Filesystem mailbox system skills instruct agents to mark processed mail read explicitly
The system SHALL require the projected filesystem mailbox system skill to distinguish between discovering unread mail and marking a message read after processing.

That skill SHALL instruct agents to mark a message read only after the agent has actually processed that message successfully through the mailbox-managed helper boundary.

The skill SHALL NOT instruct agents to mark a message read merely because unread mail was detected or because a gateway-generated reminder prompt mentioned the message.

#### Scenario: Agent marks processed message read through the managed helper boundary
- **WHEN** an agent finishes processing an unread mailbox message successfully
- **THEN** the projected filesystem mailbox system skill instructs the agent to update mailbox read state explicitly through the managed mailbox helper boundary
- **AND THEN** the agent does not need gateway participation to complete that read-state update

#### Scenario: Reminder prompt does not imply read-state mutation
- **WHEN** the agent receives a gateway-owned reminder that unread mail exists
- **THEN** the projected filesystem mailbox system skill does not treat that reminder itself as a read-state change
- **AND THEN** the unread message remains unread until the agent explicitly marks it read after processing
