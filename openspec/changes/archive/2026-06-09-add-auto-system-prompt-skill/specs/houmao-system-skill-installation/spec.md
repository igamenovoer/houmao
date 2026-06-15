## ADDED Requirements

### Requirement: System-skill policy does not control managed auto skills
Houmao system-skill installation, status, sync, and removal workflows SHALL manage only catalog-known Houmao system skills.

Managed auto skills SHALL remain outside system-skill catalog selection, named sets, CLI-default installation, managed-launch system-skill policy, and explicit uninstall behavior.

Disabling or replacing system-skill selection for a managed launch SHALL NOT disable a required managed auto skill.

#### Scenario: Disabled system-skill selection leaves auto skill eligible
- **WHEN** managed launch resolves disabled system-skill installation for a home
- **AND WHEN** launch policy requires `houmao-auto-system-prompt`
- **THEN** system-skill installation resolves no system skills
- **AND THEN** auto-skill projection remains eligible through the separate managed auto-skill projection path

#### Scenario: System-skill uninstall does not remove auto skill by catalog sweep
- **WHEN** an operator runs a Houmao system-skill uninstall workflow for a tool home
- **THEN** the workflow targets catalog-known current or retired system-skill projections
- **AND THEN** it does not treat `houmao-auto-system-prompt` as a system-skill catalog entry

#### Scenario: System-skill status omits auto-skill inventory
- **WHEN** an operator inspects system-skill status for a tool home
- **THEN** the status reports catalog-known Houmao system skills
- **AND THEN** it does not report `houmao-auto-system-prompt` as an installed system skill
