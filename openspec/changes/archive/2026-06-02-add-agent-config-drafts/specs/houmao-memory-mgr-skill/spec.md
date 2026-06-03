## REMOVED Requirements

### Requirement: `houmao-memory-mgr` treats profile-owned memo seed flags as command-template fields
**Reason**: Profile-owned memo seed authoring belongs to the profile config document shape once config drafts are available; requiring command-template field inspection for profile memo seed edits keeps the agent on the high-token CLI option schema path.

**Migration**: Use the matching profile config draft for profile-owned memo seed authoring, and keep live memory commands as direct skill guidance.

## ADDED Requirements

### Requirement: `houmao-memory-mgr` treats profile-owned memo seed fields as config-draft fields
The packaged `houmao-memory-mgr` skill SHALL treat memo seed options that are part of easy profile or raw launch-profile authoring as fields represented by the matching profile config draft when that draft exists.

The skill SHALL NOT duplicate profile YAML skeletons or profile command skeletons only to explain memo seed fields.

Live memory commands such as memo show/set/append and memory page read/write operations SHALL remain direct skill guidance unless a future change adds a matching maintained config or command-template surface for those live commands.

#### Scenario: Profile memo seed authoring uses profile config draft
- **WHEN** a user asks to add memo seed text while preparing or updating a profile document
- **THEN** the skill guidance routes the profile document shape through the matching config draft
- **AND THEN** memo seed text/file/dir shape is treated as part of the generated profile draft rather than a separate command-template schema lookup

#### Scenario: Live memo append remains skill guidance
- **WHEN** a user asks to append to the live memo of an existing agent
- **THEN** the skill may use the maintained live memory command directly
- **AND THEN** it does not require a profile config-draft generation step
