## MODIFIED Requirements

### Requirement: Claude Code CAO output is parsed by a runtime shadow provider
For CAO provider `claude_code`, when a session runs in `parsing_mode=shadow_only`, the system SHALL treat CAO as a transport layer and derive both:
1) Claude Code turn status (shadow status), and
2) the last assistant message (answer text),
from `GET /terminals/{terminal_id}/output?mode=full`.

In `parsing_mode=shadow_only`, the system SHALL NOT rely on:
- CAO `GET /terminals/{terminal_id}` `status` for turn gating, or
- CAO `mode=last` output for answer extraction,
because those behaviors are derived from upstream regexes that are known to drift.

In `parsing_mode=cao_only`, the runtime SHALL NOT invoke Claude shadow parsing for turn gating or extraction.
In `parsing_mode=cao_only`, Claude turns use the CAO-native path: readiness/completion is derived from CAO terminal status and answer extraction uses `output?mode=last`.

#### Scenario: Shadow mode keeps Claude gating/output extraction runtime-owned
- **WHEN** a Claude CAO-backed session runs with `parsing_mode=shadow_only`
- **THEN** readiness/completion is derived from runtime shadow status over `mode=full`
- **AND THEN** answer extraction uses runtime shadow parsing over `mode=full`

#### Scenario: CAO-only mode uses CAO-native gating/extraction and does not invoke Claude shadow parser
- **WHEN** a Claude CAO-backed session runs with `parsing_mode=cao_only`
- **THEN** readiness/completion uses CAO terminal status and answer extraction uses `output?mode=last`
- **AND THEN** Claude shadow parser logic is not used for gating or extraction in that turn
- **AND THEN** parser-mode switching requires a new mode selection outside that turn

## ADDED Requirements

### Requirement: Claude shadow parsing mode does not mix parser families in one turn
For Claude CAO-backed turns in `parsing_mode=shadow_only`, the runtime SHALL NOT invoke CAO-native extraction as a fallback within the same turn.

#### Scenario: Shadow extraction failure does not trigger CAO-native fallback
- **WHEN** Claude shadow extraction fails for a `shadow_only` turn
- **THEN** the turn fails with a shadow-mode error
- **AND THEN** the runtime does not call CAO-native extraction in that same turn
