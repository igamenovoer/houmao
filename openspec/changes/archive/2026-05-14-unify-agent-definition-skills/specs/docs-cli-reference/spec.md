## ADDED Requirements

### Requirement: CLI reference describes unified agent-definition skill
The CLI reference SHALL describe `houmao-agent-definition` as the packaged skill for low-level definitions, explicit launch profiles, project-easy specialists, easy profiles, and ready-profile creation.

The CLI reference SHALL route explicit recipe-backed launch-profile authoring away from `houmao-project-mgr` and toward `houmao-agent-definition`.

If `houmao-specialist-mgr` remains documented, the reference SHALL identify it as compatibility guidance or a migration alias.

#### Scenario: CLI reference routes launch profiles to agent-definition
- **WHEN** a reader checks the system-skills CLI reference for `project agents launch-profiles ...`
- **THEN** the reference points the agent-facing guidance to `houmao-agent-definition`
- **AND THEN** it does not describe `houmao-project-mgr` as the owner of explicit launch-profile authoring

#### Scenario: CLI reference includes ready-profile creation
- **WHEN** a reader checks which skill supports one-click agent profile preparation
- **THEN** the CLI reference identifies `houmao-agent-definition`
- **AND THEN** it describes that path as creating a ready-to-launch easy profile without launching the agent
