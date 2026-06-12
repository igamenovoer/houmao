## ADDED Requirements

### Requirement: Project agent launch validates only the selected birth source
`houmao-mgr project agents launch` SHALL resolve and validate only the operator-selected birth source and the definitions needed to launch that source.

The command SHALL NOT parse every project preset, profile, or launch profile in a way that can make stale unrelated records block the selected launch.

The command SHALL still fail before publishing active managed-agent registry metadata when the selected source or its dependencies contain invalid launch configuration.

#### Scenario: Specialist launch ignores unrelated stale preset
- **WHEN** an unrelated project preset contains removed system-skill selector `houmao-agent-ag-ui`
- **AND WHEN** an operator runs `houmao-mgr project agents launch --specialist test-claude-kimi --name startup-graphics-test`
- **THEN** the command does not fail because of the unrelated preset
- **AND THEN** any launch failure is tied to `test-claude-kimi`, its selected source dependencies, tmux setup, credentials, gateway setup, or provider startup

#### Scenario: Selected invalid specialist fails before registry publish
- **WHEN** the selected specialist or selected launch source contains removed system-skill selector `houmao-agent-ag-ui`
- **AND WHEN** an operator runs `houmao-mgr project agents launch` for that source
- **THEN** the command fails before publishing active managed-agent registry metadata
- **AND THEN** the error identifies the selected source and the removed selector
