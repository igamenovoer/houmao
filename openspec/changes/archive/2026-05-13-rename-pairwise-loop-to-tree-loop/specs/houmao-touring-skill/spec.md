## ADDED Requirements

### Requirement: Touring presents tree loop and generic loop families
The packaged `houmao-touring` skill SHALL present `tree loop` and `generic loop` as the canonical advanced loop families in guided-tour and advanced-usage guidance.

The touring guidance SHALL present pairwise-named loop skills as legacy-named or compatibility-named tree-loop skills.

The touring guidance SHALL preserve explicit skill names such as `houmao-agent-loop-pairwise`, `houmao-agent-loop-pairwise-v2`, `houmao-agent-loop-pairwise-v3`, `houmao-agent-loop-pairwise-v4`, and `houmao-agent-loop-pairwise-v5` when routing users to installed skill identities.

The touring guidance SHALL describe the advanced-usage elemental protocol as a local-close edge loop while preserving pairwise edge-loop alias wording for compatibility.

#### Scenario: Tour explains advanced loop choices
- **WHEN** the guided tour explains advanced loop creation choices
- **THEN** it names tree loop and generic loop as the primary families
- **AND THEN** pairwise-named skills are explained as tree-loop skills with legacy invocation names

#### Scenario: Tour routes to existing skill handles
- **WHEN** a user selects a specific pairwise-named skill from the tour
- **THEN** the tour routes to that existing skill handle
- **AND THEN** it does not invent a renamed package or hidden alias skill
