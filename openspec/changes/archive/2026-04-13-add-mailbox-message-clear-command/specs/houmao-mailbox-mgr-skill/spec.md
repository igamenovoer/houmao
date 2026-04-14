## MODIFIED Requirements

### Requirement: Houmao provides a packaged `houmao-mailbox-mgr` system skill
The system SHALL package a Houmao-owned system skill named `houmao-mailbox-mgr` under the maintained system-skill asset root.

That skill SHALL instruct agents and operators to handle mailbox-administration work through these maintained command surfaces:

- `houmao-mgr mailbox init|status|register|unregister|repair|cleanup|clear-messages`
- `houmao-mgr mailbox accounts list|get`
- `houmao-mgr mailbox messages list|get`
- `houmao-mgr project mailbox init|status|register|unregister|repair|cleanup|clear-messages`
- `houmao-mgr project mailbox accounts list|get`
- `houmao-mgr project mailbox messages list|get`
- `houmao-mgr agents mailbox status|register|unregister`

The top-level `SKILL.md` for that packaged skill SHALL serve as an index/router that selects local action-specific documents rather than flattening the entire workflow into one page.

That packaged skill SHALL treat these surfaces as explicitly out of scope:

- `houmao-mgr agents mail ...`
- shared gateway `/v1/mail/*` operations
- `houmao-mgr agents gateway mail-notifier ...`
- direct gateway `/v1/mail-notifier` or `/v1/wakeups`
- ad hoc filesystem editing inside mailbox roots

#### Scenario: Installed skill points the caller at maintained mailbox-admin surfaces
- **WHEN** an agent or operator opens the installed `houmao-mailbox-mgr` skill
- **THEN** the skill directs the caller to the maintained mailbox-root, project-mailbox, and late agent-binding command surfaces
- **AND THEN** it does not redirect the caller to unrelated actor-scoped mail, gateway reminder, or direct filesystem mutation paths

#### Scenario: Installed skill routes through action-specific local guidance
- **WHEN** an agent reads the installed `houmao-mailbox-mgr` skill
- **THEN** the top-level `SKILL.md` acts as an index/router for mailbox-admin actions
- **AND THEN** the detailed workflow lives in local action-specific documents rather than one flattened entry page

## ADDED Requirements

### Requirement: `houmao-mailbox-mgr` routes delivered-message reset work to clear-messages
The packaged `houmao-mailbox-mgr` skill SHALL route requests to remove all delivered messages while preserving mailbox accounts to the maintained `clear-messages` command for the selected mailbox scope.

When the task targets an arbitrary filesystem mailbox root, the skill SHALL use `houmao-mgr mailbox clear-messages`.

When the task targets the selected project overlay mailbox root, the skill SHALL use `houmao-mgr project mailbox clear-messages`.

The skill SHALL distinguish `clear-messages` from `cleanup`: `cleanup` remains for inactive or stashed registration cleanup, while `clear-messages` is the destructive delivered-message reset.

The skill SHALL NOT instruct callers to hand-edit mailbox-root files for message clearing when the maintained `clear-messages` command covers the request.

#### Scenario: Skill routes project-local message reset to project clear-messages
- **WHEN** the user asks to remove all emails from the active project mailbox root while preserving accounts
- **THEN** the skill directs the caller to `houmao-mgr project mailbox clear-messages`
- **AND THEN** it does not route the request to `project mailbox cleanup` or account unregister commands

#### Scenario: Skill routes arbitrary-root message reset to generic clear-messages
- **WHEN** the user asks to remove all emails from an explicit filesystem mailbox root while preserving accounts
- **THEN** the skill directs the caller to `houmao-mgr mailbox clear-messages --mailbox-root <path>`
- **AND THEN** it does not recommend ad hoc deletion inside the mailbox root
