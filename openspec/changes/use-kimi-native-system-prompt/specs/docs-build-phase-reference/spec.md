## RENAMED Requirements

- FROM: `Build-phase Kimi references document current system-prompt caveat`
- TO: `Build-phase Kimi references document the native system-prompt contract`

## MODIFIED Requirements

### Requirement: Build-phase Kimi references document the native system-prompt contract
Build-phase reference pages that describe Kimi launch policy SHALL name Kimi Code 0.34.0 as the minimum maintained release and SHALL state that earlier versions are unsupported and later versions have no upper support limit.

The launch-policy reference SHALL explain that Houmao writes the complete effective role prompt to the managed `$KIMI_CODE_HOME/SYSTEM.md`, preserves Kimi's built-in instructions through `${base_prompt}`, uses the v2 engine, and rejects higher-priority agent overrides that would bypass the file.

The reference SHALL preserve accurate Kimi skill projection, prompt-mode, TUI unattended, and versioned launch-policy details. It SHALL contain no managed auto-skill or manual role-bootstrap guidance.

#### Scenario: Reader sees current Kimi launch-policy version
- **WHEN** a reader opens `docs/reference/build-phase/launch-policy.md`
- **THEN** Kimi launch-policy guidance names Kimi Code 0.34.0 as the minimum maintained release with no upper limit
- **AND THEN** it states that Kimi releases before 0.34.0 are unsupported

#### Scenario: Reader sees native prompt projection without workaround guidance
- **WHEN** a reader reviews Kimi role-prompt build behavior
- **THEN** the docs describe managed `SYSTEM.md` projection, built-in prompt preservation, and prompt-bypass validation
- **AND THEN** they do not instruct the reader to invoke a role-delivery skill or send a bootstrap prompt
