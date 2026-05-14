## ADDED Requirements

### Requirement: Houmao loop terminology uses tree loop and generic loop as canonical names
Houmao system-skill guidance SHALL use `tree loop` as the canonical user-facing name for tree-shaped or forest-shaped local-close loop execution.

Houmao system-skill guidance SHALL use `generic loop` as the canonical user-facing name for directed graph loop execution that can include non-tree routes or cycles.

Houmao system-skill guidance SHALL preserve `pairwise loop`, `pairwise-tree`, `pairwise-only`, and pairwise-named skill identifiers as aliases for tree loop concepts.

Houmao system-skill guidance SHALL preserve `generic graph` and `generic-graph` as aliases for generic loop concepts.

The system SHALL NOT rename existing pairwise-named skill directories, frontmatter names, CLI-facing skill handles, or explicit invocation names as part of this terminology change.

#### Scenario: Agent explains the two loop families
- **WHEN** a system skill explains the high-level topology choices for a generated or authored loop
- **THEN** it presents `tree loop` and `generic loop` as the canonical choices
- **AND THEN** it may mention `pairwise loop` or `generic graph` only as compatibility aliases or existing skill identifiers

#### Scenario: Pairwise-named skill remains invokable
- **WHEN** a user explicitly invokes a pairwise-named skill such as `houmao-agent-loop-pairwise-v5`
- **THEN** the package name remains valid
- **AND THEN** the skill explains that the pairwise-named skill authors or operates tree-loop behavior

### Requirement: Generated pro topology values prefer tree-loop and generic-loop
Generated `houmao-agent-loop-pro` execplan guidance SHALL prefer `tree-loop` as the machine-readable topology mode for tree-loop execution.

Generated `houmao-agent-loop-pro` execplan guidance SHALL prefer `generic-loop` as the machine-readable topology mode for generic-loop execution.

The pro guidance SHALL accept legacy generated topology values `pairwise-tree`, `pairwise-loop`, `pairwise`, `generic-graph`, and `generic graph` as aliases when validating, clarifying, or updating existing generated material.

Newly generated process specs, topology contracts, manifests, validation notes, and examples SHOULD use `tree-loop` and `generic-loop` unless an existing artifact is being preserved for compatibility.

#### Scenario: New pro execplan records tree-loop
- **WHEN** pro generates a new execplan for tree-shaped local-close execution
- **THEN** generated topology material records `tree-loop` as the preferred topology mode
- **AND THEN** generated prose describes the behavior as a tree loop

#### Scenario: Existing pairwise-tree material remains valid
- **WHEN** pro validates or updates an existing generated execplan whose topology mode is `pairwise-tree`
- **THEN** the guidance treats `pairwise-tree` as a tree-loop alias
- **AND THEN** validation does not fail solely because the older alias appears

### Requirement: Elemental pairwise edge wording migrates to local-close edge loop
Houmao system-skill guidance SHALL use `local-close edge loop` as the canonical user-facing name for the elemental two-agent driver/worker protocol in which the worker returns the result to the same immediate driver.

Existing wording, filenames, or references containing `pairwise edge-loop` SHALL remain valid aliases for that elemental local-close edge protocol.

#### Scenario: Advanced usage explains the elemental edge protocol
- **WHEN** a system skill points to the elemental two-agent driver/worker protocol
- **THEN** it describes the protocol as a local-close edge loop
- **AND THEN** it may include `pairwise edge-loop` as a compatibility alias for existing references
