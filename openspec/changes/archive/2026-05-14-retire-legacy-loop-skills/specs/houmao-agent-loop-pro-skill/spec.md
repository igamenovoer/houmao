## ADDED Requirements

### Requirement: Pro is the sole maintained loop system skill
The packaged `houmao-agent-loop-pro` skill SHALL be the only current Houmao-owned system skill for loop authoring, generated execplan validation, and generated loop execution.

The pro skill SHALL cover both tree-loop and generic-loop topology modes through its generated execplan workflow.

The pro skill SHALL NOT instruct users to invoke retired pairwise or generic loop skill packages for current loop authoring or execution.

#### Scenario: User asks for current loop authoring
- **WHEN** a user explicitly asks for the current Houmao loop authoring skill
- **THEN** `houmao-agent-loop-pro` is the current packaged skill
- **AND THEN** the skill directs topology selection through pro `tree-loop` or `generic-loop` mode

#### Scenario: Pro does not route to retired loop packages
- **WHEN** pro guidance needs tree-loop or generic-loop behavior
- **THEN** it uses pro subskills and references
- **AND THEN** it does not route execution to retired pairwise or generic loop packages

### Requirement: Pro accepts legacy topology language without preserving legacy package routes
The pro skill SHALL accept legacy loop language such as `pairwise loop`, `pairwise-tree`, `pairwise-v2`, `generic graph`, and `generic-graph` as compatibility terminology when validating or updating existing material.

The pro skill SHALL normalize new generated material to pro topology terms and SHALL NOT preserve retired package names as current routing targets.

#### Scenario: Existing pairwise wording is normalized
- **WHEN** pro updates an existing loop definition that uses pairwise topology wording
- **THEN** it treats that wording as legacy tree-loop terminology
- **AND THEN** newly generated current material records pro topology terms
