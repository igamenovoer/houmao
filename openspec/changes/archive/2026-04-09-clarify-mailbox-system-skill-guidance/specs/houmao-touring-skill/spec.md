## ADDED Requirements

### Requirement: `houmao-touring` distinguishes mailbox-root setup from mailbox-account ownership choices
When the packaged `houmao-touring` skill offers project-local mailbox setup, it SHALL describe mailbox-root bootstrap as distinct from mailbox-account creation.

When the user's intended next step is to launch one or more specialist-backed easy instances with ordinary filesystem mailbox identities derived from managed-agent names, the touring skill SHALL explain that per-agent mailbox registration may be owned by the later `project easy instance launch` step rather than by an immediate `project mailbox register` step.

When the user instead wants a standalone shared, team, operator-facing, or otherwise manually named mailbox account that is not being created by an immediate easy-instance launch, the touring skill SHALL describe that as manual mailbox-account administration and SHALL route that work through `houmao-mailbox-mgr`.

The touring skill SHALL NOT present per-agent `project mailbox register` as a mandatory part of the common "initialize project mailbox root, then launch specialist-backed agents" flow.

#### Scenario: Guided mailbox setup for future specialist-backed launch avoids preregistering per-agent accounts
- **WHEN** the touring branch offers project-local mailbox setup
- **AND WHEN** the user is preparing to launch specialist-backed easy instances with ordinary mailbox identities such as `<agent-name>@houmao.localhost`
- **THEN** the touring skill explains that mailbox-root bootstrap and per-agent mailbox registration are separate decisions
- **AND THEN** it does not present `project mailbox register` for those same per-agent addresses as mandatory pre-launch setup

#### Scenario: Guided mailbox setup for a shared mailbox account routes manual registration explicitly
- **WHEN** the touring branch offers project-local mailbox setup
- **AND WHEN** the user wants a shared or manually named mailbox account that is not tied to an immediate specialist-backed easy launch
- **THEN** the touring skill asks for or recommends the mailbox address and principal id needed for manual registration
- **AND THEN** it routes that account-creation step through `houmao-mailbox-mgr` instead of describing it as launch-owned mailbox bootstrap
