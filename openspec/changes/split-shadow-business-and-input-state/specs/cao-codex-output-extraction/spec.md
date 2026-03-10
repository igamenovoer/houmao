## MODIFIED Requirements

### Requirement: Codex shadow surface classification is output-driven and bounded
The system SHALL compute Codex shadow surface state from `mode=full` output using a bounded provider-aware window.

The Codex surface assessment SHALL classify `business_state` at minimum as:

- `working` when Codex processing evidence is present,
- `awaiting_operator` when approval, trust, login, or selection UI requiring operator action is present,
- `idle` when the supported surface has no stronger working or operator-blocked evidence, and
- `unknown` when output matches a supported Codex output family but does not satisfy known safe business-state evidence.

The Codex surface assessment SHALL classify `input_mode` at minimum as:

- `freeform` when the active Codex surface safely accepts generic prompt input,
- `modal` when input is constrained to slash-command, approval, or selection UI,
- `closed` when no active editable prompt is safely available, and
- `unknown` when the parser cannot safely determine the active input shape.

The provider SHALL surface `ui_context` through the Codex surface-assessment contract, including the shared `slash_command` context when applicable and Codex-specific contexts such as `approval_prompt`.

At minimum, Codex evidence SHALL map to the shared axes like this:

| Active Codex evidence | `business_state` | `input_mode` | `ui_context` |
|---|---|---|---|
| approval, trust, login, or selection surface | `awaiting_operator` | `modal` or `closed` | `approval_prompt` or `selection_menu` |
| active slash-command input surface | `idle` | `modal` | `slash_command` |
| processing evidence with safe generic prompt still open | `working` | `freeform` | `normal_prompt` |
| processing evidence without a safely resolved freeform prompt | `working` | `closed` or `unknown` | `normal_prompt` or `unknown` |
| recovered normal prompt without stronger modal or blocked evidence | `idle` | `freeform` | `normal_prompt` |
| supported but unclassifiable active surface | `unknown` | `unknown` or safely derived known input mode | `unknown` or the strongest safely-derived provider context |

Codex SHALL derive `business_state`, `input_mode`, and `ui_context` from one active-surface evidence pass. When blocked or slash-command evidence conflicts with normal prompt markers in the same bounded window, the blocked or modal surface SHALL control `input_mode` and `ui_context`, while `business_state` follows the strongest supported business evidence.

#### Scenario: Working Codex surface can remain freeform
- **WHEN** a Codex snapshot contains processing evidence while the active prompt is still open for generic input
- **THEN** the system classifies the snapshot with `business_state = working`
- **AND THEN** the same snapshot may still classify `input_mode = freeform`

#### Scenario: Idle freeform Codex surface does not imply authoritative answer association
- **WHEN** a Codex snapshot contains input-ready evidence and no stronger operator-blocked or working evidence
- **THEN** the system may classify the snapshot as `business_state = idle` and `input_mode = freeform`
- **AND THEN** that classification does not by itself claim that visible assistant text belongs to the most recent prompt submission

#### Scenario: Codex slash-command UI is surfaced through the shared context vocabulary
- **WHEN** a Codex snapshot shows slash-command or command-palette style UI
- **THEN** the returned Codex surface assessment may use the shared `slash_command` `ui_context`
- **AND THEN** the same snapshot may classify `input_mode = modal` while keeping Codex-specific contexts such as `approval_prompt` available for Codex-specific UI states

### Requirement: Codex shadow status supports explicit unknown classification
For Codex in `parsing_mode=shadow_only`, if output matches a supported Codex output family but the parser cannot safely determine business-state evidence or input-mode evidence, the runtime-owned Codex shadow parser SHALL classify the affected shared axis as `unknown` instead of inferring `idle`, `awaiting_operator`, `freeform`, or `closed` without support.

#### Scenario: Recognized Codex output without known business-state evidence is unknown
- **WHEN** `mode=full` output matches a supported Codex variant
- **AND WHEN** the snapshot has no valid processing, operator-blocked, or safe idle-business evidence
- **THEN** Codex shadow `business_state` is `unknown`

#### Scenario: Recognized Codex output with ambiguous input region keeps input mode unknown
- **WHEN** `mode=full` output matches a supported Codex variant
- **AND WHEN** the parser can identify the current business state but cannot safely determine whether the active input region is freeform, modal, or closed
- **THEN** Codex shadow `input_mode` is `unknown`

## REMOVED Requirements

### Requirement: Codex waiting-user-answer is explicit in shadow mode
**Reason**: The corrected shared surface contract distinguishes broader operator-blocked surfaces from the narrower legacy `waiting_user_answer` bucket.
**Migration**: Detect blocked Codex surfaces through `business_state = awaiting_operator` and use `ui_context` plus `operator_blocked_excerpt` for provider-specific detail.

## ADDED Requirements

### Requirement: Operator-blocked Codex surfaces are surfaced as explicit errors
For Codex in `parsing_mode=shadow_only`, if `output?mode=full` indicates a surface with `business_state = awaiting_operator`, the runtime SHALL fail the turn with an explicit blocked-surface error instead of treating the turn as completed or waiting indefinitely.

#### Scenario: Approval prompt is surfaced explicitly as an operator-blocked error
- **WHEN** `output?mode=full` contains a Codex approval prompt requiring user action
- **THEN** the runtime detects `business_state = awaiting_operator`
- **AND THEN** the turn fails with an explicit blocked-surface error instead of timing out or being treated as completed
