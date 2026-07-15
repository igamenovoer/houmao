## ADDED Requirements

### Requirement: Specialist credential sources exclude Gemini
Specialist creation SHALL offer provider-native credential sources only for maintained providers and SHALL expose no Gemini API-key, OAuth, config, or home import fields.

#### Scenario: Gemini credential source flags are absent
- **WHEN** an operator inspects specialist creation help
- **THEN** no Gemini-specific credential option is present
- **AND THEN** `--tool gemini` is not a valid specialist selection
