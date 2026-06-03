## REMOVED Requirements

### Requirement: Project mailbox CLI surfaces provide command-template entries
**Reason**: Project mailbox command-template entries are retired with the command-template renderer.
**Migration**: Use direct `houmao-mgr project mailbox ...` commands in skill guidance for project mailbox initialization, status, repair, cleanup, account inspection, and message operations.

#### Scenario: Project mailbox command is documented directly
- **WHEN** a skill documents a project mailbox operation
- **THEN** it shows the direct `houmao-mgr project mailbox ...` command rather than a command-template id
