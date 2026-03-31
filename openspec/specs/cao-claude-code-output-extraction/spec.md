# cao-claude-code-output-extraction Specification

## Purpose
Define requirements for Claude Code CAO output parsing, versioned preset resolution, and runtime-owned shadow extraction behavior.
## Requirements
### Requirement: Claude Code CAO output is parsed by a runtime shadow provider
For CAO provider `claude_code`, when a session runs in `parsing_mode=shadow_only`, the system SHALL treat CAO as a transport layer and derive both:
1) Claude Code surface state, and
2) projected dialog content,
from `GET /terminals/{terminal_id}/output?mode=full`.

In `parsing_mode=shadow_only`, the system SHALL NOT rely on:
- CAO `GET /terminals/{terminal_id}` `status` for turn gating, or
- CAO `mode=last` output for dialog projection.

In `parsing_mode=shadow_only`, the core Claude shadow parser SHALL NOT promise prompt-associated final answer extraction from `mode=full`.

In `parsing_mode=cao_only`, the runtime SHALL NOT invoke Claude shadow parsing for turn gating or projection.
In `parsing_mode=cao_only`, Claude turns use the CAO-native path: readiness/completion is derived from CAO terminal status and answer extraction uses `output?mode=last`.

#### Scenario: Shadow mode keeps Claude state/projection runtime-owned
- **WHEN** a Claude CAO-backed session runs with `parsing_mode=shadow_only`
- **THEN** readiness/completion is derived from runtime-owned Claude surface assessment over `mode=full`
- **AND THEN** caller-facing dialog projection is derived from runtime-owned Claude projection over `mode=full`

#### Scenario: CAO-only mode uses CAO-native gating/extraction and does not invoke Claude shadow parser
- **WHEN** a Claude CAO-backed session runs with `parsing_mode=cao_only`
- **THEN** readiness/completion uses CAO terminal status and answer extraction uses `output?mode=last`
- **AND THEN** Claude shadow parser logic is not used for gating or projection in that turn
- **AND THEN** parser-mode switching requires a new mode selection outside that turn

### Requirement: Claude shadow parsing mode does not mix parser families in one turn
For Claude CAO-backed turns in `parsing_mode=shadow_only`, the runtime SHALL NOT invoke CAO-native extraction as a fallback within the same turn.

#### Scenario: Shadow extraction failure does not trigger CAO-native fallback
- **WHEN** Claude shadow extraction fails for a `shadow_only` turn
- **THEN** the turn fails with a shadow-mode error
- **AND THEN** the runtime does not call CAO-native extraction in that same turn

### Requirement: Claude Code shadow parsing fails explicitly on unsupported output formats
For CAO provider `claude_code`, when a session runs in `parsing_mode=shadow_only`, the runtime-owned Claude Code shadow parser SHALL explicitly detect when `output?mode=full` does not match any supported output format variant for the selected preset family.

If no supported variant matches, the system SHALL fail the turn with an explicit `unsupported_output_format`-class error and include an ANSI-stripped tail excerpt for diagnostics. The system SHALL NOT treat this condition as normal `processing` indefinitely.

#### Scenario: Drifted output fails explicitly with diagnostics
- **WHEN** a Claude Code CAO-backed session runs in `parsing_mode=shadow_only`
- **AND WHEN** `output?mode=full` does not match any supported Claude Code output format variant
- **THEN** the turn fails with an explicit `unsupported_output_format`-class error
- **AND THEN** the error includes an ANSI-stripped tail excerpt suitable for debugging

### Requirement: Claude Code parsing preset is resolved by version
The system SHALL resolve a single Claude Code parsing preset using this priority order:
1. `HOUMAO_CAO_CLAUDE_CODE_VERSION` environment variable when set and non-empty,
2. auto-detected Claude Code version from the scrollback banner, and
3. the latest known preset.

If version detection fails entirely, the system SHALL use the latest known preset. Operators MAY set `HOUMAO_CAO_CLAUDE_CODE_VERSION` to pin a specific preset when the latest patterns do not match.

#### Scenario: Env override pins the parsing preset
- **GIVEN** `HOUMAO_CAO_CLAUDE_CODE_VERSION=2.1.62` is set for the runtime process
- **WHEN** the system evaluates Claude Code output for shadow status or extraction
- **THEN** it uses the 2.1.62 parsing preset regardless of what the scrollback banner reports

### Requirement: Claude Code version floor lookup is reported as an explicit anomaly
When resolving a Claude Code parsing preset based on a detected version signature `V`, if no exact preset exists and the system uses a previous (floor) preset for best-effort parsing, the system SHALL report an explicit anomaly indicating that the output version did not match a known preset exactly.

