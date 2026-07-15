## ADDED Requirements

### Requirement: Headless output rendering has no Gemini format
Canonical headless output parsing, rendering, and artifact normalization SHALL NOT register or select a Gemini stream format.

#### Scenario: Gemini renderer selection is unavailable
- **WHEN** a caller asks the headless output layer to parse a Gemini stream
- **THEN** the layer rejects the unsupported provider format
- **AND THEN** it does not emit canonical events from Gemini-specific records
