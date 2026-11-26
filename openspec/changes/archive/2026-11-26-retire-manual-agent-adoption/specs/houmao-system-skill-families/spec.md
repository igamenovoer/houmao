# Spec Delta

## ADDED Requirements

### Requirement: Actor pack selection preserves flat managed skill paths
The maintained installable grouping SHALL consist of the `admin` and `agent` actor packs rather than workflow sets.

CLI-default external-home installation SHALL resolve the admin pack. Managed launch, rebuild, and relaunch SHALL resolve the agent pack. Explicit selection MAY install both packs and SHALL deduplicate shared standalone members.

#### Scenario: CLI default installation resolves admin
- **WHEN** an operator installs Houmao system skills without a pack selector
- **THEN** the resolved selection contains all five admin-pack standalone members
- **AND THEN** each member projects into its top-level tool-native path

#### Scenario: Managed default installation resolves agent
- **WHEN** Houmao installs default system skills for a managed home
- **THEN** the resolved selection contains all four agent-pack standalone members
- **AND THEN** admin-only public roots remain absent

#### Scenario: Install state records shared pack ownership
- **WHEN** both packs are installed in one home
- **THEN** install state records six unique top-level paths
- **AND THEN** it records both pack owners for shared routines and the two loop paths

#### Scenario: Install state records flat projected paths
- **WHEN** an operator explicitly installs both actor packs into the same supported tool home
- **THEN** the recorded or discovered Houmao-owned install surface uses the flat projected relative directories for those skills
- **AND THEN** later reinstall, status, or collision checks use those exact flat owned paths

### Requirement: Default skill installation selects one actor pack
CLI-default external-home installation SHALL select `admin`. Managed launch, rebuild, and relaunch SHALL select `agent`.

No default lane SHALL install both actor packs. Explicit repeated pack selection MAY install both for development without merging their public roles or actor contexts.

#### Scenario: Managed launch uses one actor family
- **WHEN** a managed launch uses default system-skill installation
- **THEN** its home receives the agent pack
- **AND THEN** the admin pack remains absent unless explicitly selected

## REMOVED Requirements

### Requirement: Default Houmao-owned system-skill selection can include multiple logical groups
**Reason**: The maintained installer selects actor packs and no longer resolves workflow sets.
**Migration**: Select the admin or agent pack, or select both explicitly.

### Requirement: Default lanes install one actor pack
**Reason**: Managed-join installation is retired.
**Migration**: Use the managed launch default or explicitly select a pack.
