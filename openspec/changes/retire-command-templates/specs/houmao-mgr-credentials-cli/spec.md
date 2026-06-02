## REMOVED Requirements

### Requirement: Credential CLI surfaces provide command-template entries
**Reason**: Credential command-template entries are retired with the command-template renderer.
**Migration**: Use direct `houmao-mgr project credentials <tool> ...` or `houmao-mgr internals native-agent credentials <tool> ...` commands for Claude, Codex, and Gemini credential workflows.

#### Scenario: Credential command is documented directly
- **WHEN** a skill documents credential add, set, login, list, get, rename, or remove
- **THEN** it shows the direct credential command path rather than a command-template id
