## MODIFIED Requirements

### Requirement: Specialist set supports targeted skill binding edits
`houmao-mgr project easy specialist set --name <specialist>` SHALL allow operators to edit specialist skill bindings without respecifying the entire specialist.

Repeatable `--add-skill <name>` SHALL bind an existing registered project skill by name.

Repeatable `--with-skill <dir>` SHALL register or update one canonical project skill entry using the provided skill directory and SHALL bind that registered skill to the specialist.

For `--with-skill <dir>`, the provided directory SHALL be treated as caller-owned input rather than Houmao-managed content.

`project easy specialist set --with-skill` SHALL NOT delete, move, rewrite, or partially consume the provided source directory, even when the underlying project skill registration refreshes an existing canonical entry or fails partway through.

Repeatable `--remove-skill <name>` SHALL remove the named skill binding from the specialist when present.

`--clear-skills` SHALL clear all skill bindings from the specialist.

Removing or clearing skill bindings SHALL NOT delete shared skill content only because one specialist no longer references it.

#### Scenario: Specialist set registers and adds a skill
- **WHEN** specialist `researcher` exists without skill `notes-skill`
- **AND WHEN** `/tmp/notes-skill/SKILL.md` exists
- **AND WHEN** an operator runs `houmao-mgr project easy specialist set --name researcher --with-skill /tmp/notes-skill`
- **THEN** specialist `researcher` stores skill binding `notes-skill`
- **AND THEN** the canonical project skill entry exists at `.houmao/content/skills/notes-skill`

#### Scenario: Specialist set with-skill preserves caller-owned source content
- **WHEN** specialist `researcher` exists without skill `notes-skill`
- **AND WHEN** project skill `notes-skill` is already registered through a symlink-backed canonical entry
- **AND WHEN** `/repo/skillset/notes-skill/SKILL.md` exists before the command starts
- **AND WHEN** an operator runs `houmao-mgr project easy specialist set --name researcher --with-skill /repo/skillset/notes-skill`
- **THEN** specialist `researcher` stores skill binding `notes-skill`
- **AND THEN** `/repo/skillset/notes-skill` still exists with its original content intact

#### Scenario: Specialist set removes one binding without deleting shared skill content
- **WHEN** specialist `researcher` and specialist `reviewer` both reference skill `notes`
- **AND WHEN** an operator runs `houmao-mgr project easy specialist set --name researcher --remove-skill notes`
- **THEN** specialist `researcher` no longer stores skill binding `notes`
- **AND THEN** skill content for `notes` remains available for specialist `reviewer`

### Requirement: `project easy specialist create` can bind registered project skills
`houmao-mgr project easy specialist create` SHALL support binding existing registered project skills by name at create time.

Repeatable `--skill <name>` SHALL bind one existing registered project skill to the created specialist.

Repeatable `--with-skill <dir>` MAY remain as a convenience path, but its maintained meaning SHALL be to register or update one canonical project skill entry and then bind that registered skill to the created specialist.

For `--with-skill <dir>`, the provided directory SHALL be treated as caller-owned input rather than specialist-owned or Houmao-managed content.

`project easy specialist create --with-skill` SHALL NOT delete, move, rewrite, or partially consume the provided source directory, even when the underlying project skill registration refreshes an existing canonical entry or the create command later fails.

The created specialist SHALL persist skill relationships by registered project skill name rather than by treating an imported directory path as specialist-owned canonical storage.

#### Scenario: Specialist create binds one existing registered project skill
- **WHEN** project skill `notes` is already registered
- **AND WHEN** an operator runs `houmao-mgr project easy specialist create --name researcher --tool codex --api-key sk-test --skill notes`
- **THEN** specialist `researcher` stores a binding to registered project skill `notes`
- **AND THEN** the specialist does not create a second canonical project-owned copy of that skill outside the project skill registry

#### Scenario: Specialist create with-skill preserves caller-owned source content
- **WHEN** `/repo/skillset/notes/SKILL.md` exists before the command starts
- **AND WHEN** project skill `notes` is already registered through a symlink-backed canonical entry
- **AND WHEN** an operator runs `houmao-mgr project easy specialist create --name researcher --tool codex --api-key sk-test --with-skill /repo/skillset/notes`
- **THEN** specialist `researcher` stores a binding to registered project skill `notes`
- **AND THEN** `/repo/skillset/notes` still exists with its original content intact
