## MODIFIED Requirements

### Requirement: `houmao-memory-mgr` treats profile-owned memo seed edits as maintained profile command fields
The packaged `houmao-memory-mgr` skill SHALL treat memo seed options that are part of project profile or raw launch-profile authoring as fields on the maintained profile create, add, or set commands.

The skill SHALL NOT duplicate profile YAML skeletons or full profile command skeletons only to explain memo seed flags.

The skill SHALL NOT pass memo seed fields to `houmao-mgr internals config-drafts generate`, because initial config drafts accept only minimal name/source/credential holes.

Live memory commands such as memo show/set/append and memory page read/write operations SHALL remain direct skill guidance unless a future change adds a matching maintained config surface for those live commands.

#### Scenario: Profile memo seed authoring uses maintained profile mutation
- **WHEN** a user asks to add memo seed text while creating or updating a profile
- **THEN** the skill guidance routes the profile mutation through the matching maintained profile `create`, `add`, or `set` command field
- **AND THEN** memo seed text/file/dir conflicts are handled by that maintained command path rather than by a config-draft intent

#### Scenario: Live memo append remains skill guidance
- **WHEN** a user asks to append to the live memo of an existing agent
- **THEN** the skill may use the maintained live memory command directly
- **AND THEN** it does not require a profile config-draft generation step
