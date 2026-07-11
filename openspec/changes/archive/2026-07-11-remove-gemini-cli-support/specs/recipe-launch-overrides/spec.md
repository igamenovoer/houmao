## ADDED Requirements

### Requirement: Launch overrides expose no Gemini tool or backend scope
Recipe launch-override validation SHALL NOT recognize Gemini tool parameters or Gemini backend combinations.

#### Scenario: Gemini launch override is rejected as an unsupported tool
- **WHEN** a recipe or direct build supplies launch overrides for Gemini
- **THEN** validation rejects the tool rather than reporting a supported empty Gemini parameter set
