## ADDED Requirements

### Requirement: Agent blueprint documentation does not revive the retired blueprint layout

Documentation MAY use the term **agent blueprint** for the versioned portable `blueprint.toml` package consumed by `houmao-mgr project agent-blueprints` and `agent-deployments`.

Documentation SHALL distinguish that package from the retired native-agent `blueprints/`, brains, brain-recipes, config-profile, and credential-profile layouts. It SHALL NOT describe those retired paths or shapes as inputs to the new deployment workflow.

#### Scenario: New blueprint guide uses the current package contract

- **WHEN** an operator reads the agent blueprint authoring or deployment documentation
- **THEN** the guide describes `blueprint.toml`, typed task inputs, declared output templates, and current project commands
- **AND THEN** it does not direct the operator to create the retired native-agent `blueprints/` tree
