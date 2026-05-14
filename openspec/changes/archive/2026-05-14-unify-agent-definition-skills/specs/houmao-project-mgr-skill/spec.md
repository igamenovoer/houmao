## MODIFIED Requirements

### Requirement: Packaged `houmao-project-mgr` skill covers project overlay lifecycle and project-scoped management surfaces
The packaged current Houmao-owned system-skill inventory SHALL include `houmao-project-mgr` as the Houmao-owned project-management skill.

That packaged skill SHALL use `houmao-project-mgr` as both its skill name and its packaged asset directory name under `src/houmao/agents/assets/system_skills/`.

The top-level `houmao-project-mgr` skill SHALL act as an index/router for these supported project command families:

- `houmao-mgr project init`
- `houmao-mgr project status`
- `houmao-mgr project easy instance list|get|stop`

The packaged skill SHALL treat explicit recipe-backed launch-profile authoring as an agent-definition/profile workflow and SHALL route `project agents launch-profiles list|get|add|set|remove` guidance to `houmao-agent-definition`.

The packaged skill SHALL treat `project easy instance list|get|stop` as the selected-project overlay inspection and stop surface for already-launched easy instances.

#### Scenario: Agent needs project overlay lifecycle guidance
- **WHEN** an agent is asked to create or inspect the active Houmao project overlay
- **THEN** `houmao-project-mgr` routes that task through `houmao-mgr project init` or `houmao-mgr project status`
- **AND THEN** the skill treats those commands as the canonical project-overlay lifecycle entrypoints

#### Scenario: Agent needs explicit launch-profile authoring guidance
- **WHEN** an agent is asked to list, inspect, add, update, replace, or remove one explicit recipe-backed launch profile
- **THEN** `houmao-project-mgr` routes that request to `houmao-agent-definition`
- **AND THEN** it does not keep explicit launch-profile authoring as project-overlay lifecycle work

#### Scenario: Agent needs easy-instance inspection guidance
- **WHEN** an agent is asked to inspect or stop one easy instance through the selected project overlay
- **THEN** `houmao-project-mgr` routes that task through `project easy instance list|get|stop`
- **AND THEN** the skill does not redirect that selected-overlay inspection task to unrelated generic lifecycle or mailbox command families
