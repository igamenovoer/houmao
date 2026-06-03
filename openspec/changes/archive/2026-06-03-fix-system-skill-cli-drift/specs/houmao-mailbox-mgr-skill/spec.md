## REMOVED Requirements

### Requirement: `houmao-mailbox-mgr` uses CLI-owned templates for mailbox command authoring
**Reason**: The command-template renderer has been retired; supported mailbox administration commands are documented directly in the packaged skill.

**Migration**: Use direct `houmao-mgr mailbox ...`, `houmao-mgr project mailbox ...`, and scoped `houmao-mgr agents single ... mailbox ...` command snippets.

#### Scenario: Mailbox commands no longer use template rendering
- **WHEN** a user asks the skill for mailbox administration work
- **THEN** the skill shows a direct maintained mailbox command
- **AND THEN** it does not tell the agent to render a command-template id first

## ADDED Requirements

### Requirement: `houmao-mailbox-mgr` uses direct command snippets for mailbox commands
The packaged `houmao-mailbox-mgr` skill SHALL document supported mailbox administration commands as direct fenced `bash` snippets or equivalent explicit command shapes.

Covered command families SHALL include shared mailbox commands, project mailbox commands, project mailbox account/message commands, and scoped managed-agent mailbox binding commands.

The skill SHALL keep transport explanation and mailbox workflow guidance in skill text, but executable command shapes SHALL be shown directly.

The skill SHALL NOT reference `houmao-mgr internals command-templates`, command-template ids, template blockers, or command-template support when explaining mailbox administration commands.

#### Scenario: Managed-agent mailbox register uses direct scoped command shape
- **WHEN** a user asks the skill to register a filesystem mailbox binding for one selected managed agent
- **THEN** the skill guidance shows a direct command under `houmao-mgr agents single --agent-name <agent-name> mailbox register ...` or `houmao-mgr agents single --agent-id <agent-id> mailbox register ...`
- **AND THEN** it does not direct the agent to render a managed-agent mailbox command-template id
