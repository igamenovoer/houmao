## ADDED Requirements

### Requirement: Compatibility startup waits are config-backed and overrideable
The Houmao-owned CAO-compatible control core SHALL source its synchronous compatibility startup waits and provider warmup delays from supported server configuration rather than from unoverrideable inline operational timing literals.

At minimum, supported server configuration SHALL cover:

- shell-readiness timeout
- shell-readiness polling interval
- provider-readiness timeout
- provider-readiness polling interval
- Codex warmup delay

The default compatibility startup values SHALL be:

- shell-readiness timeout = `10.0` seconds
- shell-readiness polling interval = `0.5` seconds
- provider-readiness timeout = `45.0` seconds
- provider-readiness polling interval = `1.0` seconds
- Codex warmup delay = `2.0` seconds

The Codex warmup delay override SHALL allow `0.0` so operators can disable the delay explicitly.

When operators do not override these values, the control core SHALL preserve the documented defaults above.

#### Scenario: Default server config preserves compatibility startup defaults
- **WHEN** `houmao-server` starts without explicit compatibility startup timeout overrides
- **THEN** compatibility session and terminal creation use the documented default startup waits and warmup delay
- **AND THEN** the server does not require source edits to keep those defaults

#### Scenario: Server override changes compatibility startup timing
- **WHEN** `houmao-server` starts with explicit compatibility startup timing overrides
- **THEN** compatibility session and terminal creation use those configured startup waits instead of inline literals
- **AND THEN** setting the configured Codex warmup delay to `0.0` disables the extra Codex sleep
