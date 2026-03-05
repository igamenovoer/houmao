## ADDED Requirements

### Requirement: Codex shadow parsing is a functional superset of upstream CAO provider behavior
For CAO provider `codex`, when a session runs in `parsing_mode=shadow_only`, the runtime-owned Codex shadow parser SHALL support at least the same status detection and answer extraction behaviors as the upstream CAO Codex provider parser for all supported Codex output variants.

At minimum, the Codex shadow parser SHALL correctly handle:

- label-style outputs that include `assistant:` markers, and
- interactive/TUI-style outputs that include Codex prompt chrome and bullet-style assistant markers.

#### Scenario: Label-style output is classified and extracted correctly
- **WHEN** `output?mode=full` contains a Codex turn in a label-style format (for example `You ...` followed by `assistant: ...`)
- **AND WHEN** the assistant response appears after the per-turn baseline
- **THEN** shadow status is classified as `completed`
- **AND THEN** extracted answer text includes only the assistant response content (no prompts, spinners, or footer chrome)

#### Scenario: TUI-style output is classified and extracted correctly
- **WHEN** `output?mode=full` contains a Codex turn in an interactive/TUI-style format with prompt/footer chrome and a bullet-style assistant marker
- **AND WHEN** the assistant response appears after the per-turn baseline
- **THEN** shadow status is classified as `completed`
- **AND THEN** extracted answer text includes only the assistant response content (no prompts, spinners, or footer chrome)

### Requirement: Codex shadow parsing detects approval prompts as waiting-user-answer
For Codex in `parsing_mode=shadow_only`, if `output?mode=full` indicates that Codex is waiting for a user approval/selection prompt (for example a yes/no approval question), the system SHALL classify the shadow status as `waiting_user_answer` and SHALL fail the turn with an explicit waiting-user-answer error.

#### Scenario: Approval prompt is surfaced explicitly
- **WHEN** `output?mode=full` contains a Codex approval prompt requiring user action (for example `Approve ... [y/n]`)
- **THEN** the runtime detects `waiting_user_answer`
- **AND THEN** the turn fails with an explicit waiting-user-answer error instead of timing out or being treated as completed

