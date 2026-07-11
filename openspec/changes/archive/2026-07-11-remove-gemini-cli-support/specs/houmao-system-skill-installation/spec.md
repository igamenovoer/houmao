## ADDED Requirements

### Requirement: Shared system-skill projection has no Gemini destination
The shared system-skill installer, status discovery, synchronization, and removal contracts SHALL NOT recognize Gemini or `.gemini/skills` as a Houmao target.

#### Scenario: Gemini projection root is absent from destination resolution
- **WHEN** the system resolves supported tool-native skill destinations
- **THEN** no mapping points to `.gemini/skills`
- **AND THEN** Gemini is rejected before filesystem mutation
