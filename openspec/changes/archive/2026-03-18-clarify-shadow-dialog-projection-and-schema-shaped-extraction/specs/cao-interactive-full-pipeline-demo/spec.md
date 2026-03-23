## MODIFIED Requirements

### Requirement: Multi-turn prompt driving against a live session
The interactive full-pipeline demo SHALL remain compatible with the default shadow-first CAO runtime posture for Claude and Codex.

For CAO-backed `shadow_only` turns, per-turn artifacts and verification SHALL NOT assume that the final runtime `done.message` contains the exact assistant reply text.

If the demo records one human-facing text field for a turn, that field SHALL either be derived through an explicit shadow-aware extraction path and described as best-effort, or be replaced by another completion/diagnostic summary. Successful turn verification SHALL rely on recorded turn completion, exit status, and any explicit shadow-aware text contract rather than on CAO-native reply-text assumptions.

#### Scenario: Sequential prompts stay valid under the shadow-first default
- **WHEN** the user runs the turn-driving command multiple times after a successful Claude or Codex interactive startup
- **THEN** each turn targets the same `agent_identity` recorded by startup
- **AND THEN** each turn records a successful completion artifact even when the final runtime `done.message` is a neutral shadow-mode completion message

#### Scenario: Verification does not require CAO-native reply text under shadow mode
- **WHEN** the interactive demo verifies recorded Claude or Codex turns produced under the default shadow-mode CAO posture
- **THEN** the verification flow does not require a non-empty authoritative reply string extracted from the final runtime `done.message`
- **AND THEN** it validates turn success through completion metadata plus any explicitly documented best-effort or schema-shaped text surface instead
