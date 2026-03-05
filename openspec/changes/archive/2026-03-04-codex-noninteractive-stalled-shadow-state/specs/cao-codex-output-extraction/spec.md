## ADDED Requirements

### Requirement: Codex shadow status supports explicit unknown classification
For Codex in `parsing_mode=shadow_only`, if output matches a supported Codex output family but does not satisfy known status evidence for `processing`, `waiting_user_answer`, `completed`, or `idle`, the runtime-owned Codex shadow parser SHALL classify the snapshot status as `unknown`.

#### Scenario: Recognized Codex output without known status evidence is unknown
- **WHEN** `mode=full` output matches a supported Codex variant
- **AND WHEN** the snapshot has no valid completion, waiting-user-answer, idle-prompt, or processing evidence
- **THEN** Codex shadow status is `unknown`

### Requirement: Codex unknown status can transition to stalled after configurable timeout
For Codex in `parsing_mode=shadow_only`, runtime SHALL transition from `unknown` to `stalled` when continuous unknown duration reaches configured timeout.

#### Scenario: Unknown reaches stalled threshold
- **WHEN** Codex shadow polling remains in `unknown` continuously
- **AND WHEN** elapsed unknown duration reaches `unknown_to_stalled_timeout_seconds`
- **THEN** runtime shadow lifecycle status becomes `stalled`

### Requirement: Codex stalled state supports configurable terminality and recovery
For Codex stalled handling:
- if `stalled_is_terminal=true`, runtime SHALL fail the turn with explicit stalled diagnostics,
- if `stalled_is_terminal=false`, runtime SHALL keep polling and MAY recover to a known status automatically.

#### Scenario: Non-terminal stalled recovers to completed
- **WHEN** Codex runtime is in non-terminal `stalled`
- **AND WHEN** later `mode=full` output includes valid Codex completion evidence
- **THEN** runtime transitions back to known status processing and completes turn extraction without forcing immediate failure at stalled entry

#### Scenario: Terminal stalled fails turn immediately
- **WHEN** Codex runtime reaches `stalled`
- **AND WHEN** `stalled_is_terminal=true`
- **THEN** runtime returns an explicit stalled-state failure with parser-family context and tail excerpt
