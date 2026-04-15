## ADDED Requirements

### Requirement: README links to the reusable writer-team example

When the repository contains `examples/writer-team/`, the README agent-loop story-writing section SHALL link to that example as the reusable template for the three-agent writing team.

The README SHALL distinguish the reusable example from the inline quick-start narrative by making clear that the example contains the prompt files, loop plan, start charter, and local setup instructions.

#### Scenario: Reader wants to reuse the story-writing team

- **WHEN** a reader finishes the README story-writing loop section
- **THEN** they find a link to `examples/writer-team/`
- **AND THEN** they understand that the linked example is the reusable template for creating the three-agent writing team locally
