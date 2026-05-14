## MODIFIED Requirements

### Requirement: CLI reference describes unified agent-definition skill
The CLI reference SHALL describe `houmao-agent-definition` as the packaged skill for low-level definitions, `raw-profiles`, project-easy specialists, easy `profiles`, and `create-agent-fast-forward`.

The CLI reference SHALL route raw recipe-backed profile authoring away from `houmao-project-mgr` and toward the `houmao-agent-definition` `raw-profiles` subcommand.

If `houmao-specialist-mgr` remains documented, the reference SHALL identify it as compatibility guidance or a migration alias.

#### Scenario: CLI reference routes raw profiles to agent-definition
- **WHEN** a reader checks the system-skills CLI reference for `project agents launch-profiles ...`
- **THEN** the reference points the agent-facing guidance to `houmao-agent-definition` and the `raw-profiles` subcommand
- **AND THEN** it does not describe `houmao-project-mgr` as the owner of raw recipe-backed profile authoring

#### Scenario: CLI reference includes fast-forward profile preparation
- **WHEN** a reader checks which skill supports one-click agent profile preparation
- **THEN** the CLI reference identifies `houmao-agent-definition` and `create-agent-fast-forward`
- **AND THEN** it describes that path as creating or updating a launchable easy profile without launching the agent
