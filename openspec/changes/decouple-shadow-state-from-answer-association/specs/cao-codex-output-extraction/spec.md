## MODIFIED Requirements

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

## ADDED Requirements

### Requirement: Codex shadow surface classification is output-driven and bounded
The system SHALL compute Codex shadow surface state from `mode=full` output using a bounded provider-aware window and SHALL classify at least:

- `working` when Codex processing evidence is present,
- `waiting_user_answer` when Codex approval/selection UI is present,
- `ready_for_input` when input-ready evidence is present and no higher-priority state matches, and
- `unknown` when output matches a supported Codex output family but does not satisfy known safe state evidence.

#### Scenario: Ready state does not imply authoritative answer association
- **WHEN** a Codex snapshot contains input-ready evidence and no higher-priority state evidence
- **THEN** the system classifies the snapshot as `ready_for_input`
- **AND THEN** that classification does not by itself claim that visible assistant text belongs to the most recent prompt submission

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

## REMOVED Requirements

### Requirement: Codex shadow status is baseline-aware and output-driven
**Reason**: Baseline-aware prompt association is being removed from the core Codex shadow parser contract and moved to a separate runtime/caller layer.
**Migration**: Callers and runtime should rely on shadow surface assessment plus projected dialog, with any prompt-specific association performed by a separate layer when needed.

### Requirement: Codex shadow extraction returns plain assistant text only
**Reason**: The core Codex shadow parser is no longer the authoritative owner of prompt-specific answer extraction.
**Migration**: Consume normalized dialog projection from shadow mode and perform optional caller-owned answer association when prompt-specific extraction is required.
