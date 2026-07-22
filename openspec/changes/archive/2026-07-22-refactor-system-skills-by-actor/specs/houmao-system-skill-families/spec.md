## ADDED Requirements

### Requirement: Audience packs replace workflow-family install sets
Houmao SHALL use `admin` and `agent` as the only installable pack ids for the maintained system-skill surface.

The admin pack SHALL represent human-operator orientation and execution. The agent pack SHALL represent managed-agent self execution. Workflow categories such as mailbox, lifecycle, loop, utility, and interop MAY remain documentation labels but SHALL NOT be install selectors.

#### Scenario: Operator requests the old core set
- **WHEN** an operator attempts to select `core`, `extensions`, or `all`
- **THEN** selection fails with a pack-migration diagnostic
- **AND THEN** it names `admin` and `agent` as the supported pack ids

### Requirement: Default lanes install one actor pack
CLI-default external-home installation SHALL select `admin`. Managed launch, rebuild, relaunch, and join SHALL select `agent`.

No default lane SHALL install both actor packs. Explicit repeated pack selection MAY install both for development without merging their public roles or actor contexts.

#### Scenario: Managed join uses one actor family
- **WHEN** a joined session accepts default system-skill installation
- **THEN** its home receives the agent pack
- **AND THEN** the admin pack remains absent unless explicitly selected

## REMOVED Requirements

### Requirement: Houmao system skills keep flat visible projection across supported tools
**Reason**: Only public skills remain flat; protected routines are nested.
**Migration**: Inspect public paths at the tool root and protected paths beneath entrypoints.

### Requirement: Default Houmao-owned system-skill selection can include multiple logical groups
**Reason**: Defaults select one actor pack rather than several workflow groups.
**Migration**: Use the admin default externally and the agent default in managed homes.

### Requirement: Houmao system skills keep flat visible projection when the touring skill group is installed
**Reason**: The touring group and top-level touring skill are removed.
**Migration**: Use the public admin welcome sibling.

### Requirement: Default Houmao-owned system-skill selection can include the touring logical group
**Reason**: The touring set no longer exists.
**Migration**: The admin pack always includes its welcome role.

### Requirement: System-skill organization groups are separate from installable sets
**Reason**: Workflow install sets are removed entirely.
**Migration**: Treat workflow labels as documentation only and select actor packs.

### Requirement: Utility logical group is included through all
**Reason**: The `all` set is removed.
**Migration**: Shared utilities are composed into each eligible actor pack.

### Requirement: Extension skills are default-installed without becoming core dependencies
**Reason**: The extensions set is removed and graphing is a protected shared routine.
**Migration**: Use the graphing route through either eligible entrypoint.
