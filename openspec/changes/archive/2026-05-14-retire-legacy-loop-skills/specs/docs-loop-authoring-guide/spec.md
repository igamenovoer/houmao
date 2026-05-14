## ADDED Requirements

### Requirement: Loop authoring guide is pro-oriented
The loop authoring guide SHALL present `houmao-agent-loop-pro` as the current loop authoring skill.

The guide SHALL explain that tree-loop and generic-loop are topology decisions inside pro-generated execplans.

The guide SHALL NOT maintain a current skill-selection table among retired pairwise and generic loop packages.

#### Scenario: Reader chooses topology inside pro
- **WHEN** a reader wants to author a new loop
- **THEN** the guide directs them to `houmao-agent-loop-pro`
- **AND THEN** the guide explains when to choose tree-loop versus generic-loop mode

### Requirement: Loop authoring guide preserves graph helper context
The loop authoring guide SHALL continue to mention `houmao-mgr internals graph high` as deterministic graph tooling available to pro authoring when graph artifacts are useful.

#### Scenario: Reader needs deterministic graph validation
- **WHEN** a pro-generated loop has a topology graph that benefits from deterministic analysis
- **THEN** the guide points to `houmao-mgr internals graph high`
- **AND THEN** it does not require retired loop package names to use that tool