#### Scenario: Unknown version uses floor preset and is reported
- **WHEN** `output?mode=full` includes a banner version `V`
- **AND WHEN** no exact parsing preset exists for `V`
- **AND WHEN** the system selects a previous preset for compatibility
- **THEN** the system uses the selected floor preset for parsing
- **AND THEN** parser metadata includes an explicit anomaly indicating the version mismatch

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

### Requirement: Claude unknown status can transition to stalled after configurable timeout
For Claude in `parsing_mode=shadow_only`, runtime SHALL transition from `unknown` to `stalled` when continuous unknown duration reaches configured timeout.

#### Scenario: Unknown reaches stalled threshold
- **WHEN** Claude shadow polling remains in `unknown` continuously
- **AND WHEN** elapsed unknown duration reaches `unknown_to_stalled_timeout_seconds`
- **THEN** runtime shadow lifecycle status becomes `stalled`

### Requirement: Claude stalled state supports configurable terminality and recovery
For Claude stalled handling, the runtime SHALL support configurable terminal and non-terminal recovery behavior:
- if `stalled_is_terminal=true`, runtime SHALL fail the turn with explicit stalled diagnostics,
- if `stalled_is_terminal=false`, runtime SHALL keep polling and MAY recover to a known status automatically.

#### Scenario: Non-terminal stalled recovers to completed
- **WHEN** Claude runtime is in non-terminal `stalled`
- **AND WHEN** later `mode=full` output includes valid Claude completion evidence
- **THEN** runtime transitions back to known status processing and completes turn extraction without forcing immediate failure at stalled entry

#### Scenario: Terminal stalled fails turn immediately
- **WHEN** Claude runtime reaches `stalled`
- **AND WHEN** `stalled_is_terminal=true`
- **THEN** runtime returns an explicit stalled-state failure with parser-family context and tail excerpt

### Requirement: Claude dialog projection from `mode=full` is preset-scoped, ANSI-stripped, and UI-bounded
When projecting Claude Code dialog content from `mode=full` output, the system SHALL:
1) resolve the active parsing preset,
2) strip ANSI and provider-specific TUI chrome, and
3) preserve essential visible dialog content without promising prompt-specific answer association.

Projection boundaries SHALL be provider-aware and preset-scoped so version-specific prompt lines, separators, menu chrome, and spinner output can be removed consistently.

#### Scenario: Projection removes Claude prompt chrome but preserves visible dialog
- **WHEN** tmux scrollback contains Claude prompt lines, ANSI styling, separators, and visible dialog content
- **THEN** the projected dialog excludes the prompt/UI chrome
- **AND THEN** the projected dialog preserves the visible dialog content in order

### Requirement: Core Claude shadow parsing does not own prompt-to-answer association
For Claude Code `shadow_only`, prompt-to-answer association SHALL be treated as a separate layer above the core shadow parser.

The core Claude shadow parser MAY provide state, projection, metadata, and diagnostics, but SHALL NOT guarantee that projected dialog content is the authoritative final answer for the most recent prompt submission.

#### Scenario: Historical visible content does not invalidate projection contract
- **WHEN** a Claude snapshot contains visible dialog from prior turns in addition to current-turn activity
- **THEN** the parser still returns valid Claude surface assessment and dialog projection
- **AND THEN** the parser does not claim that the projection uniquely identifies the answer to the most recent prompt

### Requirement: Operator-blocked Claude surfaces are surfaced as explicit errors
If the system detects a Claude surface with `business_state = awaiting_operator` during a turn, it SHALL fail the turn with an explicit blocked-surface error and include an ANSI-stripped excerpt when available.

#### Scenario: Trust prompt is surfaced explicitly as an operator-blocked error
- **WHEN** `mode=full` contains a Claude trust or approval prompt requiring operator action
- **THEN** the runtime detects `business_state = awaiting_operator`
- **AND THEN** the turn fails with an explicit blocked-surface error instead of timing out or being treated as completed

### Requirement: Runtime does not return raw tmux scrollback as the answer
For Claude Code in `parsing_mode=shadow_only`, the system SHALL not return raw `mode=full` tmux output as caller-facing projected dialog content.

The system SHALL return normalized dialog projection instead, and SHALL NOT represent that projection as the authoritative final answer for the current prompt unless a separate answer-association layer explicitly does so.

#### Scenario: Completed shadow turn returns projection instead of raw tmux output
- **WHEN** a Claude `shadow_only` turn reaches runtime completion
- **THEN** the caller-facing payload contains normalized dialog projection rather than raw `mode=full` tmux scrollback
- **AND THEN** the payload does not claim authoritative prompt-associated answer extraction by default

