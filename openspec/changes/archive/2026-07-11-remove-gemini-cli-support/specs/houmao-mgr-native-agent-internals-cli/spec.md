## ADDED Requirements

### Requirement: Native-agent internals exclude Gemini
Native-agent tool, credential, recipe, build, launch, and join surfaces SHALL NOT accept Gemini tool or backend identities.

#### Scenario: Native-agent Gemini selection fails before mutation
- **WHEN** an operator selects Gemini through a native-agent internals command
- **THEN** the command rejects the unsupported selection before writing agent-definition or runtime state
