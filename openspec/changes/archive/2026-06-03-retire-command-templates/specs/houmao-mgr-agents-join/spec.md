## REMOVED Requirements

### Requirement: Agent join CLI surface provides a command-template entry
**Reason**: Join command-template entries are retired with the command-template renderer.
**Migration**: Use the direct `houmao-mgr agents join ...` command and preserve selector/posture guardrails in skill guidance.

#### Scenario: Join command is documented directly
- **WHEN** a skill documents joining or adopting an agent session
- **THEN** it shows the direct `houmao-mgr agents join ...` command rather than a command-template id
