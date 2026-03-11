## ADDED Requirements

### Requirement: Brain recipes MAY declare a default agent name
The system SHALL support an optional `default_agent_name` field in brain recipes for consumers that want a recipe-owned default identity name in addition to the recipe's tool, skill, config-profile, and credential-profile selections.

When present, `default_agent_name` SHALL be secret-free metadata and SHALL be valid input to the system's existing agent-name normalization and validation rules.

#### Scenario: Brain recipe carries a reusable default agent name
- **WHEN** a developer creates or updates a brain recipe that is intended to launch directly without an external blueprint-provided name
- **THEN** the recipe may declare `default_agent_name`
- **AND** that field remains separate from the recipe identifier in `name`
- **AND** the recipe remains declarative and secret-free

#### Scenario: Shared recipe loading accepts a recipe with default_agent_name
- **WHEN** the system loads a brain recipe file that includes `default_agent_name`
- **THEN** shared recipe parsing succeeds
- **AND** the loaded recipe exposes that `default_agent_name` value to downstream consumers

#### Scenario: Shared recipe loading remains compatible with recipes that omit default_agent_name
- **WHEN** the system loads a brain recipe file that does not include `default_agent_name`
- **THEN** shared recipe parsing still succeeds
- **AND** downstream consumers can treat the default agent name as absent

### Requirement: Tracked interactive-demo brain recipes
The repository SHALL provide tracked, declarative, secret-free brain recipes under `agents/brains/brain-recipes/` for the interactive CAO full-pipeline demo launch variants that the repo documents and verifies.

The tracked interactive-demo recipe set SHALL include at minimum:

- `claude/gpu-kernel-coder-default`
- `codex/gpu-kernel-coder-default`
- `codex/gpu-kernel-coder-yunwu-openai`

Each tracked recipe SHALL continue to select its tool, skills, config profile, and credential profile by identifier only and SHALL NOT embed secret material.
Each tracked interactive-demo recipe SHALL also declare `default_agent_name` so the interactive demo can launch from the recipe without requiring a separate hard-coded default identity.
The tracked interactive-demo recipe set SHALL use tool-specific `default_agent_name` values rather than one shared cross-tool default name.

#### Scenario: Developer can locate the tracked default Claude demo recipe
- **WHEN** a developer needs to inspect or update the default Claude startup used by the interactive CAO demo
- **THEN** the repo contains a tracked recipe at `agents/brains/brain-recipes/claude/gpu-kernel-coder-default.yaml`
- **AND** that recipe declares the Claude tool plus the config-profile and credential-profile identifiers needed for the default interactive demo launch
- **AND** that recipe declares the default agent name used when the demo starts without `--agent-name`

#### Scenario: Developer can locate the tracked Codex demo recipes
- **WHEN** a developer needs to inspect or update the supported Codex startup variants used by the interactive CAO demo
- **THEN** the repo contains tracked recipes for `codex/gpu-kernel-coder-default` and `codex/gpu-kernel-coder-yunwu-openai`
- **AND** those recipes declare their default agent names for direct recipe-backed startup
- **AND** those recipes remain declarative and secret-free

#### Scenario: Tracked interactive-demo recipes use tool-distinguishable default names
- **WHEN** a developer compares the tracked Claude and Codex recipes used by the interactive CAO demo
- **THEN** the recipes do not all share one identical `default_agent_name`
- **AND** the default names distinguish the direct-launch identity defaults across the supported tools
