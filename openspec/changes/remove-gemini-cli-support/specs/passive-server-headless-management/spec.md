## ADDED Requirements

### Requirement: Passive-server headless management excludes Gemini
The passive server SHALL support only currently maintained headless backends and SHALL reject Gemini tool and backend identifiers.

#### Scenario: Passive-server Gemini launch is rejected
- **WHEN** a caller requests a passive-server headless launch for `gemini` or `gemini_headless`
- **THEN** the request fails validation
- **AND THEN** no managed-agent record or provider process is created
