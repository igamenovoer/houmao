## MODIFIED Requirements

### Requirement: Shadow status classification is output-driven and bounded
The system SHALL compute Claude Code shadow surface assessment from a bounded tail window of the `mode=full` output, and SHALL default to the last 100 lines from the end of the output.

The Claude surface assessment SHALL classify `business_state` at minimum as:

- `working` when preset-recognized spinner or progress evidence is present,
- `awaiting_operator` when trust, approval, onboarding, login, or selection UI requiring operator action is present,
- `idle` when the supported surface has no stronger working or operator-blocked evidence, and
- `unknown` when output matches a supported Claude output family but does not satisfy known safe business-state evidence.

The Claude surface assessment SHALL classify `input_mode` at minimum as:

- `freeform` when the active Claude surface safely accepts generic prompt input,
- `modal` when input is constrained to slash-command, trust, approval, or selection UI,
- `closed` when no active editable prompt is safely available, and
- `unknown` when the parser cannot safely determine the active input shape.

The provider SHALL surface `ui_context` through the Claude surface-assessment contract, including the shared `slash_command` context when applicable and Claude-specific contexts such as `trust_prompt`.
Those context details SHALL NOT imply prompt-associated answer extraction.

#### Scenario: Status checks avoid stale scrollback false positives
- **WHEN** the tmux scrollback contains an old spinner line from a previous turn
- **AND WHEN** the bounded tail window for the current status check does not include that spinner line
- **THEN** the system does not classify the terminal as `working` based on stale output

#### Scenario: Working prompt can remain typeable
- **WHEN** the current Claude snapshot shows processing evidence while the active prompt is still open for generic input
- **THEN** the system classifies the snapshot with `business_state = working`
- **AND THEN** the same snapshot may still classify `input_mode = freeform`

#### Scenario: Idle freeform state does not imply authoritative answer association
- **WHEN** the tmux scrollback contains supported Claude output with a recovered normal prompt
- **THEN** the system may classify the snapshot as `business_state = idle` and `input_mode = freeform`
- **AND THEN** that classification does not by itself claim that a visible answer belongs to the most recent prompt submission

#### Scenario: Slash-command UI is surfaced as shared context without implying answer ownership
- **WHEN** a Claude snapshot shows slash-command or command-palette UI
- **THEN** the returned Claude surface assessment may use the shared `slash_command` `ui_context`
- **AND THEN** the same snapshot may classify `input_mode = modal` without implying prompt-associated answer extraction

### Requirement: Claude shadow status supports explicit unknown classification
For Claude Code in `parsing_mode=shadow_only`, if output matches a supported Claude output family but the parser cannot safely determine business-state evidence or input-mode evidence, the runtime-owned Claude shadow parser SHALL classify the affected shared axis as `unknown` instead of inferring `idle`, `awaiting_operator`, `freeform`, or `closed` without support.

#### Scenario: Recognized Claude output without known business-state evidence is unknown
- **WHEN** `mode=full` output matches a supported Claude variant
- **AND WHEN** the snapshot has no valid processing, operator-blocked, or safe idle-business evidence
- **THEN** Claude shadow `business_state` is `unknown`

#### Scenario: Recognized Claude output with ambiguous input region keeps input mode unknown
- **WHEN** `mode=full` output matches a supported Claude variant
- **AND WHEN** the parser can identify the current business state but cannot safely determine whether the active input region is freeform, modal, or closed
- **THEN** Claude shadow `input_mode` is `unknown`

## REMOVED Requirements

### Requirement: Waiting-user-answer is surfaced as an explicit error
**Reason**: The corrected shared surface contract distinguishes broader operator-blocked surfaces from the narrower legacy `waiting_user_answer` bucket.
**Migration**: Detect blocked Claude surfaces through `business_state = awaiting_operator` and use `ui_context` plus `waiting_user_answer_excerpt` for provider-specific detail.

## ADDED Requirements

### Requirement: Operator-blocked Claude surfaces are surfaced as explicit errors
If the system detects a Claude surface with `business_state = awaiting_operator` during a turn, it SHALL fail the turn with an explicit blocked-surface error and include an ANSI-stripped excerpt when available.

#### Scenario: Trust prompt is surfaced explicitly as an operator-blocked error
- **WHEN** `mode=full` contains a Claude trust or approval prompt requiring operator action
- **THEN** the runtime detects `business_state = awaiting_operator`
- **AND THEN** the turn fails with an explicit blocked-surface error instead of timing out or being treated as completed
