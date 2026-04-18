## ADDED Requirements

### Requirement: Stable promptable error surfaces recover from false active state
For supported live TUI sessions, a stable promptable surface with current recoverable error evidence SHALL be eligible for non-active ready state when independent prompt-ready evidence is present.

If stale or false active evidence leaves `turn.phase=active` while the parsed surface is submit-ready, the surface accepts input, the surface is not editing input, no blocking overlay is present, and the raw surface remains stable for the configured final stable-active recovery dwell, the live tracker SHALL recover the public state to `turn.phase=ready`.

That recovery SHALL NOT settle `last_turn.result=success`, SHALL NOT emit `known_failure`, and SHALL preserve diagnostic evidence that the current surface includes recoverable error context.

#### Scenario: Stable promptable compact-error surface becomes ready
- **WHEN** a supported live Codex TUI session shows a prompt-adjacent recoverable compact/server error
- **AND WHEN** the parsed surface is submit-ready
- **AND WHEN** the tracked surface reports `surface.accepting_input=yes` and `surface.editing_input=no`
- **AND WHEN** stale or false active evidence keeps `turn.phase=active`
- **AND WHEN** the surface remains stable for the configured final stable-active recovery dwell
- **THEN** the live tracked state reports `turn.phase=ready`
- **AND THEN** the live tracked state reports prompt-ready surface posture for prompt admission
- **AND THEN** the live tracked state does not report `last_turn.result=success`

#### Scenario: Promptable error surface does not manufacture terminal success
- **WHEN** a supported live TUI session recovers a stable promptable error surface from false active state
- **THEN** the recovery does not settle the previous turn as successful
- **AND THEN** the recovery does not report the recoverable error as a known failure unless a narrower known-failure signature is present

#### Scenario: Recovery does not apply while prompt readiness is ambiguous
- **WHEN** a supported live TUI session has recoverable error evidence
- **AND WHEN** the prompt surface is not accepting input, is editing input, has a blocking overlay, or lacks submit-ready parsed-surface evidence
- **THEN** the final stable-active recovery path does not publish ready state solely because an error is visible
