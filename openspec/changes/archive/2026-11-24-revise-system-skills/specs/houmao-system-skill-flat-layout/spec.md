# System-Skill Flat Layout Delta

## MODIFIED Requirements

### Requirement: Nested layout expresses ownership rather than workflow families
The nested path SHALL express ownership by the standalone shared root. Commands and references SHALL remain below their owning skill. Mailbox, project, loop, and utility labels SHALL NOT create additional installable filesystem families.

#### Scenario: Mailbox routine is installed for a managed agent
- **WHEN** the agent pack installs the shared root
- **THEN** the mailbox routine appears under `houmao-shared-routines/subskills/`
- **AND THEN** no top-level mailbox family or peer mailbox skill is projected

### Requirement: Houmao-owned system skills use a flat packaged asset layout
Each standalone current system skill SHALL have one top-level directory directly under `src/houmao/agents/assets/system_skills/public/`. The static collection specification defines the six public roots. Only the shared root SHALL own current parent-scoped runtime skills directly under `subskills/`.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

The active packaged source SHALL NOT require an external `protected/` tree, audience route variants, or family-specific source directories. Historical loop references MAY remain under `legacy/` and SHALL NOT be current install units.

#### Scenario: Maintainer inspects the packaged skill asset root
- **WHEN** a maintainer inspects the maintained Houmao system-skill assets
- **THEN** the six standalone skills live under `src/houmao/agents/assets/system_skills/public/<houmao-skill>/`
- **AND THEN** all manifest-declared shared children live under `public/houmao-shared-routines/subskills/` and own `SKILL-MAIN.md`
- **AND THEN** no active current skill depends on a separately composed `protected/` source tree

## ADDED Requirements

### Requirement: Actor packs group standalone install units
The system SHALL group current system skills by reserved `houmao-` names, actor pack membership, and explicit parent ownership. Workflow labels MAY organize route indexes and documentation.

#### Scenario: Operator inspects current Houmao system-skill inventory
- **WHEN** an operator lists the current manifest
- **THEN** the output distinguishes standalone install units from declared shared children
- **AND THEN** it groups standalone installation through admin and agent packs
- **AND THEN** it treats mailbox and project workflow labels as route guidance

## REMOVED Requirements

### Requirement: Public discovery remains flat while protected implementation is nested
**Reason**: The static shared sibling owns all nested paths. Actor entrypoints contain no mounted skill trees.

**Migration**: Use the flat packaged asset layout and the static collection requirements.

### Requirement: Grouping is expressed through reserved names and named sets rather than filesystem families
**Reason**: Current install units are grouped by actor packs.

**Migration**: Use the admin or agent pack and select the appropriate nested route after invocation.
