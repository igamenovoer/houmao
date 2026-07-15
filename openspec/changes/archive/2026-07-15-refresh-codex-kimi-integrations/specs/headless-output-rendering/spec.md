## ADDED Requirements

### Requirement: Codex collaboration calls use the canonical action lifecycle
The Codex headless parser SHALL normalize `collab_tool_call` started, updated, and completed records into canonical action request and action result events. Canonical data SHALL preserve available collaboration method, sender thread, receiver thread or agent identifiers, prompt, status, and agent-state details.

#### Scenario: Delegated agent call becomes canonical actions
- **WHEN** Codex emits started and completed `collab_tool_call` items for a delegated agent operation
- **THEN** the canonical stream contains a matching action request and action result
- **AND THEN** downstream renderers do not receive those recognized records as generic passthrough events

### Requirement: Kimi retry metadata becomes canonical progress and diagnostics
The Kimi headless parser SHALL normalize `turn.step.retrying` metadata into canonical progress or diagnostic events while preserving failed attempt, next attempt, maximum attempts, delay, status, and error details that Kimi emits.

#### Scenario: Retrying step remains visible without provider-specific parsing
- **WHEN** Kimi stream JSON emits `turn.step.retrying`
- **THEN** the canonical stream reports retry progress with the available attempt and delay fields
- **AND THEN** the raw Kimi payload remains preserved in the raw artifact

