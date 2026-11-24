# docs-system-skills-overview-guide Specification

## Purpose

Define the getting-started narrative-guide requirements for the packaged Houmao-owned system skills: a single page that bridges the README catalog row view and the CLI reference page by walking readers through each shipped skill, the CLI families it routes to, and the managed-home auto-install versus external-home CLI-default install distinction.
## Requirements
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

### Requirement: System-skills overview presents the admin welcome tour
The guide SHALL describe `houmao-admin-welcome` as the read-only first-use and reorientation surface.

It SHALL list the welcome commands and curated paths, explain the mutation boundary, and demonstrate context-preserving handoff to `houmao-admin-entrypoint`. It SHALL identify `houmao-touring` only as the retired name when migration context requires it.

#### Scenario: First-time reader follows the guided path
- **WHEN** a reader wants a guided introduction
- **THEN** the guide directs them to `$houmao-admin-welcome start-guided-tour`
- **AND THEN** it explains that concrete execution transfers to the admin entrypoint

### Requirement: System-skills overview explains actor safety and protected limitations
The guide SHALL state that the admin assistant is not the managed agent, that the agent entrypoint verifies `agents self identity`, and that shared routines preserve the actor frame.

It SHALL state that protected placement is a discovery convention rather than an authorization boundary and that runtime and CLI checks enforce real target validity.

#### Scenario: Reader sees a protected routine path
- **WHEN** the guide shows an internal protected designator
- **THEN** it warns against direct standalone invocation
- **AND THEN** it provides the corresponding public entrypoint invocation

### Requirement: Overview guide explains the static six-skill collection
The overview SHALL list the six standalone roots and distinguish them from the manifest-declared children of `houmao-shared-routines`. It SHALL explain that actor entrypoints support actor-scoped implicit selection, while welcome, shared routines, and the loops require explicit initial selection.

#### Scenario: Reader opens the current inventory section
- **WHEN** a reader opens the current system-skill inventory
- **THEN** the standalone inventory matches the six `public/*/SKILL.md` roots
- **AND THEN** shared children are presented as parent-scoped routes rather than independent install units

### Requirement: Overview guide explains sibling actor routing
The guide SHALL explain admin entrypoint, agent entrypoint, direct shared-routines, and direct loop posture. It SHALL show that actor entrypoints route ordinary work to the shared sibling and loop work to top-level loop siblings.

The guide SHALL NOT show shared routines nested beneath either entrypoint or describe a protected mount assembled at installation time.

#### Scenario: Reader follows an inspection example
- **WHEN** a reader wants human-operator inspection
- **THEN** the guide shows an admin-entrypoint route and explains its delegation to shared routines
- **AND THEN** it also identifies direct shared invocation as the advanced bypass

### Requirement: Overview guide documents both installation paths
The overview SHALL distinguish Houmao pack-aware installation from standard Skills CLI or copy-paste installation.

It SHALL provide complete admin and agent sibling lists for external installation, explain that Skills CLI does not resolve Houmao pack dependencies automatically, and show that exact discovery exposes six standalone roots.

#### Scenario: Reader chooses Skills CLI installation
- **WHEN** a reader follows the standard Agent Skills path
- **THEN** the guide provides an all-skills example and explicit actor-specific selections
- **AND THEN** it does not imply that selecting only an entrypoint installs its siblings

### Requirement: Overview guide preserves the guided-tour entry path
The overview SHALL present `$houmao-admin-welcome` as the state-aware, read-only first-user and reorientation route. It SHALL summarize the maintained guided paths and show executable handoff to the admin entrypoint.

#### Scenario: First-time reader wants orientation
- **WHEN** a reader does not yet know which operational route fits
- **THEN** the guide directs the reader to admin welcome
- **AND THEN** it does not replace the guided experience with the shared routine catalog
