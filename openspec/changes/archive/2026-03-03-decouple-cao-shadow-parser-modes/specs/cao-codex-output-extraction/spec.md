## ADDED Requirements

### Requirement: Codex CAO output supports runtime shadow parsing mode
For CAO provider `codex`, when a session runs in `parsing_mode=shadow_only`, the system SHALL treat CAO as a transport layer and derive both:
1) Codex turn status (shadow status), and
2) the last assistant message (answer text),
from `GET /terminals/{terminal_id}/output?mode=full`.

In `parsing_mode=shadow_only`, the system SHALL NOT rely on:
- CAO `GET /terminals/{terminal_id}` `status` for turn gating, or
- CAO `mode=last` output for answer extraction.

#### Scenario: Codex shadow mode uses only `mode=full` for gating and extraction
- **WHEN** a Codex CAO-backed session runs with `parsing_mode=shadow_only`
- **THEN** readiness/completion is classified from `output?mode=full`
- **AND THEN** answer extraction is performed from `output?mode=full`

### Requirement: Codex shadow parsing format contract is versioned and fails explicitly on mismatch
For Codex `shadow_only` turns, the runtime SHALL use a versioned Codex shadow output format contract (for example `codex_shadow_v1`).

If `output?mode=full` does not match the expected format contract, the turn SHALL fail with an explicit `unsupported_output_format` error. The runtime SHALL NOT return raw tmux scrollback as the user-visible answer and SHALL NOT fall back to `cao_only` within the same turn.

#### Scenario: Unknown Codex output format fails explicitly
- **WHEN** a Codex CAO-backed session runs with `parsing_mode=shadow_only`
- **AND WHEN** `output?mode=full` does not match the expected `codex_shadow_v1` format contract
- **THEN** the turn fails with an explicit `unsupported_output_format` error
- **AND THEN** the runtime does not attempt best-effort extraction or fall back to `cao_only` in that turn

### Requirement: Codex shadow status is baseline-aware and output-driven
The system SHALL compute Codex shadow status from `mode=full` output using a per-turn baseline captured before prompt submission so completion requires post-baseline assistant output.

#### Scenario: Completion requires post-baseline response evidence
- **WHEN** `mode=full` contains historical assistant output from prior turns
- **AND WHEN** no new post-baseline assistant output exists for the current turn
- **THEN** the system does not classify the turn as completed

### Requirement: Codex shadow extraction returns plain assistant text only
For Codex `shadow_only` turns, the runtime SHALL return extracted plain assistant text and SHALL NOT return raw tmux scrollback as the user-visible answer.

#### Scenario: Extraction strips prompt/UI chrome from output
- **WHEN** `mode=full` includes Codex prompts, footer chrome, or spinner lines around assistant content
- **THEN** the extracted answer excludes those UI lines
- **AND THEN** returned answer text is plain text suitable for caller consumption

### Requirement: Codex waiting-user-answer is explicit in shadow mode
If Codex `shadow_only` status indicates waiting for user interaction, the turn SHALL fail with an explicit error rather than being classified as completed.

#### Scenario: Waiting-user-answer interrupts normal completion
- **WHEN** Codex `shadow_only` output indicates an approval/selection prompt requiring user action
- **THEN** the runtime returns an explicit waiting-user-answer error
- **AND THEN** the turn is not treated as completed

### Requirement: Codex CAO-only mode uses CAO-native gating and extraction
For CAO provider `codex`, when a session runs in `parsing_mode=cao_only`, the runtime SHALL derive readiness/completion from CAO terminal status and SHALL extract answer text from `GET /terminals/{terminal_id}/output?mode=last`. The runtime SHALL NOT invoke the Codex shadow parser in this mode.

#### Scenario: Codex CAO-only mode uses `mode=last`
- **WHEN** a Codex CAO-backed session runs with `parsing_mode=cao_only`
- **THEN** readiness/completion is derived from CAO terminal status
- **AND THEN** answer extraction uses `output?mode=last`
