# Static System-Skill Collection Delta

## ADDED Requirements

### Requirement: Shared routines own the declared parent-scoped children
The packaged manifest SHALL declare the current shared child inventory. The directories directly under `houmao-shared-routines/subskills/` SHALL match that inventory exactly. The current inventory SHALL contain eighteen children, including `houmao-agent-access` and `houmao-agent-files`. Each child SHALL own a `SKILL-MAIN.md` entrypoint.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

Each direct child SHALL contain only its role-canonical entrypoint filename. The Pro and Lite loop skills SHALL be public siblings outside the shared tree.

#### Scenario: Current shared tree matches its declaration
- **WHEN** Houmao validates the current shared source tree
- **THEN** the exact child directories match the manifest
- **AND THEN** the retained shared routines and both new children are present

#### Scenario: Exact entrypoint scanner traverses shared routines
- **WHEN** a recursive scanner registers only exact `SKILL.md` filenames
- **THEN** it registers `houmao-shared-routines` as one standalone skill
- **AND THEN** the scan returns only that root for the complete shared tree

## REMOVED Requirements

### Requirement: Shared routines own sixteen parent-scoped children
**Reason**: Retained access and versioned file edits add two shared children.

**Migration**: Use the current manifest-declared inventory and the existing parent-scoped entrypoint convention.
