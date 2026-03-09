## ADDED Requirements

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
The system SHALL resolve a single Claude Code parsing preset that controls:
1) assistant response marker detection,
2) spinner/processing detection,
3) idle prompt detection (used for shadow status and extraction stop conditions), and
4) separator line detection (for example `────────`).

Preset selection SHALL follow this priority order:
1) `AGENTSYS_CAO_CLAUDE_CODE_VERSION` environment variable (when set and non-empty),
2) auto-detected Claude Code version from the scrollback banner (for example `Claude Code v2.1.62`), and
3) latest known preset (fallback).

If version detection fails entirely (no banner/version found), the system SHALL use the latest known preset. Operators MAY set `AGENTSYS_CAO_CLAUDE_CODE_VERSION` to pin a specific preset when the latest patterns do not match.

When selecting a preset for a requested/detected version `V`, the system SHALL:
- use an exact-match preset when present, otherwise
- use the closest previous preset (floor lookup), and
- if `V` is older than the oldest known preset, use the oldest (baseline) preset.

#### Scenario: Env override pins the parsing preset
- **GIVEN** `AGENTSYS_CAO_CLAUDE_CODE_VERSION=2.1.62` is set for the runtime process
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
The system SHALL compute Claude Code shadow surface state from a bounded tail window of the `mode=full` output, and SHALL default to the last 100 lines from the end of the output.

The system SHALL classify at least:
- `working` when preset-recognized spinner/progress evidence is present,
- `waiting_user_answer` when selection UI is present,
- `ready_for_input` when idle/input-ready evidence is present and no higher-priority state matches, and
- `unknown` when output matches a supported Claude output family but does not satisfy known safe state evidence.

The provider SHALL surface `ui_context` through the Claude surface-assessment contract, including the shared `slash_command` context when applicable and Claude-specific contexts such as `trust_prompt`.
Those context details SHALL NOT imply prompt-associated answer extraction.

#### Scenario: Status checks avoid stale scrollback false positives
- **WHEN** the tmux scrollback contains an old spinner line from a previous turn
- **AND WHEN** the bounded tail window for the current status check does not include that spinner line
- **THEN** the system does not classify the terminal as `working` based on stale output

#### Scenario: Ready state does not imply authoritative answer association
- **WHEN** the tmux scrollback contains idle/input-ready evidence
- **THEN** the system classifies the snapshot as `ready_for_input` when no higher-priority state matches
- **AND THEN** that state classification does not by itself claim that a visible answer belongs to the most recent prompt submission

#### Scenario: Slash-command UI is surfaced as shared context without implying answer ownership
- **WHEN** a Claude snapshot shows slash-command or command-palette UI
- **THEN** the returned Claude surface assessment may use the shared `slash_command` `ui_context`
- **AND THEN** that context classification does not imply prompt-associated answer extraction

### Requirement: Claude shadow status supports explicit unknown classification
For Claude Code in `parsing_mode=shadow_only`, if output matches a supported Claude output family but does not satisfy known status evidence for `processing`, `waiting_user_answer`, `completed`, or `idle`, the runtime-owned Claude shadow parser SHALL classify the snapshot status as `unknown`.

#### Scenario: Recognized Claude output without known status evidence is unknown
- **WHEN** `mode=full` output matches a supported Claude variant
- **AND WHEN** the snapshot has no valid completion, waiting-user-answer, idle-prompt, or processing evidence
- **THEN** Claude shadow status is `unknown`

### Requirement: Claude unknown status can transition to stalled after configurable timeout
For Claude in `parsing_mode=shadow_only`, runtime SHALL transition from `unknown` to `stalled` when continuous unknown duration reaches configured timeout.

#### Scenario: Unknown reaches stalled threshold
- **WHEN** Claude shadow polling remains in `unknown` continuously
- **AND WHEN** elapsed unknown duration reaches `unknown_to_stalled_timeout_seconds`
- **THEN** runtime shadow lifecycle status becomes `stalled`

### Requirement: Claude stalled state supports configurable terminality and recovery
For Claude stalled handling:
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

### Requirement: Waiting-user-answer is surfaced as an explicit error
If the system detects `waiting_user_answer` for Claude Code during a turn, it SHALL fail the turn with an explicit error and include an ANSI-stripped excerpt showing the selection options.

### Requirement: Runtime does not return raw tmux scrollback as the answer
For Claude Code in `parsing_mode=shadow_only`, the system SHALL not return raw `mode=full` tmux output as caller-facing projected dialog content.

The system SHALL return normalized dialog projection instead, and SHALL NOT represent that projection as the authoritative final answer for the current prompt unless a separate answer-association layer explicitly does so.

#### Scenario: Completed shadow turn returns projection instead of raw tmux output
- **WHEN** a Claude `shadow_only` turn reaches runtime completion
- **THEN** the caller-facing payload contains normalized dialog projection rather than raw `mode=full` tmux scrollback
- **AND THEN** the payload does not claim authoritative prompt-associated answer extraction by default
