## ADDED Requirements

### Requirement: Cleanup commands keep destructive filesystem actions contained to owned artifacts
`houmao-mgr` cleanup commands SHALL delete only owned runtime, session, log, mailbox, or registry artifacts selected through a validated cleanup authority.

If cleanup resolution determines that the selected artifact path escapes the applicable owned root, the command SHALL fail clearly before mutating the filesystem.

If the selected artifact path itself is a symlink, cleanup SHALL treat that symlink as the artifact and SHALL NOT recursively delete its target.

#### Scenario: Cleanup rejects an escaped owned-root mutation target
- **WHEN** cleanup resolution produces one candidate artifact path that is not contained within the applicable owned runtime or registry root
- **THEN** the cleanup command fails clearly before mutating the filesystem

#### Scenario: Cleanup removes a symlink artifact without deleting its target
- **WHEN** one cleanup command is authorized to remove one owned artifact path
- **AND WHEN** that artifact path currently exists as a symlink to a directory outside the owned root
- **THEN** cleanup removes only the symlink artifact path
- **AND THEN** it does not recursively delete the symlink target
