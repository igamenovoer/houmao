## ADDED Requirements

### Requirement: Easy-specialist guide documents project skill registration and name-based binding
The easy-specialist guide SHALL explain that project-local custom skills are registered first and then bound to specialists by name.

At minimum, the guide SHALL document:

- `houmao-mgr project skills add --name <name> --source <dir> --mode copy|symlink`
- `houmao-mgr project easy specialist create --skill <name>`
- `houmao-mgr project easy specialist set --add-skill <name>`

If the guide documents `--with-skill <dir>`, it SHALL describe that flag as a convenience path that registers or updates the canonical project skill entry before binding the resulting registered skill to the specialist.

The guide SHALL explain that canonical project skill storage lives under `.houmao/content/skills/`, while `.houmao/agents/skills/` is derived projection only.

The guide SHALL direct existing users with older easy-specialist project metadata to `houmao-mgr project migrate` instead of implying that `project easy` commands silently upgrade those specialist definitions in place.

#### Scenario: Reader learns to register a skill before binding it to a specialist
- **WHEN** a reader follows the easy-specialist authoring guide
- **THEN** the guide shows `project skills add` before `project easy specialist create --skill <name>` or `set --add-skill <name>`
- **AND THEN** the guide does not present `.houmao/agents/skills/` as the canonical skill authoring root

#### Scenario: Reader sees explicit migration guidance for older easy-specialist state
- **WHEN** a reader already has one older project overlay with legacy easy-specialist metadata
- **THEN** the guide directs them to `houmao-mgr project migrate`
- **AND THEN** the guide does not imply that ordinary `project easy` commands will silently upgrade that metadata
