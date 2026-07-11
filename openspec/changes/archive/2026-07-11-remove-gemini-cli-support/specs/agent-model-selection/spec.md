## ADDED Requirements

### Requirement: Model selection has no Gemini projection target
Houmao model-name and reasoning-level resolution SHALL NOT recognize Gemini or mutate `GEMINI_CLI_HOME` settings.

#### Scenario: Gemini model request is unsupported
- **WHEN** model selection receives Gemini as the resolved tool
- **THEN** it rejects the unsupported tool
- **AND THEN** it does not write `.gemini/settings.json` or Gemini thinking configuration
