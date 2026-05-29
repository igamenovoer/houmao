## MODIFIED Requirements

### Requirement: Lite operations remain bounded and delegate platform mechanics
Lite generated skills SHALL model on-event and tick work as prompt-triggered bounded turns.

Lite generated skills SHALL NOT instruct agents to sleep, poll, tail logs, or wait in-chat for future work.

Lite generated skills SHALL route ordinary mailbox operations through maintained Houmao mailbox skills or supported CLI surfaces.

Lite generated skills SHALL route gateway, notifier, launch, messaging, inspection, workspace, and agent-definition operations through their owning maintained Houmao skills or supported CLI surfaces.

When explicit workspace setup is needed, lite guidance SHALL route standard Houmao workspace planning, creation, validation, and summaries through `houmao-utils-workspace-mgr`.

Lite guidance SHALL NOT describe workspace-manager `execute` as the standard workspace setup operation.

#### Scenario: Mail-driven lite event stops after one action
- **WHEN** a lite generated receiver skill handles one recognized template type
- **THEN** it performs one bounded role-owned action
- **AND THEN** it ends the turn after required mail, state, or artifact updates complete

#### Scenario: Lite does not duplicate maintained platform contracts
- **WHEN** a lite generated operator skill needs to enable notifier behavior for a participant
- **THEN** it routes that operation through `houmao-agent-gateway`
- **AND THEN** it does not restate the low-level gateway notifier contract inline

#### Scenario: Lite routes workspace readiness through workspace manager
- **WHEN** a lite generated process needs explicit standard workspace setup or readiness evidence
- **THEN** lite guidance routes planning, creation, validation, or summaries through `houmao-utils-workspace-mgr`
- **AND THEN** it does not use `execute` as the standard workspace-manager operation name
