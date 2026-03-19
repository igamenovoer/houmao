## MODIFIED Requirements

### Requirement: Shadow status classification is output-driven and bounded
The system SHALL compute Claude Code shadow surface assessment from a bounded tail window of the `mode=full` output, and SHALL default to the last 100 lines from the end of the output.

Before classifying state, the system SHALL partition the bounded tail window into a historical zone and an active zone using cursor-anchored prompt boundary detection. State classification SHALL operate on the active zone only. Historical signals above the prompt boundary SHALL NOT contribute to `business_state`, `input_mode`, or `ui_context` classification.
When a visible Claude prompt owns spinner/progress evidence below it, the prompt line SHALL remain inside the active zone so `working + freeform` remains representable.

The Claude surface assessment SHALL classify `business_state` at minimum as:

- `working` when preset-recognized spinner or progress evidence is present in the active zone,
- `awaiting_operator` when trust, approval, onboarding, login, or selection UI requiring operator action is present in the active zone,
- `idle` when the active zone has no stronger working or operator-blocked evidence, and
- `unknown` when output matches a supported Claude output family but the active zone does not satisfy known safe business-state evidence.

The Claude surface assessment SHALL classify `input_mode` at minimum as:

- `freeform` when the active Claude surface safely accepts generic prompt input,
- `modal` when input is constrained to slash-command, trust, approval, or selection UI,
- `closed` when no active editable prompt is safely available, and
- `unknown` when the parser cannot safely determine the active input shape.

The provider SHALL surface `ui_context` through the Claude surface-assessment contract, including the shared `slash_command` context when applicable and Claude-specific contexts such as `trust_prompt`.
Those context details SHALL NOT imply prompt-associated answer extraction.

At minimum, Claude evidence SHALL map to the shared axes like this:

| Active Claude evidence | `business_state` | `input_mode` | `ui_context` |
|---|---|---|---|
| trust, approval, onboarding, or selection surface | `awaiting_operator` | `modal` or `closed` | `trust_prompt` or `selection_menu` |
| active slash-command input surface | `idle` | `modal` | `slash_command` |
| processing evidence with safe generic prompt still open | `working` | `freeform` | `normal_prompt` |
| processing evidence without a safely resolved freeform prompt | `working` | `closed` or `unknown` | `normal_prompt` or `unknown` |
| recovered normal prompt without stronger modal or blocked evidence | `idle` | `freeform` | `normal_prompt` |
| supported but unclassifiable active surface | `unknown` | `unknown` or safely derived known input mode | `unknown` or the strongest safely-derived provider context |

Claude SHALL derive `business_state`, `input_mode`, and `ui_context` from one active-surface evidence pass over the active zone. When blocked or slash-command evidence conflicts with normal prompt markers in the same active zone, the blocked or modal surface SHALL control `input_mode` and `ui_context`, while `business_state` follows the strongest supported business evidence.

#### Scenario: Status checks avoid stale scrollback false positives via zone partitioning
- **WHEN** the tmux scrollback contains an old spinner line from a previous turn in the historical zone
- **AND WHEN** the active zone contains a recovered idle prompt
- **THEN** the system does not classify the terminal as `working` based on stale output
- **AND THEN** zone partitioning ensures historical signals are excluded from classification

#### Scenario: Historical slash-command output does not poison current classification
- **WHEN** the bounded tail window contains a previous `/model` command and its output in the historical zone
- **AND WHEN** the active zone contains a normal idle prompt
- **THEN** the system classifies `ui_context = normal_prompt` rather than `slash_command`

#### Scenario: Working prompt can remain typeable
- **WHEN** the current Claude snapshot shows processing evidence while the active prompt is still open for generic input
- **THEN** the system classifies the snapshot with `business_state = working`
- **AND THEN** the same snapshot may still classify `input_mode = freeform`
- **AND THEN** the active zone boundary remains at the prompt line rather than moving down to the spinner line

#### Scenario: Idle freeform state does not imply authoritative answer association
- **WHEN** the tmux scrollback contains supported Claude output with a recovered normal prompt
- **THEN** the system may classify the snapshot as `business_state = idle` and `input_mode = freeform`
- **AND THEN** that classification does not by itself claim that a visible answer belongs to the most recent prompt submission

#### Scenario: Slash-command UI is surfaced as shared context without implying answer ownership
- **WHEN** a Claude snapshot shows slash-command or command-palette UI in the active zone
- **THEN** the returned Claude surface assessment may use the shared `slash_command` `ui_context`
- **AND THEN** the same snapshot may classify `input_mode = modal` without implying prompt-associated answer extraction
