## REMOVED Requirements

### Requirement: Shared mailbox CLI surfaces provide command-template entries
**Reason**: Shared mailbox command-template entries are retired with the command-template renderer.
**Migration**: Use direct `houmao-mgr mailbox ...` commands in skill guidance for shared mailbox initialization, status, registration, cleanup, export, and message operations.

#### Scenario: Shared mailbox command is documented directly
- **WHEN** a skill documents a shared mailbox operation
- **THEN** it shows the direct `houmao-mgr mailbox ...` command rather than a command-template id
