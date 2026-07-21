## MODIFIED Requirements

### Requirement: Houmao system skills keep flat visible projection across supported tools
The system SHALL project every selected standalone Houmao system skill into one top-level directory under the established skill root for each supported tool.

The six public roots SHALL remain siblings at the tool root. The sixteen parent-scoped routines SHALL remain inside the projected `houmao-shared-routines` directory. No installed actor entrypoint SHALL contain a generated copy of shared routines or a loop skill.

#### Scenario: Codex installs both actor packs into one flat skill root
- **WHEN** Houmao installs admin and agent packs into a Codex home
- **THEN** the Codex `skills/` directory contains exactly the six standalone Houmao roots
- **AND THEN** shared children remain nested only under `skills/houmao-shared-routines/subskills/`

#### Scenario: Claude installs the agent pack
- **WHEN** Houmao installs the agent pack into a Claude home
- **THEN** the four agent-pack members are top-level siblings under `skills/`
- **AND THEN** no visible workflow-family directory is required

### Requirement: Default Houmao-owned system-skill selection can include multiple logical groups
The maintained installable grouping SHALL consist of the `admin` and `agent` actor packs rather than workflow sets.

CLI-default external-home installation SHALL resolve the admin pack. Managed launch, rebuild, relaunch, and join SHALL resolve the agent pack. Explicit selection MAY install both packs and SHALL deduplicate shared standalone members.

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

## REMOVED Requirements

### Requirement: Houmao system skills keep flat visible projection when the touring skill group is installed
**Reason**: `houmao-touring` and the touring workflow group are replaced by the standalone admin welcome inside the admin pack.
**Migration**: Use `houmao-admin-welcome` or install the admin pack.

### Requirement: Default Houmao-owned system-skill selection can include the touring logical group
**Reason**: Defaults select actor packs rather than a touring workflow set.
**Migration**: The admin pack includes `houmao-admin-welcome` as a required member.

### Requirement: System-skill organization groups are separate from installable sets
**Reason**: Current installation uses actor packs and static sibling dependencies rather than workflow sets.
**Migration**: Use `--pack admin` or `--pack agent`; treat workflow labels as documentation only.

### Requirement: Utility logical group is included through all
**Reason**: The `all` set is removed from the current static collection contract.
**Migration**: Workspace management is a child of `houmao-shared-routines`, included through both packs.

### Requirement: Extension skills are default-installed without becoming core dependencies
**Reason**: The `core` and `extensions` sets are removed; graphing is a shared child available through the installed shared-routines sibling.
**Migration**: Invoke the graphing route through an actor entrypoint or directly through `houmao-shared-routines`.
