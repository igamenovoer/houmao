## ADDED Requirements

### Requirement: CAO control core exposes no Gemini compatibility provider
The CAO control core SHALL NOT register `gemini_cli` or provide Gemini startup, rendered-status, input, or interrupt behavior.

#### Scenario: Gemini compatibility provider lookup fails
- **WHEN** a caller requests the CAO compatibility provider `gemini_cli`
- **THEN** provider lookup reports an unsupported provider
- **AND THEN** no `gemini` process command is constructed
