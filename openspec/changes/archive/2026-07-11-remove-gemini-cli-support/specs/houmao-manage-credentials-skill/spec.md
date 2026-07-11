## ADDED Requirements

### Requirement: Credential management skill excludes Gemini
The credential management skill SHALL expose actions, kinds, examples, and references only for maintained credential providers and SHALL delete Gemini-only reference pages.

#### Scenario: Credential skill routing has no Gemini target
- **WHEN** an agent reads credential kind or action routing
- **THEN** it can route Claude, Codex, or Kimi credential work
- **AND THEN** no Gemini credential reference is discoverable from the skill
