## ADDED Requirements

### Requirement: CLI reference documents launch-profile editing controls
The `houmao-mgr` CLI reference SHALL document patch and replacement controls for reusable launch profiles.

For `project easy profile`, the reference SHALL list `create`, `list`, `get`, `set`, and `remove`, and SHALL document `set` as the patch command that preserves unspecified stored fields.

For `project easy profile create`, the reference SHALL document `--yes` as the non-interactive confirmation for replacing an existing same-lane easy profile, and SHALL state that replacement clears omitted optional fields.

For `project agents launch-profiles add`, the reference SHALL document `--yes` as the non-interactive confirmation for replacing an existing same-lane explicit launch profile, and SHALL state that `launch-profiles set` remains the patch command.

The reference SHALL state that replacement does not cross easy-profile and explicit-launch-profile lanes.

#### Scenario: Reader finds easy-profile set in CLI reference
- **WHEN** a reader looks up `houmao-mgr project easy profile`
- **THEN** the CLI reference lists `set` alongside `create`, `list`, `get`, and `remove`
- **AND THEN** the reference explains that `set` mutates stored future launch defaults rather than one running instance

#### Scenario: Reader finds same-lane replacement guidance
- **WHEN** a reader looks up same-name reusable profile creation
- **THEN** the CLI reference explains when to use `--yes` for same-lane replacement
- **AND THEN** it distinguishes replacement from patching through `set`
