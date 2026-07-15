## ADDED Requirements

### Requirement: Gateway notifier has no Gemini prompt specialization
Gateway mail-notifier prompt rendering SHALL NOT contain Gemini-specific skill invocation, destination paths, or provider branches.

#### Scenario: Maintained notifier providers exclude Gemini
- **WHEN** notifier guidance is rendered for a maintained provider
- **THEN** it uses the applicable Claude, Codex, or Kimi contract
- **AND THEN** no Gemini prompt branch is selectable
