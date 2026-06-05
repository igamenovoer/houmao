## ADDED Requirements

### Requirement: Claude style-classified suggestions preserve ready tracked state

For supported Claude Code TUI sessions, when the selected tracked-TUI profile classifies the current prompt payload as ghost suggestion or placeholder content rather than user-authored draft input, the authoritative tracked state SHALL treat the prompt as non-editing.

When no stronger active-turn evidence, modal overlay, blocked surface, or instability rule applies, that same snapshot SHALL remain eligible for ready tracked state with `surface.accepting_input=yes`, `surface.editing_input=no`, `surface.ready_posture=yes`, and `turn.phase=ready`.

The tracked state SHALL NOT depend on exact ghost-suggestion wording to produce that ready posture. It SHALL depend on the selected profile's style-based prompt classification.

Real user-authored draft input SHALL continue to report `surface.editing_input=yes` and SHALL NOT be downgraded to non-editing solely because Claude also displays a styled suggestion suffix.

#### Scenario: Claude ghost suggestion is non-editing

- **WHEN** the current Claude Code prompt line contains only style-classified ghost suggestion payload
- **AND WHEN** no current active-turn evidence or modal overlay is visible
- **THEN** the tracked state reports `surface.accepting_input=yes`
- **AND THEN** the tracked state reports `surface.editing_input=no`
- **AND THEN** the tracked state reports `surface.ready_posture=yes`
- **AND THEN** the tracked state reports `turn.phase=ready`

#### Scenario: Suggestion wording does not drive tracked readiness

- **WHEN** two Claude Code snapshots show different ghost-suggestion text with the same profile-recognized suggestion styling
- **THEN** both snapshots derive non-editing prompt posture from style-based classification
- **AND THEN** the tracked state does not require either suggestion text to match a fixed phrase

#### Scenario: Real draft still blocks ready editing posture

- **WHEN** the operator has typed real draft input into the Claude Code prompt area
- **THEN** the tracked state reports `surface.editing_input=yes`
- **AND THEN** it does not classify that prompt as non-editing solely because a suggestion-style suffix is also visible
