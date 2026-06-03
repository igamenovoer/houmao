## ADDED Requirements

### Requirement: Credential-management skill uses consolidated project targeting
The packaged credential-management skill SHALL route ordinary project credential requests to:

```text
houmao-mgr project [--project-dir <dir>] credentials <tool> <verb>
```

When the user names a project directory explicitly, the skill SHALL use the group-level `--project-dir` option instead of selecting a top-level credential target.

The skill SHALL NOT present `houmao-mgr credentials --project ...` as the maintained project credential workflow.

#### Scenario: Skill routes explicit project credential request
- **WHEN** a user asks the agent to list Codex credentials for project `/repo`
- **THEN** the skill guidance routes to `houmao-mgr project --project-dir /repo credentials codex list`
- **AND THEN** it does not route to `houmao-mgr credentials --project codex list`

### Requirement: Credential-management skill routes direct native credentials to internals
The packaged credential-management skill SHALL treat direct native-agent credential roots as internal provider-aligned material.

When the user explicitly asks for direct native-agent credential CRUD outside a Houmao project, the skill SHALL route to:

```text
houmao-mgr internals native-agent credentials <tool> <verb> --native-agent-root <dir>
```

The skill SHALL ask for a native-agent root when the user requests direct native credential work but no root can be inferred.

#### Scenario: Skill routes direct native credential request
- **WHEN** a user asks the agent to update a Codex credential under native-agent root `/tmp/native`
- **THEN** the skill guidance routes to `houmao-mgr internals native-agent credentials codex set --native-agent-root /tmp/native`
- **AND THEN** it does not route to a top-level `credentials --agent-def-dir` command
