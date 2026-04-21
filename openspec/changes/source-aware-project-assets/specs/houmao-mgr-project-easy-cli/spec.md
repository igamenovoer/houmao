## ADDED Requirements

### Requirement: Easy-specialist flows do not auto-upgrade legacy specialist metadata
Maintained `houmao-mgr project easy ...` specialist flows SHALL NOT silently import or rewrite legacy `.houmao/easy/specialists/*.toml` metadata during ordinary specialist inspection, mutation, or launch preparation.

When the selected project overlay still depends on legacy easy-specialist metadata that requires explicit migration, the command SHALL fail clearly and direct the operator to `houmao-mgr project migrate`.

#### Scenario: Specialist get rejects legacy specialist metadata with migration guidance
- **WHEN** the selected project overlay still contains one legacy `.houmao/easy/specialists/researcher.toml` specialist definition that has not been migrated
- **AND WHEN** an operator runs `houmao-mgr project easy specialist get --name researcher`
- **THEN** the command fails clearly
- **AND THEN** the diagnostic directs the operator to `houmao-mgr project migrate`

### Requirement: `project easy specialist create` can bind registered project skills
`houmao-mgr project easy specialist create` SHALL support binding existing registered project skills by name at create time.

Repeatable `--skill <name>` SHALL bind one existing registered project skill to the created specialist.

Repeatable `--with-skill <dir>` MAY remain as a convenience path, but its maintained meaning SHALL be to register or update one canonical project skill entry and then bind that registered skill to the created specialist.

The created specialist SHALL persist skill relationships by registered project skill name rather than by treating an imported directory path as specialist-owned canonical storage.

#### Scenario: Specialist create binds one existing registered project skill
- **WHEN** project skill `notes` is already registered
- **AND WHEN** an operator runs `houmao-mgr project easy specialist create --name researcher --tool codex --api-key sk-test --skill notes`
- **THEN** specialist `researcher` stores a binding to registered project skill `notes`
- **AND THEN** the specialist does not create a second canonical project-owned copy of that skill outside the project skill registry

### Requirement: Specialist get reports registry-backed skill references
`houmao-mgr project easy specialist get --name <specialist>` SHALL report each bound project skill by registered name.

When the bound project skill is registered in `copy` or `symlink` mode, `specialist get` SHALL report that mode and the canonical project skill path under `.houmao/content/skills/`.

#### Scenario: Specialist get reports canonical project skill references
- **WHEN** specialist `researcher` binds project skill `notes`
- **AND WHEN** `notes` is registered in `symlink` mode
- **AND WHEN** an operator runs `houmao-mgr project easy specialist get --name researcher`
- **THEN** the command reports bound project skill `notes`
- **AND THEN** it reports canonical path `.houmao/content/skills/notes` and mode `symlink`

## MODIFIED Requirements

### Requirement: Specialist set supports targeted skill binding edits
`houmao-mgr project easy specialist set --name <specialist>` SHALL allow operators to edit specialist skill bindings without respecifying the entire specialist.

Repeatable `--add-skill <name>` SHALL bind an existing registered project skill by name.

Repeatable `--with-skill <dir>` SHALL register or update one canonical project skill entry using the provided skill directory and SHALL bind that registered skill to the specialist.

Repeatable `--remove-skill <name>` SHALL remove the named skill binding from the specialist when present.

`--clear-skills` SHALL clear all skill bindings from the specialist.

Removing or clearing skill bindings SHALL NOT delete shared skill content only because one specialist no longer references it.

#### Scenario: Specialist set registers and adds a skill
- **WHEN** specialist `researcher` exists without skill `notes-skill`
- **AND WHEN** `/tmp/notes-skill/SKILL.md` exists
- **AND WHEN** an operator runs `houmao-mgr project easy specialist set --name researcher --with-skill /tmp/notes-skill`
- **THEN** specialist `researcher` stores skill binding `notes-skill`
- **AND THEN** the canonical project skill entry exists at `.houmao/content/skills/notes-skill`

#### Scenario: Specialist set removes one binding without deleting shared skill content
- **WHEN** specialist `researcher` and specialist `reviewer` both reference skill `notes`
- **AND WHEN** an operator runs `houmao-mgr project easy specialist set --name researcher --remove-skill notes`
- **THEN** specialist `researcher` no longer stores skill binding `notes`
- **AND THEN** skill content for `notes` remains available for specialist `reviewer`
