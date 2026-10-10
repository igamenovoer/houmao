## MODIFIED Requirements

### Requirement: README distinguishes external and managed pack defaults
The README SHALL state that explicit external-home installation defaults to the admin pack, while managed launch, rebuild, relaunch, and join default to the agent pack.

It SHALL state that the admin welcome and entrypoint install atomically and that no default installs both actors. It SHALL distinguish catalog-backed system-skill packs from provider-native role-prompt files created by brain construction and SHALL contain no managed auto-skill category.

#### Scenario: Reader compares two homes
- **WHEN** a reader compares a human-operated CLI-agent home with a Houmao-managed home
- **THEN** the README identifies the admin pack for the first and the agent pack for the second
- **AND THEN** it does not describe provider-native prompt files as skills or pack members
