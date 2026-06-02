## ADDED Requirements

### Requirement: Agent-definition skill avoids top-level target-variant commands
The packaged `houmao-agent-definition` skill SHALL route ordinary project authoring through:

```text
houmao-mgr project [--project-dir <dir>] ...
```

The skill SHALL route direct provider-aligned native material through:

```text
houmao-mgr internals native-agent [--native-agent-root <dir>] ...
```

The skill SHALL NOT present top-level `credentials --project`, top-level `credentials --agent-def-dir`, or top-level `brains build` as maintained command paths.

#### Scenario: Skill uses project directory selector for project authoring
- **WHEN** a user asks the agent to create a specialist in project `/repo`
- **THEN** the skill guidance routes to `houmao-mgr project --project-dir /repo specialist create`
- **AND THEN** it does not choose a top-level command only to select that project

#### Scenario: Skill uses internals for direct native build
- **WHEN** a user explicitly asks the agent to build a brain from native-agent root `/tmp/native`
- **THEN** the skill guidance routes to `houmao-mgr internals native-agent brain build --native-agent-root /tmp/native`
- **AND THEN** it does not route to top-level `houmao-mgr brains build --agent-def-dir /tmp/native`
