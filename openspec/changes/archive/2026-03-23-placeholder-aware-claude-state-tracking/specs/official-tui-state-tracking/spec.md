## ADDED Requirements

### Requirement: Styled placeholder prompt text does not imply editing input
For supported interactive TUI surfaces, the tracked state SHALL treat visible placeholder or suggestion text on the prompt line as non-editing posture when the selected profile classifies that prompt payload as placeholder content rather than user-authored draft input.

The system SHALL continue to report real draft prompt content as `surface.editing_input=yes` when the selected profile classifies the same prompt region as active draft input.

#### Scenario: Claude startup suggestion remains non-editing
- **WHEN** Claude Code renders styled suggestion text on the visible `❯` prompt line before the operator types anything
- **THEN** the tracked state reports `surface.accepting_input=yes`
- **AND THEN** the tracked state reports `surface.ready_posture=yes`
- **AND THEN** the tracked state reports `surface.editing_input=no`
- **AND THEN** the tracked state reports `turn.phase=ready`

#### Scenario: Real Claude draft text still reports editing
- **WHEN** the operator types real draft text into the Claude prompt area
- **AND WHEN** the selected Claude profile classifies the visible prompt payload as draft input rather than placeholder content
- **THEN** the tracked state reports `surface.editing_input=yes`
- **AND THEN** the tracked state does not downgrade that draft to placeholder solely because the prompt line contains styling
