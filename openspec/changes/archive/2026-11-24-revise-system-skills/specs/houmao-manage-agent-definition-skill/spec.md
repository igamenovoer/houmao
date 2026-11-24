# Agent Definition Skill Delta

## ADDED Requirements

### Requirement: Definition guidance authors saved tmux server selectors
The definition skill SHALL teach saving tmux selectors with `project profile create|set` for specialist-backed profiles and `project agents launch-profiles add|set` for recipe-backed project profiles. It SHALL keep these flags within those project profile command families.

#### Scenario: An operator saves a tmux server choice for future launches
- **WHEN** the operator chooses a tmux server while authoring one of the two project profile types
- **THEN** the skill describes `user-default`, `houmao-default`, `new`, and `socket`
- **AND THEN** it explains that `socket` requires an absolute `--tmux-socket-path` in the execution owner's context and selects an existing server at launch
- **AND THEN** it shows that the profile's matching `get` command reports `defaults.posture.tmux`

#### Scenario: A profile patch preserves or clears the selected server
- **WHEN** an operator patches an existing profile
- **THEN** the skill explains that omitting tmux options preserves the saved selector, setting a mode replaces it, and `set --clear-tmux-server` restores launch-time fallback
- **AND THEN** it keeps those options distinct from native launch-dossier authoring and other launch posture options
