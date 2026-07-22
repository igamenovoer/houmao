## ADDED Requirements

### Requirement: System-skills overview explains the actor-pack model
`docs/getting-started/system-skills-overview.md` SHALL explain that Houmao exposes an admin pack for human-operator work and an agent pack for managed-agent work.

The guide SHALL list the three public skills and roles: `houmao-admin-welcome`, `houmao-admin-entrypoint`, and `houmao-agent-entrypoint`. It SHALL state that protected routines are nested implementation and are not independent install or public trigger surfaces.

#### Scenario: Reader wants to choose a public skill
- **WHEN** a reader opens the system-skills overview
- **THEN** the guide distinguishes welcome, admin execution, and managed-agent execution
- **AND THEN** it provides a copyable public invocation for each applicable role

### Requirement: System-skills overview documents pack installation defaults and lifecycle
The guide SHALL explain that external-home CLI installation defaults to the admin pack and managed launch, rebuild, relaunch, and join default to the agent pack.

It SHALL document explicit pack selection, atomic admin welcome and entrypoint management, copy and symlink posture, pack receipts, status classifications, upgrade, uninstall, legacy conflict handling, effective-home resolution, and supported tool targets without claiming Gemini support.

#### Scenario: Reader compares external and managed defaults
- **WHEN** a reader needs to know which public skills appear in a home
- **THEN** the guide explains the admin external default and agent managed default
- **AND THEN** it states that no default lane installs both actor packs

### Requirement: System-skills overview provides a protected routine route map
The guide SHALL provide a compact route map from each maintained protected logical id to its eligible admin, agent, or shared entrypoint route and canonical `houmao-mgr` command families.

The map SHALL include every manifest-declared protected routine, distinguish admin-only and agent-only routines, identify actor-specific branches for shared routines, and label protected designators as internal route traces.

#### Scenario: Reader looks up mailbox behavior
- **WHEN** a reader searches the route map for mailbox work
- **THEN** the guide distinguishes notifier-round processing from ordinary mailbox operations
- **AND THEN** it shows that managed mailbox work begins through `houmao-agent-entrypoint`

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

## REMOVED Requirements

### Requirement: Getting-started guide narrates the packaged system skills
**Reason**: The guide now narrates public actor packs and protected routes rather than peer packaged skills.
**Migration**: Use the actor-pack overview and protected route map.

### Requirement: Overview guide lists the renamed AG-UI interop skill
**Reason**: AG-UI interop is protected implementation rather than a public inventory row.
**Migration**: List it in the protected route map with both eligible actors.

### Requirement: System-skills overview guide lists the manual guided touring skill
**Reason**: `houmao-touring` is retired.
**Migration**: Document `houmao-admin-welcome` and its guided paths.

### Requirement: System-skills overview guide uses the dedicated credential-management routing
**Reason**: Credential guidance is now an admin-only protected route.
**Migration**: Document the admin entrypoint's credential route and canonical CLI families.

### Requirement: Overview guide table enumerates every catalog entry
**Reason**: The flat catalog entry table is replaced by three public roles plus a protected route map.
**Migration**: Enumerate public and protected records in separate sections.

### Requirement: System-skills overview guide avoids stale counts
**Reason**: One flat skill count no longer describes the public/protected model.
**Migration**: State counts by manifest record type or derive them automatically.

### Requirement: Overview guide routes credential management through the dedicated CLI
**Reason**: CLI routing remains but now appears under an actor-qualified protected route.
**Migration**: Keep command-family detail in the protected route map.

### Requirement: System-skills overview guide includes the packaged memory-management skill
**Reason**: Memory management is protected shared content.
**Migration**: List the memory route for both eligible entrypoints.

### Requirement: System-skills overview mentions Copilot installation
**Reason**: Tool support must be documented at pack level.
**Migration**: Include Copilot in the supported pack-projection target section.

### Requirement: System-skills overview guide explains uninstall behavior
**Reason**: Per-skill removal is replaced by receipt-owned pack uninstall.
**Migration**: Document pack-atomic uninstall and conflict preservation.

### Requirement: System-skills overview guide explains organization groups and installable sets
**Reason**: `core`, `extensions`, and `all` are removed.
**Migration**: Explain actor packs and treat workflow labels as documentation only.

### Requirement: System-skills overview guide includes the workspace manager utility skill
**Reason**: Workspace management is a protected shared route.
**Migration**: List it in the protected route map.

### Requirement: System-skills overview routes agent-definition concerns to unified skill
**Reason**: Agent definition is a protected admin route rather than a public skill.
**Migration**: Document its admin-entrypoint invocation and canonical ownership.

### Requirement: System-skills overview presents pro-only loop control
**Reason**: Both pro and lite remain maintained protected routes.
**Migration**: Document their distinct protected routes and welcome choices.

### Requirement: System-skills overview lists the lite loop skill
**Reason**: Lite is no longer a public inventory row.
**Migration**: List it in the protected route map.

### Requirement: System-skills overview explains skill-level help
**Reason**: Help differs by public role and protected route.
**Migration**: Document welcome help, entrypoint help, and internal route summaries separately.

### Requirement: System-skills overview explains installation choices
**Reason**: Set and subset choices are replaced by packs.
**Migration**: Document repeatable pack selection and defaults.

### Requirement: System-skills overview explains prompt-level help
**Reason**: Direct peer-skill prompt help is removed.
**Migration**: Use public entrypoint and welcome help examples.

### Requirement: System-skills overview omits the removed LLM Wiki utility skill
**Reason**: The protected manifest is authoritative and no low-level inventory exception is needed.
**Migration**: Omit any routine not declared by the manifest.

### Requirement: System-skills overview explains Kimi reachability constraints
**Reason**: Kimi reachability now applies to public pack projections.
**Migration**: Keep the maintained caveat in the supported-target section.

### Requirement: System-skills overview guide lists the graphing extension skill
**Reason**: Graphing is a protected shared route and extensions are not a pack.
**Migration**: List graphing in the protected route map.

### Requirement: System-skills overview guide explains extension routing boundary
**Reason**: The extensions set and peer-extension boundary are removed.
**Migration**: Explain graphing as an optional protected routine with no effect on unrelated routes.

### Requirement: System-skills guide excludes Gemini
**Reason**: Provider exclusions now apply to pack projection as a whole.
**Migration**: State the supported pack targets once in the installation section.
