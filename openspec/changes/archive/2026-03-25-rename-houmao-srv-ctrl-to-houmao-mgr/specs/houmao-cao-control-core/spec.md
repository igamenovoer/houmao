## MODIFIED Requirements

### Requirement: V1 control-core provider coverage preserves the current pair compatibility launch surface
The control core SHALL preserve the current pair compatibility launch surface accepted by `houmao-mgr launch` and `houmao-mgr cao launch` in v1.

At minimum, the v1 provider-adapter registry SHALL cover these provider identifiers:

- `kiro_cli`
- `claude_code`
- `codex`
- `gemini_cli`
- `kimi_cli`
- `q_cli`

If a later change intentionally retires or narrows that set, it SHALL do so explicitly rather than by leaving a previously supported pair provider unspecified during CAO absorption.

#### Scenario: Current pair compatibility provider identifiers remain launchable in v1
- **WHEN** a supported pair launch flow requests provider `kimi_cli`
- **THEN** the control core resolves that provider through a Houmao-owned provider adapter path
- **AND THEN** the pair does not require external CAO runtime delegation to satisfy that provider selection
