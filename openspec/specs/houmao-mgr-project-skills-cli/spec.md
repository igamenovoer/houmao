# houmao-mgr-project-skills-cli Specification

## Purpose
TBD - created by archiving change source-aware-project-assets. Update Purpose after archive.
## Requirements
### Requirement: `houmao-mgr project skills` manages canonical project-local skill registrations
`houmao-mgr` SHALL expose a `project skills` command family for canonical project-local skill registration under the active project overlay.

At minimum, that family SHALL include:

- `add`
- `set`
- `list`
- `get`
- `remove`

`project skills` SHALL resolve the active project overlay and SHALL manage skill registrations under `.houmao/content/skills/` rather than through `.houmao/agents/skills/`.

`project skills list` and `get` SHALL report each registered skill's canonical project path and storage mode.

#### Scenario: Operator sees the project skill registry verbs
- **WHEN** an operator runs `houmao-mgr project skills --help`
- **THEN** the help output lists `add`, `set`, `list`, `get`, and `remove`
- **AND THEN** the help output presents `project skills` as canonical project-local skill administration

#### Scenario: Skill get reports canonical project skill state
- **WHEN** project skill `notes` is registered
- **AND WHEN** an operator runs `houmao-mgr project skills get --name notes`
- **THEN** the command reports canonical path `.houmao/content/skills/notes`
- **AND THEN** it reports the registered storage mode for that skill

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

### Requirement: Removing a project skill registration protects referenced specialists
`houmao-mgr project skills remove --name <name>` SHALL refuse to remove a registered project skill while that skill is still referenced by one or more persisted specialist definitions or by one or more stored launch-profile registered skill refs.

Launch-profile private path-backed skills SHALL NOT count as project skill registry references because they are not project skill registrations.

Once no persisted specialist and no stored launch profile references that registered project skill by name, `project skills remove` SHALL remove the canonical project skill entry from `.houmao/content/skills/`.

#### Scenario: Removing a specialist-referenced project skill fails clearly
- **WHEN** project skill `notes` is registered
- **AND WHEN** specialist `researcher` still binds project skill `notes`
- **AND WHEN** an operator runs `houmao-mgr project skills remove --name notes`
- **THEN** the command fails clearly
- **AND THEN** the canonical project skill entry remains present

#### Scenario: Removing a launch-profile-referenced project skill fails clearly
- **WHEN** project skill `notes` is registered
- **AND WHEN** launch profile `reviewer-a` stores registered skill ref `notes`
- **AND WHEN** an operator runs `houmao-mgr project skills remove --name notes`
- **THEN** the command fails clearly
- **AND THEN** the canonical project skill entry remains present
- **AND THEN** the error identifies the launch profile reference

#### Scenario: Removing a project skill is allowed when only private path skills share its name
- **WHEN** project skill `notes` is registered
- **AND WHEN** launch profile `reviewer-a` stores private skill source `/repo/profile-skills/notes`
- **AND WHEN** no specialist or launch profile registered skill ref references project skill `notes`
- **AND WHEN** an operator runs `houmao-mgr project skills remove --name notes`
- **THEN** the command removes project skill `notes`
- **AND THEN** launch profile `reviewer-a` still stores its private path-backed skill source
