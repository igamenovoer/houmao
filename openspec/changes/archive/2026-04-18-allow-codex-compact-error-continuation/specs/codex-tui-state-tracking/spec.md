## ADDED Requirements

### Requirement: Prompt-adjacent compact errors are recoverable degraded context
The `codex_tui` profile SHALL classify a current prompt-adjacent compact/server error cell as recoverable degraded-context evidence rather than mandatory reset evidence.

When the current prompt-adjacent compact/server error cell is present, the profile SHALL expose current-error evidence for the current turn and SHALL prevent success candidacy for that surface.

When the current prompt-adjacent compact/server error cell is present and the current composer facts otherwise indicate prompt readiness, the profile SHALL preserve prompt readiness instead of forcing the input surface to unknown or active solely because of that error.

The profile SHALL derive this compact/server error classification from the bounded prompt-adjacent prompt region. It SHALL NOT classify old compact/server error text from arbitrary historical scrollback as current degraded-context evidence.

The profile SHALL NOT use a public state name that implies mandatory reset for this recoverable condition.

#### Scenario: Compact error near prompt keeps promptable degraded state
- **WHEN** the current Codex TUI snapshot shows a compact/server red error cell in the bounded prompt-adjacent region
- **AND WHEN** the prompt is visible, accepting input, not editing input, not blocked by an overlay, and has no current active-turn evidence
- **THEN** the `codex_tui` profile exposes current-error evidence for the current turn
- **AND THEN** the profile blocks success candidacy for that turn
- **AND THEN** the profile preserves prompt-ready input posture for downstream tracked-state reduction
- **AND THEN** the profile exposes recoverable degraded-context evidence without requiring a context reset

#### Scenario: Historical compact error does not degrade current prompt state
- **WHEN** a Codex TUI snapshot contains an older compact/server error cell in long scrollback above the current prompt area
- **AND WHEN** the bounded prompt-adjacent region near the current prompt does not contain a compact/server error cell
- **THEN** the `codex_tui` profile does not expose degraded-context evidence from that historical error
- **AND THEN** the profile does not expose current-error evidence solely because that historical error remains visible

#### Scenario: Generic prompt-adjacent error remains a success blocker only
- **WHEN** the current Codex TUI snapshot shows a prompt-adjacent generic red error cell that does not match the compact/server degraded-context signature
- **THEN** the `codex_tui` profile exposes current-error evidence for the current turn
- **AND THEN** the profile blocks success candidacy for that turn
- **AND THEN** the profile does not expose recoverable compact/server degraded-context evidence
