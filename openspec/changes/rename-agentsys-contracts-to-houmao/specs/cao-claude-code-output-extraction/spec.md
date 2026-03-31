## MODIFIED Requirements

### Requirement: Claude Code parsing preset is resolved by version
The system SHALL resolve a single Claude Code parsing preset using this priority order:
1. `HOUMAO_CAO_CLAUDE_CODE_VERSION` environment variable when set and non-empty,
2. auto-detected Claude Code version from the scrollback banner, and
3. the latest known preset.

If version detection fails entirely, the system SHALL use the latest known preset. Operators MAY set `HOUMAO_CAO_CLAUDE_CODE_VERSION` to pin a specific preset when the latest patterns do not match.

#### Scenario: Env override pins the parsing preset
- **GIVEN** `HOUMAO_CAO_CLAUDE_CODE_VERSION=2.1.62` is set for the runtime process
- **WHEN** the system evaluates Claude Code output for shadow status or extraction
- **THEN** it uses the 2.1.62 parsing preset regardless of what the scrollback banner reports

