## ADDED Requirements

### Requirement: `houmao-mailbox-mgr` uses CLI-owned templates for mailbox command authoring
The packaged `houmao-mailbox-mgr` skill SHALL instruct agents to use CLI-owned command templates before authoring supported mailbox commands.

Covered command families SHALL include shared mailbox commands, project mailbox commands, project mailbox account/message commands, and managed-agent mailbox binding commands.

The skill SHALL keep transport explanation and mailbox workflow guidance in skill text, but command shapes, required fields, clear/remove behavior, and conflict rules SHALL come from the template registry.

#### Scenario: Project mailbox account get uses template renderer
- **WHEN** a user asks the skill to inspect one project mailbox account by address
- **THEN** the skill guidance directs the agent to render the project mailbox account-get template
- **AND THEN** it does not require a skill-owned command skeleton

#### Scenario: Managed-agent mailbox register uses template renderer
- **WHEN** a user asks the skill to register a filesystem mailbox binding for one managed agent
- **THEN** the skill guidance directs the agent to render the managed-agent mailbox register template
- **AND THEN** selector conflicts are handled by template blockers
