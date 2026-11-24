# System Skills Overview Guide Delta

## MODIFIED Requirements

### Requirement: System-skills overview explains the actor-pack model
The getting-started guide SHALL explain the admin pack for human operators and the agent pack for managed agents. It SHALL distinguish the welcome and actor entrypoint roles, the standalone shared and loop siblings, and the children owned by shared routines.

#### Scenario: Reader wants to choose a public skill
- **WHEN** a reader opens the system-skills overview
- **THEN** the guide distinguishes welcome, admin execution, and managed-agent execution
- **AND THEN** it provides a copyable public invocation for each applicable role

### Requirement: System-skills overview documents pack installation defaults and lifecycle
The guide SHALL explain that external-home CLI installation defaults to the admin pack and managed launch, rebuild, relaunch, and join default to the agent pack.

#### Scenario: Acceptance criteria
- **GIVEN** a reader who needs to select a supported tool and manage a skill installation
- **THEN** the guide describes explicit pack selection, atomic pack installation, and copy and symlink modes
- **AND THEN** it explains the ownership config, status classifications, upgrade, uninstall, legacy conflicts, and effective-home resolution

#### Scenario: Reader compares external and managed defaults
- **WHEN** a reader needs to know which public skills appear in a home
- **THEN** the guide explains the admin external default and agent managed default
- **AND THEN** it states that no default lane installs both actor packs

### Requirement: System-skills overview provides a protected routine route map
The guide SHALL map every manifest-declared shared child to its public route names and supported `houmao-mgr` command families. Each row SHALL identify eligible actors and distinguish internal designators from public invocations.

#### Scenario: Reader looks up mailbox behavior
- **WHEN** a reader searches the route map for mailbox work
- **THEN** the guide distinguishes notifier-round processing from ordinary mailbox operations
- **AND THEN** it shows that managed mailbox work begins through `houmao-agent-entrypoint`

#### Scenario: Reader looks up access and peer edits
- **WHEN** a reader searches the route map for gateway authorization or versioned peer file edits
- **THEN** the guide shows the `agent-access` and `agent-files` routes and their associated CLI command families
- **AND THEN** it distinguishes owner-local policy administration from signed peer requests and authorized gateway file operations

### Requirement: Overview guide explains the static six-skill collection
The overview SHALL list the six standalone roots and distinguish them from the manifest-declared children of `houmao-shared-routines`. It SHALL explain that actor entrypoints support actor-scoped implicit selection, while welcome, shared routines, and the loops require explicit initial selection.

#### Scenario: Reader opens the current inventory section
- **WHEN** a reader opens the current system-skill inventory
- **THEN** the standalone inventory matches the six `public/*/SKILL.md` roots
- **AND THEN** shared children are presented as parent-scoped routes rather than independent install units
