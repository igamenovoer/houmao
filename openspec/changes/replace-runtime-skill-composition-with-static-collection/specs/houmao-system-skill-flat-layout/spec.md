## MODIFIED Requirements

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
