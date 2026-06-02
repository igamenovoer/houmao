## REMOVED Requirements

### Requirement: Agent relaunch CLI surface provides a command-template entry
**Reason**: Relaunch command-template entries are retired with the command-template renderer.
**Migration**: Use direct `houmao-mgr agents single --agent-id <id> relaunch`, `houmao-mgr agents single --agent-name <name> relaunch`, or `houmao-mgr agents self relaunch` commands.

#### Scenario: Relaunch command is documented directly
- **WHEN** a skill documents relaunch for a selected agent or current session
- **THEN** it shows the direct scoped `houmao-mgr agents ... relaunch` command rather than a command-template id
