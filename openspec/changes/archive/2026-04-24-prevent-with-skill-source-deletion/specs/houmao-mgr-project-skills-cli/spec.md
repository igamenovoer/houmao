## MODIFIED Requirements

### Requirement: Project skill registration supports copy-backed and symlink-backed canonical entries
`houmao-mgr project skills add --name <name> --source <dir>` SHALL register one project skill at `.houmao/content/skills/<name>`.

`project skills add|set` SHALL accept `--mode copy|symlink`.

When `--mode copy` is used, the command SHALL copy the source directory into `.houmao/content/skills/<name>`.

When `--mode symlink` is used, the command SHALL create `.houmao/content/skills/<name>` as a symlink to the provided source directory.

When `--mode` is omitted, the default mode SHALL be `copy`.

The source directory SHALL contain `SKILL.md`.

The provided `--source <dir>` SHALL be treated as caller-owned input rather than Houmao-managed content.

`project skills add|set` SHALL mutate only Houmao-managed canonical or derived skill paths inside the active project overlay.

`project skills add|set` SHALL NOT delete, move, rewrite, or partially consume the provided source directory, regardless of whether the currently registered canonical entry is copy-backed or symlink-backed.

If registration or update fails after Houmao-managed paths were prepared or refreshed, rollback or cleanup SHALL still leave the caller-owned source directory untouched.

#### Scenario: Copy-backed skill registration creates a canonical project-owned copy
- **WHEN** `/repo/skillset/notes/SKILL.md` exists
- **AND WHEN** an operator runs `houmao-mgr project skills add --name notes --source /repo/skillset/notes --mode copy`
- **THEN** the project overlay stores `.houmao/content/skills/notes/` as a copied directory
- **AND THEN** project skill `notes` is available as one canonical project skill registration

#### Scenario: Symlink-backed skill registration creates a canonical project-local symlink entry
- **WHEN** `/repo/skillset/notes/SKILL.md` exists
- **AND WHEN** an operator runs `houmao-mgr project skills add --name notes --source /repo/skillset/notes --mode symlink`
- **THEN** the project overlay stores `.houmao/content/skills/notes` as a symlink to `/repo/skillset/notes`
- **AND THEN** the registered project skill remains canonical through `.houmao/content/skills/notes`

#### Scenario: Updating a symlink-backed canonical skill to copy mode preserves the caller-owned source
- **WHEN** project skill `notes` is registered in `symlink` mode
- **AND WHEN** `.houmao/content/skills/notes` currently resolves to `/repo/skillset/notes`
- **AND WHEN** an operator runs `houmao-mgr project skills set --name notes --source /repo/skillset/notes --mode copy`
- **THEN** the project overlay stores `.houmao/content/skills/notes/` as a copied directory
- **AND THEN** `/repo/skillset/notes` still exists with its original content intact

#### Scenario: Failed project-skill update does not consume caller-owned source content
- **WHEN** project skill `notes` is registered
- **AND WHEN** `/repo/skillset/notes/SKILL.md` exists before the update starts
- **AND WHEN** `houmao-mgr project skills set --name notes --source /repo/skillset/notes --mode copy` fails after touching only Houmao-managed overlay paths
- **THEN** `/repo/skillset/notes` still exists with its original content intact
- **AND THEN** any cleanup or rollback remains confined to Houmao-managed overlay paths
