## MODIFIED Requirements

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

### Requirement: Runtime does not return raw tmux scrollback as the answer
For Claude Code in `parsing_mode=shadow_only`, the system SHALL not return raw `mode=full` tmux output as caller-facing projected dialog content.

The system SHALL return normalized dialog projection instead, and SHALL NOT represent that projection as the authoritative final answer for the current prompt unless a separate answer-association layer explicitly does so.

#### Scenario: Completed shadow turn returns projection instead of raw tmux output
- **WHEN** a Claude `shadow_only` turn reaches runtime completion
- **THEN** the caller-facing payload contains normalized dialog projection rather than raw `mode=full` tmux scrollback
- **AND THEN** the payload does not claim authoritative prompt-associated answer extraction by default

## ADDED Requirements

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

## REMOVED Requirements

### Requirement: Answer extraction from `mode=full` is preset-scoped, ANSI-stripped, and prompt-bounded
**Reason**: Generic prompt-associated answer extraction from CAO/tmux Claude TUI snapshots is not a stable core parser guarantee. The provider contract is being narrowed to state detection and dialog projection.
**Migration**: Callers should consume projected dialog/state payloads and apply a separate caller-owned answer-association layer when prompt-specific answer extraction is required.
