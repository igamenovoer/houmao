## ADDED Requirements

### Requirement: System-skills overview explains skill-level help
The getting-started guide `docs/getting-started/system-skills-overview.md` SHALL explain that every current packaged Houmao system skill supports an explicit help request from its top-level skill instructions.

The guide SHALL explain that help responses are read-only and are meant to show purpose, available functionality, common starting prompts, and related skill boundaries.

The guide SHALL explain that help is handled before normal workflow routing when the user explicitly asks for skill usage, but ordinary task requests still route to the task workflow.

The guide SHALL include one or more example help prompts.

#### Scenario: Reader learns the help convention
- **WHEN** a reader opens the system-skills overview guide
- **THEN** the guide states that each current packaged system skill supports explicit help
- **AND THEN** the guide explains what a help response should contain
- **AND THEN** it distinguishes explicit help from ordinary workflow requests
