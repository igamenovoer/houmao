## Purpose
Define the flat packaged asset layout for the current Houmao-owned system-skill catalog.
## Requirements
### Requirement: Public discovery remains flat while protected implementation is nested
Houmao SHALL project public system skills as top-level directories in the established tool-native skill root.

Protected mounts and routines SHALL appear only below executable public entrypoints. The packaged source SHALL separate `public/` and `protected/` trees rather than placing every routine directly under the asset root.

#### Scenario: Operator inspects an installed admin pack
- **WHEN** an operator lists the top-level Houmao skills in a supported home
- **THEN** only `houmao-admin-welcome` and `houmao-admin-entrypoint` appear for the admin pack
- **AND THEN** the entrypoint contains nested protected implementation

### Requirement: Nested layout expresses ownership rather than workflow families
The nested path SHALL express the entrypoint, protected mount, and true subskill ownership chain.

Mailbox, project, loop, and utility labels SHALL NOT create independently installable filesystem families. Commands and references SHALL remain beneath the skill that owns them.

#### Scenario: Mailbox routine is installed for a managed agent
- **WHEN** the agent pack includes a mailbox routine
- **THEN** the routine appears under `houmao-agent-entrypoint/subskills/houmao-shared-routines/subskills/`
- **AND THEN** no top-level mailbox family or peer mailbox skill is projected

### Requirement: Houmao-owned system skills use a flat packaged asset layout
The system SHALL package each standalone current Houmao system skill as one top-level directory directly under `src/houmao/agents/assets/system_skills/public/`.

The standalone inventory SHALL be the six static roots defined by `houmao-system-skill-static-collection`. Only `houmao-shared-routines` SHALL contain current parent-scoped runtime skills, and those children SHALL live directly beneath its `subskills/` directory with `SKILL-MAIN.md` entrypoints.

The active packaged source SHALL NOT require an external `protected/` tree, audience route variants, or family-specific source directories. Historical loop references MAY remain under `legacy/` and SHALL NOT be current install units.

#### Scenario: Maintainer inspects the packaged skill asset root
- **WHEN** a maintainer inspects the maintained Houmao system-skill assets
- **THEN** the six standalone skills live under `src/houmao/agents/assets/system_skills/public/<houmao-skill>/`
- **AND THEN** the sixteen parent-scoped routines live under `public/houmao-shared-routines/subskills/`
- **AND THEN** no active current skill depends on a separately composed `protected/` source tree

### Requirement: Grouping is expressed through reserved names and named sets rather than filesystem families
The system SHALL use reserved `houmao-` names, actor pack membership, and explicit skill ownership to group current system skills.

Admin and agent packs SHALL group standalone install units. `houmao-shared-routines/subskills/` SHALL express parent ownership for ordinary routines. Workflow labels such as mailbox, project, loop, utility, and interop MAY appear in route indexes and documentation but SHALL NOT create installable filesystem families.

#### Scenario: Operator inspects current Houmao system-skill inventory
- **WHEN** an operator lists the current manifest
- **THEN** the output distinguishes six standalone skills from sixteen shared children
- **AND THEN** it groups standalone installation through admin and agent packs
- **AND THEN** it does not expose mailbox or project filesystem namespaces as install units

#### Scenario: Operator inspects current Houmao-owned skill inventory
- **WHEN** an operator lists the packaged Houmao-owned system skills and named sets
- **THEN** the current skills remain distinguishable through their reserved `houmao-` names
- **AND THEN** mailbox-oriented and project-oriented groupings remain expressible through named sets such as `mailbox-full` and `project-easy`
- **AND THEN** those groupings do not require `mailbox/` or `project/` filesystem namespaces

