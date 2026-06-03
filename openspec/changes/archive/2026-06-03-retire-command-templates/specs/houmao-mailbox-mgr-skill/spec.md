## REMOVED Requirements

### Requirement: `houmao-mailbox-mgr` uses CLI-owned templates for mailbox command authoring
**Reason**: Mailbox command templates are retired with the command-template renderer.
**Migration**: Document direct shared mailbox, project mailbox, project account/message, and managed-agent mailbox binding commands in fenced `bash` blocks.

#### Scenario: Mailbox authoring does not use templates
- **WHEN** the packaged skill documents mailbox commands
- **THEN** it shows direct maintained `houmao-mgr mailbox ...`, `houmao-mgr project mailbox ...`, or scoped managed-agent mailbox commands rather than command-template ids

## ADDED Requirements

### Requirement: `houmao-mailbox-mgr` uses direct command snippets for mailbox commands
The packaged `houmao-mailbox-mgr` skill SHALL document supported mailbox commands as fenced `bash` snippets.

Covered command families SHALL include shared mailbox commands, project mailbox commands, project mailbox account/message commands, and managed-agent mailbox binding commands.

The skill SHALL keep transport explanation and mailbox workflow guidance in skill text, while direct command snippets SHALL show required selectors, clear/remove posture, and option conflicts that matter before execution.

The skill SHALL NOT reference `houmao-mgr internals command-templates show`, `houmao-mgr internals command-templates render`, command-template ids, or template blockers.

#### Scenario: Project mailbox account get uses direct command snippet
- **WHEN** a user asks the skill to inspect one project mailbox account by address
- **THEN** the skill guidance shows the direct project mailbox account-get command
- **AND THEN** it does not require a renderer-owned command skeleton

#### Scenario: Managed-agent mailbox register validates selector conflicts directly
- **WHEN** a user asks the skill to register a filesystem mailbox binding for one managed agent
- **THEN** the skill checks selected-agent selector conflicts before command execution
- **AND THEN** it shows the direct scoped mailbox register command
