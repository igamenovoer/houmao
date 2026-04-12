## ADDED Requirements

### Requirement: CLI reference documents specialist editing controls
The `houmao-mgr` CLI reference SHALL document patch and replacement controls for reusable easy specialists.

For `project easy specialist`, the reference SHALL list `create`, `list`, `get`, `set`, and `remove`, and SHALL document `set` as the patch command that preserves unspecified stored specialist fields.

For `project easy specialist create`, the reference SHALL document `--yes` as the non-interactive confirmation for replacing an existing same-name specialist, and SHALL state that replacement uses create semantics where omitted optional fields may be cleared.

The reference SHALL state that `specialist set` updates the reusable specialist source for future launches and does not mutate running managed agents in place.

#### Scenario: Reader finds specialist set in CLI reference
- **WHEN** a reader looks up `houmao-mgr project easy specialist`
- **THEN** the CLI reference lists `set` alongside `create`, `list`, `get`, and `remove`
- **AND THEN** the reference explains that `set` mutates stored future source defaults rather than one running instance

#### Scenario: Reader finds specialist replacement guidance
- **WHEN** a reader looks up same-name specialist creation
- **THEN** the CLI reference explains when to use `--yes` for replacement
- **AND THEN** it distinguishes replacement from patching through `set`
