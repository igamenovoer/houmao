## Purpose
Define how Houmao-owned system skills stay flat and tool-native across multiple logical workflow groups.
## Requirements
### Requirement: System-skill families contain no Gemini provider guidance
Packaged current system-skill families SHALL NOT define Gemini-specific projection, credential, launch, or discovery behavior.

#### Scenario: Packaged skill audit excludes Gemini provider instructions
- **WHEN** maintainers scan current system-skill content and catalog metadata
- **THEN** no active provider route or example claims Gemini support

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

#### Scenario: Codex installs mailbox and user-control skills into the same flat skill root
- **WHEN** Houmao installs one mailbox-oriented skill and one user-control skill into a Codex home
- **THEN** both skills project under top-level Houmao-owned skill directories in `skills/`
- **AND THEN** Codex does not require a visible family subdirectory for those installed skills

#### Scenario: Claude keeps top-level Houmao-owned skill directories across logical groups
- **WHEN** Houmao installs mailbox-oriented and user-control skills into a Claude home
- **THEN** both skills project into top-level Houmao-owned skill directories under `skills/`
- **AND THEN** Claude does not require a visible family subdirectory for those installed skills

#### Scenario: Gemini keeps top-level Houmao-owned skill directories across logical groups
- **WHEN** Houmao installs mailbox-oriented and user-control skills into a Gemini home
- **THEN** both skills project into top-level Houmao-owned skill directories under `.gemini/skills/`
- **AND THEN** Gemini does not require a visible family subdirectory for those installed skills

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

#### Scenario: CLI default installation resolves the all set
- **WHEN** an operator installs the CLI-default Houmao-owned system-skill selection into a supported tool home
- **THEN** the resolved selection expands the `all` set
- **AND THEN** each installed skill projects into the visible path appropriate for its supported tool

#### Scenario: Managed default installation resolves core and extensions
- **WHEN** Houmao installs system skills into a managed launch or join home
- **THEN** the resolved selection expands `core` and `extensions` in that order
- **AND THEN** each installed skill projects into the visible path appropriate for its supported tool

#### Scenario: Install state records flat projected paths
- **WHEN** Houmao installs system skills from multiple logical workflow groups into the same supported tool home
- **THEN** the recorded or discovered Houmao-owned install surface uses the flat projected relative directories for those skills
- **AND THEN** later reinstall, status, or collision checks use those exact flat owned paths
