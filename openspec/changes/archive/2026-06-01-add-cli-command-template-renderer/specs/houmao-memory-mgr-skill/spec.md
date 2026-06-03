## ADDED Requirements

### Requirement: `houmao-memory-mgr` treats profile-owned memo seed flags as command-template fields
The packaged `houmao-memory-mgr` skill SHALL treat memo seed options that are part of easy profile or raw launch-profile authoring as fields owned by those profile command templates.

The skill SHALL NOT duplicate profile command skeletons only to explain memo seed flags.

Live memory commands such as memo show/set/append and memory page read/write operations SHALL remain direct skill guidance unless this change adds matching command-template entries for those maintained `houmao-mgr` surfaces.

#### Scenario: Profile memo seed authoring uses profile template
- **WHEN** a user asks to add memo seed text while creating or updating a profile
- **THEN** the skill guidance routes the profile mutation through the matching profile command template
- **AND THEN** memo seed text/file/dir conflicts are handled by that template

#### Scenario: Live memo append remains skill guidance
- **WHEN** a user asks to append to the live memo of an existing agent
- **THEN** the skill may use the maintained live memory command directly
- **AND THEN** it does not require a profile command-template render
