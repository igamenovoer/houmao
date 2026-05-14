## ADDED Requirements

### Requirement: Touring presents pro as the current loop path
The touring skill SHALL present `houmao-agent-loop-pro` as the current advanced loop authoring and execution path.

The touring skill SHALL NOT enumerate retired pairwise or generic loop packages as current loop choices.

#### Scenario: Touring user asks about advanced loops
- **WHEN** a user asks touring for advanced loop creation or loop operation guidance
- **THEN** touring identifies `houmao-agent-loop-pro` as the current loop skill
- **AND THEN** it describes tree-loop and generic-loop as mode choices inside pro
