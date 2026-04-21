## ADDED Requirements

### Requirement: Getting-started docs explain canonical project skill storage versus derived projection
The getting-started documentation SHALL explain that canonical project-local custom skills live under `.houmao/content/skills/`.

That guidance SHALL explain that `.houmao/agents/skills/` is a derived compatibility projection rather than the source of truth for project-local skill authoring.

The docs SHALL introduce `houmao-mgr project skills ...` as the maintained surface for registering or updating project-local custom skills.

The docs SHALL introduce `houmao-mgr project migrate` as the supported command for existing users who need to convert one known older project structure into the current `houmao-mgr project` layout.

When the docs describe project skill storage modes, they SHALL explain that:

- `copy` mode creates a project-owned copy under `.houmao/content/skills/<name>/`,
- `symlink` mode creates `.houmao/content/skills/<name>` as a symlink to the chosen source directory.

#### Scenario: Reader sees one canonical project skill root
- **WHEN** a reader follows the getting-started project overlay documentation
- **THEN** the docs identify `.houmao/content/skills/` as the canonical project-local skill root
- **AND THEN** the docs describe `.houmao/agents/skills/` as derived projection state

#### Scenario: Reader is directed to explicit project migration for older overlays
- **WHEN** a reader already has one older project overlay that predates the current project layout
- **THEN** the getting-started docs direct them to `houmao-mgr project migrate`
- **AND THEN** the docs do not imply that ordinary project commands will silently upgrade that overlay in place
