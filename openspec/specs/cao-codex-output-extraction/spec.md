## Purpose
Define expected runtime behaviors for extracting output and classifying turn status
for Codex when using CAO as a transport layer.

## Requirements

## ADDED Requirements

### Requirement: Codex CAO output supports runtime shadow parsing mode
For CAO provider `codex`, when a session runs in `parsing_mode=shadow_only`, the system SHALL treat CAO as a transport layer and derive both:
1) Codex surface state, and
2) projected dialog content,
from `GET /terminals/{terminal_id}/output?mode=full`.

In `parsing_mode=shadow_only`, the system SHALL NOT rely on:
- CAO `GET /terminals/{terminal_id}` `status` for turn gating, or
- CAO `mode=last` output for dialog projection.

In `parsing_mode=shadow_only`, the core Codex shadow parser SHALL NOT promise prompt-associated final answer extraction from `mode=full`.

#### Scenario: Codex shadow mode uses only `mode=full` for state and projection
- **WHEN** a Codex CAO-backed session runs with `parsing_mode=shadow_only`
- **THEN** readiness/completion is derived from runtime-owned Codex surface assessment over `mode=full`
- **AND THEN** caller-facing dialog projection is derived from `mode=full`

### Requirement: Codex shadow parsing format contract is versioned and fails explicitly on mismatch
For Codex `shadow_only` turns, the runtime SHALL use a versioned Codex shadow output format contract (for example `codex_shadow_v1`).

If `output?mode=full` does not match the expected format contract, the turn SHALL fail with an explicit `unsupported_output_format` error. The runtime SHALL NOT return raw tmux scrollback as the user-visible answer and SHALL NOT fall back to `cao_only` within the same turn.

#### Scenario: Unknown Codex output format fails explicitly
- **WHEN** a Codex CAO-backed session runs with `parsing_mode=shadow_only`
- **AND WHEN** `output?mode=full` does not match the expected `codex_shadow_v1` format contract
- **THEN** the turn fails with an explicit `unsupported_output_format` error
- **AND THEN** the runtime does not attempt best-effort extraction or fall back to `cao_only` in that turn

### Requirement: Codex shadow parsing is a functional superset of upstream CAO provider behavior
For CAO provider `codex`, when a session runs in `parsing_mode=shadow_only`, the runtime-owned Codex shadow parser SHALL support at least the same status detection and dialog projection behaviors as the upstream CAO Codex provider parser for all supported Codex output variants.

At minimum, the Codex shadow parser SHALL correctly handle:

- label-style outputs that include `assistant:` markers, and
- interactive/TUI-style outputs that include Codex prompt chrome and bullet-style assistant markers.

#### Scenario: Label-style output is classified and projected correctly
- **WHEN** `output?mode=full` contains a Codex turn in a label-style format
- **THEN** shadow surface state is classified correctly for that snapshot
- **AND THEN** projected dialog preserves assistant-visible content without prompt/footer chrome

#### Scenario: TUI-style output is classified and projected correctly
- **WHEN** `output?mode=full` contains a Codex turn in an interactive/TUI-style format with prompt/footer chrome and a bullet-style assistant marker
- **THEN** shadow surface state is classified correctly for that snapshot
- **AND THEN** projected dialog preserves assistant-visible content without prompt/footer chrome

### Requirement: Codex shadow surface classification is output-driven and bounded
The system SHALL compute Codex shadow surface state from `mode=full` output using a bounded provider-aware window and SHALL classify at least:

- `working` when Codex processing evidence is present,
- `waiting_user_answer` when Codex approval/selection UI is present,
- `ready_for_input` when input-ready evidence is present and no higher-priority state matches, and
- `unknown` when output matches a supported Codex output family but does not satisfy known safe state evidence.

The provider SHALL surface `ui_context` through the Codex surface-assessment contract, including the shared `slash_command` context when applicable and Codex-specific contexts such as `approval_prompt`.

#### Scenario: Ready state does not imply authoritative answer association
- **WHEN** a Codex snapshot contains input-ready evidence and no higher-priority state evidence
- **THEN** the system classifies the snapshot as `ready_for_input`
- **AND THEN** that classification does not by itself claim that visible assistant text belongs to the most recent prompt submission

#### Scenario: Codex slash-command UI is surfaced through the shared context vocabulary
- **WHEN** a Codex snapshot shows slash-command or command-palette style UI
- **THEN** the returned Codex surface assessment may use the shared `slash_command` `ui_context`
- **AND THEN** Codex-specific contexts such as `approval_prompt` remain available for Codex-specific UI states

### Requirement: Codex dialog projection returns normalized dialog content
For Codex `shadow_only` turns, the runtime SHALL return normalized dialog projection and SHALL NOT return raw tmux scrollback as the caller-facing shadow-mode dialog surface.

The projected dialog SHALL remove Codex-specific prompt/footer/spinner chrome while preserving essential visible dialog content.

#### Scenario: Projection strips Codex UI chrome from the caller-facing dialog surface
- **WHEN** `mode=full` includes Codex prompts, footer chrome, or spinner lines around visible dialog content
- **THEN** the projected dialog excludes those UI lines
- **AND THEN** the returned dialog surface preserves the essential visible dialog content

### Requirement: Core Codex shadow parsing does not own prompt-to-answer association
For Codex `shadow_only`, prompt-to-answer association SHALL be treated as a separate layer above the core shadow parser.

The core Codex shadow parser MAY provide state, projection, metadata, and diagnostics, but SHALL NOT guarantee that projected dialog content is the authoritative final answer for the most recent prompt submission.

#### Scenario: Historical visible content does not invalidate Codex projection contract
- **WHEN** a Codex snapshot contains visible dialog from prior turns in addition to current-turn activity
- **THEN** the parser still returns valid Codex surface assessment and dialog projection
- **AND THEN** the parser does not claim that the projection uniquely identifies the answer to the most recent prompt

### Requirement: Codex waiting-user-answer is explicit in shadow mode
For Codex in `parsing_mode=shadow_only`, if `output?mode=full` indicates that Codex is waiting for a user approval/selection prompt (for example a yes/no approval question), the runtime SHALL classify the shadow status as `waiting_user_answer` and SHALL fail the turn with an explicit waiting-user-answer error.

#### Scenario: Approval prompt is surfaced explicitly
- **WHEN** `output?mode=full` contains a Codex approval prompt requiring user action (for example `Approve ... [y/n]`)
- **THEN** the runtime detects `waiting_user_answer`
- **AND THEN** the turn fails with an explicit waiting-user-answer error instead of timing out or being treated as completed

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

### Requirement: Codex CAO-only mode uses CAO-native gating and extraction
For CAO provider `codex`, when a session runs in `parsing_mode=cao_only`, the runtime SHALL derive readiness/completion from CAO terminal status and SHALL extract answer text from `GET /terminals/{terminal_id}/output?mode=last`. The runtime SHALL NOT invoke the Codex shadow parser in this mode.

#### Scenario: Codex CAO-only mode uses `mode=last`
- **WHEN** a Codex CAO-backed session runs with `parsing_mode=cao_only`
- **THEN** readiness/completion is derived from CAO terminal status
- **AND THEN** answer extraction uses `output?mode=last`
