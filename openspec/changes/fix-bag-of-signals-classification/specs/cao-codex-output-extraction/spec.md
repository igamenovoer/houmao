## MODIFIED Requirements

### Requirement: Codex shadow surface classification is output-driven and bounded
The system SHALL compute Codex shadow surface state from `mode=full` output using a bounded provider-aware window.

Before classifying state, the system SHALL partition the bounded window into a historical zone and an active zone using cursor-anchored prompt boundary detection. State classification SHALL operate on the active zone only. Historical signals above the prompt boundary SHALL NOT contribute to `business_state`, `input_mode`, or `ui_context` classification.

The Codex surface assessment SHALL classify `business_state` at minimum as:

- `working` when Codex processing evidence is present in the active zone,
- `awaiting_operator` when approval, trust, login, or selection UI requiring operator action is present in the active zone,
- `idle` when the active zone has no stronger working or operator-blocked evidence, and
- `unknown` when output matches a supported Codex output family but the active zone does not satisfy known safe business-state evidence.

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

Codex SHALL derive `business_state`, `input_mode`, and `ui_context` from one active-surface evidence pass over the active zone. When blocked or slash-command evidence conflicts with normal prompt markers in the same active zone, the blocked or modal surface SHALL control `input_mode` and `ui_context`, while `business_state` follows the strongest supported business evidence.

#### Scenario: Historical spinner does not produce false working state via zone partitioning
- **WHEN** the tmux scrollback contains an old processing spinner line in the historical zone
- **AND WHEN** the active zone contains a recovered idle prompt
- **THEN** the system does not classify the terminal as `working` based on stale output

#### Scenario: Historical slash-command output does not poison current Codex classification
- **WHEN** the bounded window contains a previous slash command and its output in the historical zone
- **AND WHEN** the active zone contains a normal idle prompt
- **THEN** the system classifies `ui_context = normal_prompt` rather than `slash_command`

#### Scenario: Working Codex surface can remain freeform
- **WHEN** a Codex snapshot contains processing evidence while the active prompt is still open for generic input
- **THEN** the system classifies the snapshot with `business_state = working`
- **AND THEN** the same snapshot may still classify `input_mode = freeform`

#### Scenario: Idle freeform Codex surface does not imply authoritative answer association
- **WHEN** a Codex snapshot contains input-ready evidence and no stronger operator-blocked or working evidence in the active zone
- **THEN** the system may classify the snapshot as `business_state = idle` and `input_mode = freeform`
- **AND THEN** that classification does not by itself claim that visible assistant text belongs to the most recent prompt submission
