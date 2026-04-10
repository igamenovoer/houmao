## ADDED Requirements

### Requirement: `houmao-mailbox-mgr` distinguishes manual registration from launch-owned and late-binding mailbox association
The packaged `houmao-mailbox-mgr` skill SHALL describe `mailbox register` and `project mailbox register` as manual filesystem mailbox-account administration rather than as the default preparation step for every mailbox-enabled managed-agent launch.

When the user is preparing a new specialist-backed easy instance whose filesystem mailbox identity will be derived from the managed-agent instance name under the same shared mailbox root, the skill SHALL explain that launch-time mailbox bootstrap may own registration for that address and SHALL NOT present manual preregistration of the same address as the default lane.

When the user wants to add or update filesystem mailbox support for an already-running local managed agent, the skill SHALL direct that work to `agents mailbox register` rather than to `project mailbox register`.

When the user wants a standalone shared, team, integration, or operator-facing mailbox account that is not being created by immediate easy launch and is not an existing-agent late binding case, the skill SHALL continue to treat `mailbox register` or `project mailbox register` as the correct maintained lane.

#### Scenario: Same-root easy launch mailbox setup is not treated as mandatory manual preregistration
- **WHEN** the user asks `houmao-mailbox-mgr` how to prepare mailbox support for a new specialist-backed easy instance
- **AND WHEN** the intended mailbox address matches the ordinary launch-owned pattern derived from the managed-agent instance name under the same shared root
- **THEN** the skill explains that manual `project mailbox register` for that address is not the default preparatory step
- **AND THEN** it distinguishes mailbox-root bootstrap from later launch-owned registration

#### Scenario: Existing live managed agent uses the late-binding lane
- **WHEN** the user asks to add filesystem mailbox support to one already-running local managed agent
- **THEN** the skill directs the caller to `houmao-mgr agents mailbox register`
- **AND THEN** it does not reinterpret that task as generic `project mailbox register` account administration

#### Scenario: Shared mailbox account still uses manual registration
- **WHEN** the user asks to create one shared or manually named mailbox account under a mailbox root
- **AND WHEN** that account is not being created by immediate easy launch and is not an existing-agent late-binding request
- **THEN** the skill directs the caller to `houmao-mgr mailbox register` or `houmao-mgr project mailbox register` according to scope
- **AND THEN** it keeps that task inside mailbox-account administration rather than launch guidance
