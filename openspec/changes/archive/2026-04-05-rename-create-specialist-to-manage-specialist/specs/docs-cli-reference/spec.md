## ADDED Requirements

### Requirement: System-skills reference documents the renamed specialist-management skill
The CLI reference page `docs/reference/cli/system-skills.md` SHALL describe the current project-easy packaged skill as `houmao-manage-specialist`.

That page SHALL describe the packaged skill as the Houmao-owned specialist-management entry point for `project easy specialist create|list|get|remove`.

The page SHALL describe the top-level packaged skill page as an index/router and SHALL state that `project easy instance launch` remains outside that packaged skill scope.

The page SHALL NOT continue to describe `houmao-create-specialist` as the active packaged project-easy skill.

#### Scenario: Reader sees the renamed packaged skill in system-skills reference
- **WHEN** a reader opens `docs/reference/cli/system-skills.md`
- **THEN** the page identifies `houmao-manage-specialist` as the packaged project-easy skill
- **AND THEN** it describes that skill as covering `create`, `list`, `get`, and `remove`

#### Scenario: Reader does not see the stale create-only packaged skill name
- **WHEN** a reader opens `docs/reference/cli/system-skills.md`
- **THEN** the page does not present `houmao-create-specialist` as the current packaged specialist-management skill
- **AND THEN** it explains that easy-instance launch remains outside the packaged skill scope
