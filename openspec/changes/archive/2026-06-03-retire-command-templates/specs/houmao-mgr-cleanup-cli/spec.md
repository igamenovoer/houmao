## REMOVED Requirements

### Requirement: Agent cleanup CLI surfaces provide command-template entries
**Reason**: Cleanup command-template entries are retired with the command-template renderer.
**Migration**: Use direct `houmao-mgr agents single ... cleanup session`, `houmao-mgr agents single ... cleanup logs`, or other maintained scoped cleanup commands.

#### Scenario: Cleanup command is documented directly
- **WHEN** a skill documents session or log cleanup
- **THEN** it shows a direct scoped cleanup command rather than a command-template id
