## REMOVED Requirements

### Requirement: Gateway CLI surfaces provide command-template entries
**Reason**: Gateway command-template entries are retired with the command-template renderer.
**Migration**: Use direct `houmao-mgr agents single ... gateway ...` or `houmao-mgr agents self gateway ...` commands in skill guidance, and keep HTTP workflow decisions in gateway skill prose.

#### Scenario: Gateway commands are documented directly
- **WHEN** a skill documents gateway prompt, send-keys, notifier, or reminder actions
- **THEN** it shows direct scoped `houmao-mgr agents ... gateway ...` commands rather than command-template ids
